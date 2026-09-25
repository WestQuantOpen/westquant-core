# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Protocol, Sequence


MetricValue = float | int | None


@dataclass(frozen=True)
class Objective:
    name: str
    direction: str = "min"
    weight: float = 1.0

    def __post_init__(self) -> None:
        if self.direction not in {"min", "max"}:
            raise ValueError("direction must be 'min' or 'max'")

    def normalize(self, value: MetricValue) -> float:
        if value is None:
            return math.inf
        x = float(value)
        return x if self.direction == "min" else -x


@dataclass(frozen=True)
class Action:
    stage: str
    name: str
    parameters: dict[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str:
        blob = json.dumps(
            {"stage": self.stage, "name": self.name, "parameters": self.parameters},
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return f"{self.stage}:{self.name}:{hashlib.sha256(blob.encode()).hexdigest()[:12]}"

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "stage": self.stage, "name": self.name, "parameters": self.parameters}


@dataclass
class Evaluation:
    success: bool
    metrics: dict[str, MetricValue] = field(default_factory=dict)
    verification: dict[str, Any] = field(default_factory=dict)
    error: dict[str, Any] | None = None
    artifacts: dict[str, Any] = field(default_factory=dict)
    cost: dict[str, MetricValue] = field(default_factory=dict)

    @property
    def selectable(self) -> bool:
        if not self.success:
            return False
        equivalence = self.verification.get("equivalence")
        return equivalence != "invalid"

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "selectable": self.selectable,
            "metrics": self.metrics,
            "verification": self.verification,
            "error": self.error,
            "artifacts": self.artifacts,
            "cost": self.cost,
        }


@dataclass
class PolicyState:
    state_id: str
    parent_state_id: str | None
    step_index: int
    prefix: tuple[Action, ...]
    evaluation: Evaluation | None = None
    kept: bool = False
    terminal: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "state_id": self.state_id,
            "parent_state_id": self.parent_state_id,
            "step_index": self.step_index,
            "prefix": [a.to_dict() for a in self.prefix],
            "evaluation": self.evaluation.to_dict() if self.evaluation else None,
            "kept": self.kept,
            "terminal": self.terminal,
        }


class RolloutEvaluator(Protocol):
    def __call__(self, prefix: Sequence[Action]) -> Evaluation: ...


class ActionProvider(Protocol):
    def __call__(self, stage: str, prefix: Sequence[Action]) -> Iterable[Action]: ...


def state_id(challenge_id: str, prefix: Sequence[Action]) -> str:
    blob = json.dumps([a.to_dict() for a in prefix], sort_keys=True, separators=(",", ":"), default=str)
    return f"{challenge_id}:state:{hashlib.sha256(blob.encode()).hexdigest()[:16]}"


def pareto_dominates(a: dict[str, MetricValue], b: dict[str, MetricValue], objectives: Sequence[Objective]) -> bool:
    better_or_equal = True
    strictly_better = False
    for obj in objectives:
        av = obj.normalize(a.get(obj.name))
        bv = obj.normalize(b.get(obj.name))
        if av > bv:
            better_or_equal = False
            break
        if av < bv:
            strictly_better = True
    return better_or_equal and strictly_better


def pareto_front(items: Sequence[Any], metrics: Callable[[Any], dict[str, MetricValue]], objectives: Sequence[Objective]) -> list[Any]:
    front: list[Any] = []
    for i, item in enumerate(items):
        mi = metrics(item)
        if any(i != j and pareto_dominates(metrics(other), mi, objectives) for j, other in enumerate(items)):
            continue
        front.append(item)
    return front


@dataclass
class BeamSearchResult:
    challenge_id: str
    stages: tuple[str, ...]
    beam_width: int
    states: list[PolicyState]
    final_beam: list[PolicyState]
    objectives: tuple[Objective, ...]

    @property
    def best(self) -> PolicyState | None:
        selectable = [s for s in self.final_beam if s.evaluation and s.evaluation.selectable]
        if not selectable:
            return None
        return min(selectable, key=self._score_key)

    def _score_key(self, state: PolicyState) -> tuple[float, ...]:
        assert state.evaluation is not None
        exact_penalty = 0.0 if state.evaluation.verification.get("equivalence") == "exact" else 1.0
        vals = tuple(obj.normalize(state.evaluation.metrics.get(obj.name)) for obj in self.objectives)
        return (exact_penalty, *vals)

    def records(self, *, framework: str, context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        by_id = {s.state_id: s for s in self.states}
        out: list[dict[str, Any]] = []
        for s in self.states:
            if s.parent_state_id is None or s.evaluation is None:
                continue
            p = by_id.get(s.parent_state_id)
            before = p.evaluation.metrics if p and p.evaluation else {}
            after = s.evaluation.metrics
            out.append({
                "schema_version": "wqt-policy-v0.1",
                "framework": framework,
                "challenge_id": self.challenge_id,
                "context": context or {},
                "state_id": s.parent_state_id,
                "next_state_id": s.state_id,
                "step_index": s.step_index,
                "stage": s.prefix[-1].stage,
                "action": s.prefix[-1].to_dict(),
                "prefix_before": [a.to_dict() for a in (p.prefix if p else ())],
                "prefix_after": [a.to_dict() for a in s.prefix],
                "success": s.evaluation.success,
                "selectable": s.evaluation.selectable,
                "verification": s.evaluation.verification,
                "metrics_before": before,
                "metrics_after": after,
                "reward_vector": metric_delta(after, before),
                "cost": s.evaluation.cost,
                "kept_in_beam": s.kept,
                "terminal": s.terminal,
                "error": s.evaluation.error,
            })
        return out


def metric_delta(after: dict[str, MetricValue], before: dict[str, MetricValue]) -> dict[str, float | None]:
    keys = sorted(set(after) | set(before))
    out: dict[str, float | None] = {}
    for k in keys:
        av, bv = after.get(k), before.get(k)
        if isinstance(av, (int, float)) and isinstance(bv, (int, float)):
            out[k] = float(av) - float(bv)
        else:
            out[k] = None
    return out


class DeterministicBeamSearch:
    def __init__(self, *, stages: Sequence[str], beam_width: int, objectives: Sequence[Objective]) -> None:
        if not stages:
            raise ValueError("stages must be non-empty")
        if beam_width < 1:
            raise ValueError("beam_width must be >= 1")
        if not objectives:
            raise ValueError("at least one objective is required")
        self.stages = tuple(stages)
        self.beam_width = int(beam_width)
        self.objectives = tuple(objectives)

    def run(self, *, challenge_id: str, actions: ActionProvider, evaluate: RolloutEvaluator) -> BeamSearchResult:
        root = PolicyState(
            state_id=state_id(challenge_id, ()),
            parent_state_id=None,
            step_index=-1,
            prefix=(),
            evaluation=None,
            kept=True,
            terminal=False,
        )
        states = [root]
        beam = [root]

        for step_index, stage in enumerate(self.stages):
            expanded: list[PolicyState] = []
            for parent in beam:
                choices = sorted(list(actions(stage, parent.prefix)), key=lambda a: (a.name, a.id))
                for action in choices:
                    prefix = parent.prefix + (action,)
                    ev = evaluate(prefix)
                    expanded.append(PolicyState(
                        state_id=state_id(challenge_id, prefix),
                        parent_state_id=parent.state_id,
                        step_index=step_index,
                        prefix=prefix,
                        evaluation=ev,
                        kept=False,
                        terminal=step_index == len(self.stages) - 1,
                    ))
            expanded.sort(key=self._state_key)
            beam = [s for s in expanded if s.evaluation and s.evaluation.selectable][: self.beam_width]
            for s in beam:
                s.kept = True
            states.extend(expanded)
            if not beam:
                break

        return BeamSearchResult(
            challenge_id=challenge_id,
            stages=self.stages,
            beam_width=self.beam_width,
            states=states,
            final_beam=beam,
            objectives=self.objectives,
        )

    def _state_key(self, state: PolicyState) -> tuple[float, ...]:
        if state.evaluation is None or not state.evaluation.selectable:
            return (math.inf,) * (len(self.objectives) + 2)
        exact_penalty = 0.0 if state.evaluation.verification.get("equivalence") == "exact" else 1.0
        vals = tuple(obj.normalize(state.evaluation.metrics.get(obj.name)) for obj in self.objectives)
        # Stable deterministic tie-breaker based on prefix action ids.
        tie = int(hashlib.sha256("|".join(a.id for a in state.prefix).encode()).hexdigest()[:12], 16)
        return (exact_penalty, *vals, float(tie))


@dataclass
class UnifiedSearchResult:
    """Framework-agnostic search result interface."""
    challenge_id: str
    best_metrics: dict[str, MetricValue] | None
    best_config: dict[str, Any] | None
    best_circuit: Any | None = None
    n_candidates: int = 0
    n_compile_success: int = 0
    n_verified: int = 0
    n_pareto: int = 0
    framework: str = ""

    @staticmethod
    def from_qiskit(result: Any) -> "UnifiedSearchResult":
        """Adapt a Qiskit SearchResult to unified interface."""
        best = result.best
        return UnifiedSearchResult(
            challenge_id=result.challenge_id,
            best_metrics=best.metrics if best else None,
            best_config=best.config.to_dict() if best else None,
            n_candidates=len(result.candidates),
            n_compile_success=sum(c.compile_success for c in result.candidates),
            n_verified=sum(bool(c.verification and c.verification.verified) for c in result.candidates),
            n_pareto=len(result.pareto_front),
            framework="qiskit",
        )

    @staticmethod
    def from_pytket(result: Any) -> "UnifiedSearchResult":
        """Adapt a pytket BeamSearchResult to unified interface."""
        best = result.best
        return UnifiedSearchResult(
            challenge_id=result.challenge_id,
            best_metrics=best.evaluation.metrics if best and best.evaluation else None,
            best_config=None,
            n_candidates=len(result.states),
            n_compile_success=sum(bool(s.evaluation and s.evaluation.success) for s in result.states if s.parent_state_id),
            n_verified=0,
            n_pareto=0,
            framework="pytket",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "challenge_id": self.challenge_id,
            "framework": self.framework,
            "best_metrics": self.best_metrics,
            "best_config": self.best_config,
            "n_candidates": self.n_candidates,
            "n_compile_success": self.n_compile_success,
            "n_verified": self.n_verified,
            "n_pareto": self.n_pareto,
        }


def _within(a: MetricValue, b: MetricValue, tol: float) -> bool:
    if a is None or b is None:
        return a is None and b is None
    return abs(float(a) - float(b)) <= tol


def cluster_representations(
    items: Sequence[Any], metrics: Callable[[Any], dict[str, MetricValue]], tolerance: float = 0.0
) -> list[list[Any]]:
    """Group items by metric similarity within tolerance.

    Items are in the same cluster if all metric values are within tolerance
    of each other.
    """
    if not items:
        return []
    clusters: list[list[Any]] = []
    for item in items:
        mi = metrics(item)
        placed = False
        for cluster in clusters:
            m0 = metrics(cluster[0])
            if all(_within(mi.get(k), m0.get(k), tolerance) for k in set(mi) | set(m0)):
                cluster.append(item)
                placed = True
                break
        if not placed:
            clusters.append([item])
    return clusters


def score_representations(
    items: Sequence[Any], metrics: Callable[[Any], dict[str, MetricValue]], weights: dict[str, float]
) -> list[tuple[float, Any]]:
    """Score items by weighted sum of normalized metrics.

    Returns list of (score, item) sorted by score ascending (lower is better).
    """
    scored = []
    for item in items:
        mi = metrics(item)
        score = 0.0
        for name, weight in weights.items():
            val = mi.get(name)
            if val is not None:
                score += weight * float(val)
        scored.append((score, item))
    scored.sort(key=lambda x: x[0])
    return scored


def hypervolume(
    pareto_items: Sequence[Any],
    metrics: Callable[[Any], dict[str, MetricValue]],
    objectives: Sequence[Objective],
    reference: dict[str, MetricValue] | None = None,
) -> float:
    """Compute hypervolume of Pareto front.

    Uses a simple recursive algorithm for 2D, Monte Carlo for higher dims.
    """
    if not pareto_items:
        return 0.0
    if len(objectives) == 2:
        return _hypervolume_2d(pareto_items, metrics, objectives, reference)
    # Monte Carlo for higher dimensions
    return _hypervolume_mc(pareto_items, metrics, objectives, reference)


def _hypervolume_2d(items, metrics, objectives, reference):
    import random
    pts = []
    for item in items:
        mi = metrics(item)
        pts.append(tuple(obj.normalize(mi.get(obj.name)) for obj in objectives))
    if not pts:
        return 0.0
    ref = reference or {}
    ref_pt = tuple(obj.normalize(ref.get(obj.name, 0.0)) for obj in objectives)
    pts.sort()
    hv = 0.0
    prev = ref_pt[1]
    for x, y in pts:
        if y < prev:
            hv += (x - ref_pt[0]) * (prev - y)
            prev = y
    return hv


def _hypervolume_mc(items, metrics, objectives, reference, n_samples=10000):
    import random
    random.seed(42)
    pts = []
    for item in items:
        mi = metrics(item)
        pts.append(tuple(obj.normalize(mi.get(obj.name)) for obj in objectives))
    if not pts:
        return 0.0
    ref = reference or {}
    ref_pt = tuple(obj.normalize(ref.get(obj.name, 0.0)) for obj in objectives)
    mins = [min(p[i] for p in pts) for i in range(len(objectives))]
    maxs = [max(p[i] for p in pts) for i in range(len(objectives))]
    count = 0
    for _ in range(n_samples):
        sample = tuple(random.uniform(mins[i], maxs[i]) for i in range(len(objectives)))
        dominated = all(all(s <= p[i] for i, p in enumerate(pts)) for s in [sample])
        if dominated:
            count += 1
    vol = 1.0
    for i in range(len(objectives)):
        vol *= (maxs[i] - mins[i])
    return vol * count / n_samples
