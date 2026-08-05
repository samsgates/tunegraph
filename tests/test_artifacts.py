from pathlib import Path

from tunegraph.config import Settings
from tunegraph.services.artifacts import LocalArtifactStore


def test_local_artifact_store_is_content_addressed(tmp_path: Path) -> None:
    settings = Settings(secret_key="x" * 64, artifact_root=tmp_path)
    store = LocalArtifactStore(settings)
    first = store.put_bytes("patches", "adapter.bin", b"content")
    second = store.put_bytes("patches", "adapter.bin", b"content")
    assert first.uri == second.uri
    assert store.read_bytes(first.uri) == b"content"
