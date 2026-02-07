"""Archive storage abstraction — local filesystem impl, swappable for S3 in Phase 7."""

from __future__ import annotations

import gzip
import json
import logging
from collections.abc import Iterator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class ArchiveStorage(Protocol):
    """Protocol for archive storage backends."""

    def write(
        self, org_id: str, table_name: str, records: list[dict[str, Any]], metadata: dict[str, Any]
    ) -> tuple[str, int]:
        """Write records to archive. Returns (relative_path, compressed_size_bytes)."""
        ...

    def read(self, file_path: str) -> Iterator[dict[str, Any]]:
        """Stream records from archive, skipping metadata header."""
        ...

    def exists(self, file_path: str) -> bool:
        """Check if archive file exists."""
        ...


class LocalArchiveStorage:
    """Local filesystem archive storage (JSONL.gz)."""

    def __init__(self, base_path: str = "/app/archives") -> None:
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def write(
        self, org_id: str, table_name: str, records: list[dict[str, Any]], metadata: dict[str, Any]
    ) -> tuple[str, int]:
        """Write records as gzipped JSONL. Returns (relative_path, compressed_size)."""
        now = datetime.now(timezone.utc)
        rel_dir = Path(org_id) / table_name
        filename = f"{now.strftime('%Y%m%d_%H%M%S')}.jsonl.gz"
        rel_path = rel_dir / filename

        full_path = self.base_path / rel_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        with gzip.open(full_path, "wt", encoding="utf-8") as f:
            f.write(json.dumps({"_metadata": metadata}, default=str) + "\n")
            for record in records:
                f.write(json.dumps(record, default=str) + "\n")

        compressed_size = full_path.stat().st_size
        logger.info("Wrote archive %s (%d records, %d bytes)", rel_path, len(records), compressed_size)
        return str(rel_path), compressed_size

    def read(self, file_path: str) -> Iterator[dict[str, Any]]:
        """Stream records from gzipped JSONL, skipping metadata header."""
        full_path = self.base_path / file_path
        with gzip.open(full_path, "rt", encoding="utf-8") as f:
            for line in f:
                record = json.loads(line.strip())
                if "_metadata" not in record:
                    yield record

    def exists(self, file_path: str) -> bool:
        """Check if archive file exists."""
        return (self.base_path / file_path).exists()
