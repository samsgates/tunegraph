from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from tunegraph.config import Settings
from tunegraph.services.hashing import sha256_bytes


@dataclass(frozen=True, slots=True)
class StoredArtifact:
    uri: str
    sha256: str
    size_bytes: int


class LocalArtifactStore:
    def __init__(self, settings: Settings) -> None:
        self.root = settings.artifact_root
        self.root.mkdir(parents=True, exist_ok=True)

    def put_bytes(self, namespace: str, name: str, payload: bytes) -> StoredArtifact:
        safe_namespace = self._safe_component(namespace)
        safe_name = self._safe_component(name)
        digest = sha256_bytes(payload)
        destination = self.root / safe_namespace / digest[:2] / f"{safe_name}-{digest}"
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        temporary.write_bytes(payload)
        os.replace(temporary, destination)
        return StoredArtifact(
            uri=destination.as_uri(), sha256=digest, size_bytes=destination.stat().st_size
        )

    def import_file(self, namespace: str, source: Path) -> StoredArtifact:
        payload = source.read_bytes()
        artifact = self.put_bytes(namespace, source.name, payload)
        return artifact

    def read_bytes(self, uri: str) -> bytes:
        parsed = urlparse(uri)
        if parsed.scheme != "file":
            raise ValueError("LocalArtifactStore only supports file:// URIs")
        path = Path(parsed.path).resolve()
        if self.root not in path.parents and path != self.root:
            raise ValueError("Artifact path escapes configured root")
        return path.read_bytes()

    def delete(self, uri: str) -> None:
        parsed = urlparse(uri)
        path = Path(parsed.path).resolve()
        if self.root not in path.parents:
            raise ValueError("Artifact path escapes configured root")
        path.unlink(missing_ok=True)

    def clear(self) -> None:
        if self.root.exists():
            shutil.rmtree(self.root)
            self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _safe_component(value: str) -> str:
        safe = "".join(char for char in value if char.isalnum() or char in "-_.")
        if not safe or safe in {".", ".."}:
            raise ValueError("Invalid artifact component")
        return safe[:255]
