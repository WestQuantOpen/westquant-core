# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True)
class TransformationSpec:
    transform_id: str
    version: str
    input_kinds: tuple[str, ...]
    output_kind: str
    equivalence: str = "unknown"
    description: str = ""
    applicability: dict[str, Any] = field(default_factory=dict)
    verification_method: str = "runtime"


class TransformationRegistry:
    def __init__(self) -> None:
        self._specs: dict[str, TransformationSpec] = {}
        self._impls: dict[str, Callable[..., Any]] = {}

    def register(self, spec: TransformationSpec, implementation: Callable[..., Any] | None = None) -> None:
        key = f"{spec.transform_id}@{spec.version}"
        if key in self._specs:
            raise ValueError(f"duplicate transformation: {key}")
        self._specs[key] = spec
        if implementation is not None:
            self._impls[key] = implementation

    def get(self, transform_id: str, version: str) -> TransformationSpec:
        return self._specs[f"{transform_id}@{version}"]

    def implementation(self, transform_id: str, version: str) -> Callable[..., Any] | None:
        return self._impls.get(f"{transform_id}@{version}")

    def list(self) -> list[TransformationSpec]:
        return [self._specs[k] for k in sorted(self._specs)]
