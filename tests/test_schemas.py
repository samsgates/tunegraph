import pytest
from pydantic import ValidationError

from tunegraph.schemas import GraphCreate, TrainingJobCreate


def test_graph_rejects_duplicate_patches() -> None:
    with pytest.raises(ValidationError):
        GraphCreate(
            name="graph",
            version=1,
            base_model_id="model",
            patch_ids=["patch", "patch"],
        )


def test_training_method_is_bounded() -> None:
    with pytest.raises(ValidationError):
        TrainingJobCreate(
            name="job",
            base_model_id="model",
            dataset_id="dataset",
            capability_id="capability",
            method="full_finetune",
        )
