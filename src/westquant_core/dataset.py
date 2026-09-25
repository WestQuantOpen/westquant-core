from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class DatasetManifest:
    dataset_id: str
    schema_version: str
    generator_version: str
    framework: str
    config: dict[str, Any]
    planned_challenges: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset_id": self.dataset_id,
            "schema_version": self.schema_version,
            "generator_version": self.generator_version,
            "framework": self.framework,
            "config": self.config,
            "planned_challenges": self.planned_challenges,
            "metadata": self.metadata,
        }

    @property
    def sha256(self) -> str:
        blob = json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"), default=str).encode()
        return hashlib.sha256(blob).hexdigest()


def write_jsonl(path: str | Path, records: Iterable[dict[str, Any]], *, append: bool = False) -> int:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    n = 0
    with path.open(mode, encoding="utf-8") as f:
        for record in records:
            f.write(json.dumps(record, sort_keys=True, default=str) + "\n")
            n += 1
    return n


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, 1):
            if not line.strip():
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid JSONL at line {line_no}: {exc}") from exc
    return out
