# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from .model import Representation, TransformationRecord


@dataclass(frozen=True)
class PluginCapabilities:
    import_kinds: tuple[str, ...] = ()
    export_kinds: tuple[str, ...] = ()
    transformations: tuple[str, ...] = ()
    evaluators: tuple[str, ...] = ()
    runtimes: tuple[str, ...] = ()
    supports_repgraph: bool = True
    supports_wqt_policy: bool = False


@dataclass(frozen=True)
class PluginManifest:
    plugin_id: str
    version: str
    framework: str
    framework_versions: str
    api_version: str = "0.1"
    capabilities: PluginCapabilities = field(default_factory=PluginCapabilities)


@runtime_checkable
class FrontendAdapter(Protocol):
    def import_native(self, obj: Any, **context: Any) -> Representation: ...
    def export_native(self, representation: Representation, **context: Any) -> Any: ...


@runtime_checkable
class TransformationProvider(Protocol):
    def available_transformations(self, representation: Representation, **context: Any) -> list[str]: ...
    def apply_transformation(
        self, representation: Representation, transform_id: str, **context: Any
    ) -> tuple[Representation, TransformationRecord]: ...


@runtime_checkable
class CompilerAdapter(Protocol):
    def compile(self, representation: Representation, **context: Any) -> Representation: ...


@runtime_checkable
class EvaluatorAdapter(Protocol):
    def evaluate(self, representation: Representation, **context: Any) -> dict[str, Any]: ...


@runtime_checkable
class RuntimeAdapter(Protocol):
    def execute(self, representation: Representation, **context: Any) -> dict[str, Any]: ...


@runtime_checkable
class WestQuantPlugin(Protocol):
    @property
    def manifest(self) -> PluginManifest: ...
