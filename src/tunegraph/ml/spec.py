from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator


class LoraMethodConfig(BaseModel):
    type: Literal["lora", "qlora", "dora"] = "lora"
    rank: int = Field(default=8, ge=1, le=1024)
    alpha: int = Field(default=16, ge=1)
    dropout: float = Field(default=0.05, ge=0, lt=1)
    target_modules: list[str] = Field(default_factory=lambda: ["q_proj", "v_proj"])
    use_rslora: bool = False


class TrainingSpecification(BaseModel):
    model_name_or_path: str
    model_revision: str | None = None
    dataset_uri: str
    output_dir: str
    text_field: str = "text"
    max_sequence_length: int = Field(default=2048, ge=128, le=131072)
    learning_rate: float = Field(default=2e-4, gt=0)
    epochs: float = Field(default=1.0, gt=0)
    per_device_train_batch_size: int = Field(default=1, ge=1)
    gradient_accumulation_steps: int = Field(default=8, ge=1)
    warmup_ratio: float = Field(default=0.03, ge=0, le=1)
    seed: int = 42
    bf16: bool = True
    gradient_checkpointing: bool = True
    method: LoraMethodConfig = Field(default_factory=LoraMethodConfig)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_quantization(self) -> "TrainingSpecification":
        if self.method.type == "qlora" and not self.bf16:
            raise ValueError("QLoRA requires bf16 compute in the reference trainer")
        return self
