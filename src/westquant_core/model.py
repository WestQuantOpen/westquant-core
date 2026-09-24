from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RepresentationKind(str, Enum):
    PROBLEM = "problem"
    OPERATOR = "operator"
    CIRCUIT = "circuit"
    LAYOUT = "layout"
    CONTROL = "control"
    HARDWARE = "hardware"
    EXECUTION = "execution"
    EVALUATION = "evaluation"


class EquivalenceKind(str, Enum):
    EXACT = "exact"
    OBJECTIVE_EQUIVALENT = "objective_equivalent"
    GROUND_STATE_EQUIVALENT = "ground_state_equivalent"
    SAME_PROBLEM_DIFFERENT_DYNAMICS = "same_problem_different_dynamics"
    APPROXIMATE = "approximate"
    UNKNOWN = "unknown"
    INVALID = "invalid"


@dataclass(frozen=True)
class Representation:
    id: str
    kind: RepresentationKind
    payload: dict[str, Any]
    schema_version: str = "0.2"
    semantic_root: str | None = None
    framework: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id.strip():
            raise ValueError("representation id must be non-empty")
        if not isinstance(self.payload, dict):
            raise TypeError("payload must be a dict")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "schema_version": self.schema_version,
            "semantic_root": self.semantic_root,
            "framework": self.framework,
            "payload": self.payload,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Representation":
        return cls(
            id=data["id"],
            kind=RepresentationKind(data["kind"]),
            schema_version=data.get("schema_version", "0.2"),
            semantic_root=data.get("semantic_root"),
            framework=data.get("framework"),
            payload=dict(data.get("payload", {})),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True)
class TransformationRecord:
    id: str
    input_id: str
    output_id: str
    transform_id: str
    transform_version: str
    equivalence: EquivalenceKind = EquivalenceKind.UNKNOWN
    parameters: dict[str, Any] = field(default_factory=dict)
    verification: dict[str, Any] = field(default_factory=dict)
    outcome: dict[str, Any] = field(default_factory=dict)
    metrics_before: dict[str, float | int | None] = field(default_factory=dict)
    metrics_after: dict[str, float | int | None] = field(default_factory=dict)
    framework: str | None = None
    cost: dict[str, float | int | None] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.id.strip() or not self.transform_id.strip():
            raise ValueError("transformation id fields must be non-empty")
        if self.input_id == self.output_id:
            raise ValueError("input_id and output_id must differ")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "input_id": self.input_id,
            "output_id": self.output_id,
            "transform_id": self.transform_id,
            "transform_version": self.transform_version,
            "equivalence": self.equivalence.value,
            "parameters": self.parameters,
            "verification": self.verification,
            "outcome": self.outcome,
            "metrics_before": self.metrics_before,
            "metrics_after": self.metrics_after,
            "framework": self.framework,
            "cost": self.cost,
        }
