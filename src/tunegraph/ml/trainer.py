from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tunegraph.ml.spec import TrainingSpecification
from tunegraph.services.hashing import sha256_bytes


class OptionalDependencyError(RuntimeError):
    pass


def run_peft_training(specification: TrainingSpecification) -> dict[str, Any]:
    """Run a supervised PEFT training job.

    Heavy ML dependencies are imported lazily so the control plane remains lightweight.
    The dataset URI currently supports local JSON/JSONL/Parquet paths and Hugging Face
    dataset identifiers accepted by `datasets.load_dataset`.
    """

    try:
        import torch
        from datasets import load_dataset
        from peft import LoraConfig
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        from trl import SFTConfig, SFTTrainer
    except ImportError as exc:
        raise OptionalDependencyError(
            "Install TuneGraph with the ML extra: uv sync --extra ml"
        ) from exc

    output_dir = Path(specification.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    quantization_config = None
    if specification.method.type == "qlora":
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        )

    tokenizer = AutoTokenizer.from_pretrained(
        specification.model_name_or_path,
        revision=specification.model_revision,
        trust_remote_code=False,
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        specification.model_name_or_path,
        revision=specification.model_revision,
        quantization_config=quantization_config,
        torch_dtype=torch.bfloat16 if specification.bf16 else torch.float16,
        trust_remote_code=False,
    )
    model.config.use_cache = False

    data_files = None
    path = Path(specification.dataset_uri)
    if path.exists():
        suffix = path.suffix.lower()
        loader = "json" if suffix in {".json", ".jsonl"} else "parquet"
        data_files = {"train": str(path)}
        dataset = load_dataset(loader, data_files=data_files, split="train")
    else:
        dataset = load_dataset(specification.dataset_uri, split="train")

    peft_config = LoraConfig(
        r=specification.method.rank,
        lora_alpha=specification.method.alpha,
        lora_dropout=specification.method.dropout,
        target_modules=specification.method.target_modules,
        task_type="CAUSAL_LM",
        use_rslora=specification.method.use_rslora,
        use_dora=specification.method.type == "dora",
        bias="none",
    )
    training_args = SFTConfig(
        output_dir=str(output_dir),
        num_train_epochs=specification.epochs,
        per_device_train_batch_size=specification.per_device_train_batch_size,
        gradient_accumulation_steps=specification.gradient_accumulation_steps,
        learning_rate=specification.learning_rate,
        warmup_ratio=specification.warmup_ratio,
        max_length=specification.max_sequence_length,
        dataset_text_field=specification.text_field,
        gradient_checkpointing=specification.gradient_checkpointing,
        bf16=specification.bf16,
        seed=specification.seed,
        save_strategy="epoch",
        logging_steps=10,
        report_to="none",
    )
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset,
        processing_class=tokenizer,
        peft_config=peft_config,
    )
    result = trainer.train()
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))

    manifest = {
        "specification": specification.model_dump(mode="json"),
        "metrics": result.metrics,
        "files": {},
    }
    for file in sorted(output_dir.rglob("*")):
        if file.is_file():
            manifest["files"][str(file.relative_to(output_dir))] = sha256_bytes(file.read_bytes())
    manifest_bytes = json.dumps(manifest, sort_keys=True, indent=2).encode()
    (output_dir / "tunegraph-manifest.json").write_bytes(manifest_bytes)
    return {"output_dir": str(output_dir), "manifest_sha256": sha256_bytes(manifest_bytes), **manifest}
