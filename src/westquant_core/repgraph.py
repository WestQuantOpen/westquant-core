# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .model import Representation, TransformationRecord


@dataclass
class RepGraph:
    graph_id: str
    schema_version: str = "0.2"
    nodes: dict[str, Representation] = field(default_factory=dict)
    edges: list[TransformationRecord] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_representation(self, representation: Representation) -> None:
        if representation.id in self.nodes:
            raise ValueError(f"duplicate representation id: {representation.id}")
        self.nodes[representation.id] = representation

    def add_transformation(self, edge: TransformationRecord) -> None:
        if edge.input_id not in self.nodes:
            raise ValueError(f"missing input representation: {edge.input_id}")
        if edge.output_id not in self.nodes:
            raise ValueError(f"missing output representation: {edge.output_id}")
        if any(existing.id == edge.id for existing in self.edges):
            raise ValueError(f"duplicate transformation id: {edge.id}")
        self.edges.append(edge)
        if self._has_cycle():
            self.edges.pop()
            raise ValueError("RepGraph must remain acyclic")

    def children(self, node_id: str) -> list[Representation]:
        ids = [e.output_id for e in self.edges if e.input_id == node_id]
        return [self.nodes[i] for i in ids]

    def validate(self) -> list[str]:
        errors: list[str] = []
        if not self.graph_id.strip():
            errors.append("graph_id is empty")
        for edge in self.edges:
            if edge.input_id not in self.nodes:
                errors.append(f"dangling input: {edge.input_id}")
            if edge.output_id not in self.nodes:
                errors.append(f"dangling output: {edge.output_id}")
        if self._has_cycle():
            errors.append("graph contains a cycle")
        return errors

    def _has_cycle(self) -> bool:
        adjacency: dict[str, list[str]] = {node_id: [] for node_id in self.nodes}
        for edge in self.edges:
            if edge.input_id in adjacency:
                adjacency[edge.input_id].append(edge.output_id)

        visiting: set[str] = set()
        visited: set[str] = set()

        def dfs(node: str) -> bool:
            if node in visiting:
                return True
            if node in visited:
                return False
            visiting.add(node)
            for nxt in adjacency.get(node, []):
                if dfs(nxt):
                    return True
            visiting.remove(node)
            visited.add(node)
            return False

        return any(dfs(node) for node in adjacency if node not in visited)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "graph_id": self.graph_id,
            "metadata": self.metadata,
            "nodes": [node.to_dict() for node in self.nodes.values()],
            "edges": [edge.to_dict() for edge in self.edges],
        }
