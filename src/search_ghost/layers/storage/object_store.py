"""
Unified file I/O via fsspec.
All storage operations go through this module — swap local↔S3 by changing kb_path.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import fsspec


class ObjectStore:
    """Thin wrapper around fsspec for consistent local/S3 access."""

    def __init__(self, root: str) -> None:
        self.root = root.rstrip("/")
        # Infer protocol from root prefix
        if root.startswith("s3://"):
            self._fs: fsspec.AbstractFileSystem = fsspec.filesystem("s3")
        else:
            self._fs = fsspec.filesystem("file")
            # Ensure local root exists
            Path(root).mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Path helpers
    # ------------------------------------------------------------------

    def _full(self, rel: str) -> str:
        return f"{self.root}/{rel}"

    # ------------------------------------------------------------------
    # Core ops
    # ------------------------------------------------------------------

    def exists(self, rel: str) -> bool:
        return self._fs.exists(self._full(rel))

    def makedirs(self, rel: str) -> None:
        self._fs.makedirs(self._full(rel), exist_ok=True)

    def read_bytes(self, rel: str) -> bytes:
        with self._fs.open(self._full(rel), "rb") as f:
            return f.read()

    def write_bytes(self, rel: str, data: bytes) -> None:
        self._fs.makedirs(self._full(rel).rsplit("/", 1)[0], exist_ok=True)
        with self._fs.open(self._full(rel), "wb") as f:
            f.write(data)

    def read_text(self, rel: str, encoding: str = "utf-8") -> str:
        return self.read_bytes(rel).decode(encoding)

    def write_text(self, rel: str, text: str, encoding: str = "utf-8") -> None:
        self.write_bytes(rel, text.encode(encoding))

    def read_json(self, rel: str) -> Any:
        return json.loads(self.read_text(rel))

    def write_json(self, rel: str, data: Any, indent: int = 2) -> None:
        self.write_text(rel, json.dumps(data, indent=indent, default=str))

    def ls(self, rel: str) -> list[str]:
        try:
            return self._fs.ls(self._full(rel), detail=False)
        except FileNotFoundError:
            return []

    def rm(self, rel: str, recursive: bool = False) -> None:
        self._fs.rm(self._full(rel), recursive=recursive)

    def local_path(self, rel: str) -> str:
        """Return local filesystem path (only valid for file:// stores)."""
        if self.root.startswith("s3://"):
            raise ValueError("Cannot get local path for S3 store")
        return self._full(rel)
