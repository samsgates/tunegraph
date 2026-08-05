from tunegraph.services.dataset_validation import DatasetValidator


def test_dataset_validation_passes_clean_metadata() -> None:
    report = DatasetValidator().validate(
        record_count=100,
        content_sha256="a" * 64,
        metadata={},
        checks=["schema", "duplicates", "secrets"],
        minimum_quality_score=0.8,
    )
    assert report["passed"] is True


def test_dataset_validation_blocks_secrets() -> None:
    report = DatasetValidator().validate(
        record_count=100,
        content_sha256="a" * 64,
        metadata={"contains_secrets": True},
        checks=["secrets"],
        minimum_quality_score=0.8,
    )
    assert report["passed"] is False
