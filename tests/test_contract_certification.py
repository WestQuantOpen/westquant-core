"""Phase 2: Core contract certification tests.

Tests serialization round-trips, canonical identity stability,
RepGraph integrity, transformation record completeness, and
policy schema validation.
"""
from westquant_core import (
    Action,
    EquivalenceKind,
    Evaluation,
    Objective,
    RepGraph,
    Representation,
    RepresentationKind,
    TransformationRecord,
    validate_policy_record,
    state_id,
    pareto_front,
    pareto_dominates,
    DeterministicBeamSearch,
)
import hashlib
import json


# --- Serialization round-trip ---

def test_representation_roundtrip_all_kinds():
    for kind in RepresentationKind:
        r = Representation(id=f"r-{kind.value}", kind=kind, payload={"k": "v"}, framework="test")
        d = r.to_dict()
        r2 = Representation.from_dict(d)
        assert r2 == r, f"roundtrip failed for {kind}"


def test_representation_roundtrip_with_metadata():
    r = Representation(
        id="r1", kind=RepresentationKind.SEARCH_STATE,
        payload={"stage": "layout"}, framework="qiskit",
        metadata={"seed": 42, "version": "0.2.0a1"},
        semantic_root="root-problem",
    )
    r2 = Representation.from_dict(r.to_dict())
    assert r2 == r
    assert r2.metadata == r.metadata
    assert r2.semantic_root == "root-problem"


def test_transformation_record_roundtrip():
    t = TransformationRecord(
        id="t1", input_id="a", output_id="b",
        transform_id="compile.qiskit", transform_version="2.5.2",
        equivalence=EquivalenceKind.EXACT,
        parameters={"opt_level": 2},
        verification={"method": "unitary", "verified": True},
        metrics_before={"depth": 4},
        metrics_after={"depth": 6},
        framework="qiskit",
        cost={"compile_seconds": 0.01},
    )
    d = t.to_dict()
    assert d["equivalence"] == "exact"
    assert d["framework"] == "qiskit"


def test_transformation_record_rejects_same_io():
    try:
        TransformationRecord(id="t1", input_id="a", output_id="a", transform_id="x", transform_version="1")
        raise AssertionError("Should have rejected same input/output")
    except ValueError:
        pass


# --- Canonical identity ---

def test_state_id_stable_for_same_prefix():
    actions = (Action("layout", "sabre"), Action("routing", "basic"))
    sid1 = state_id("challenge-1", actions)
    sid2 = state_id("challenge-1", actions)
    assert sid1 == sid2, "same prefix must produce same state_id"


def test_state_id_differs_for_different_challenge():
    actions = (Action("layout", "sabre"),)
    sid1 = state_id("challenge-1", actions)
    sid2 = state_id("challenge-2", actions)
    assert sid1 != sid2, "different challenge must produce different state_id"


def test_action_id_stable():
    a1 = Action("layout", "sabre", {"seed": 0})
    a2 = Action("layout", "sabre", {"seed": 0})
    assert a1.id == a2.id, "same action must produce same id"


def test_action_id_differs_for_different_params():
    a1 = Action("layout", "sabre", {"seed": 0})
    a2 = Action("layout", "sabre", {"seed": 1})
    assert a1.id != a2.id, "different params must produce different action id"


# --- RepGraph integrity ---

def test_repgraph_rejects_dangling_edge():
    g = RepGraph("g1")
    a = Representation("a", RepresentationKind.CIRCUIT, {})
    g.add_representation(a)
    try:
        g.add_transformation(TransformationRecord(
            "e1", "a", "missing", "t", "1", EquivalenceKind.EXACT
        ))
        raise AssertionError("Should reject dangling output")
    except ValueError:
        pass


def test_repgraph_rejects_duplicate_node():
    g = RepGraph("g1")
    g.add_representation(Representation("a", RepresentationKind.CIRCUIT, {}))
    try:
        g.add_representation(Representation("a", RepresentationKind.CIRCUIT, {}))
        raise AssertionError("Should reject duplicate node")
    except ValueError:
        pass


def test_repgraph_rejects_duplicate_edge():
    g = RepGraph("g1")
    a = Representation("a", RepresentationKind.CIRCUIT, {})
    b = Representation("b", RepresentationKind.CIRCUIT, {})
    g.add_representation(a)
    g.add_representation(b)
    g.add_transformation(TransformationRecord("e1", "a", "b", "t", "1"))
    try:
        g.add_transformation(TransformationRecord("e1", "a", "b", "t", "1"))
        raise AssertionError("Should reject duplicate edge")
    except ValueError:
        pass


def test_repgraph_serialization_roundtrip():
    g = RepGraph("g1", metadata={"framework": "test"})
    a = Representation("a", RepresentationKind.PROBLEM, {"type": "mwis"})
    b = Representation("b", RepresentationKind.CIRCUIT, {"depth": 4}, semantic_root="a")
    g.add_representation(a)
    g.add_representation(b)
    g.add_transformation(TransformationRecord(
        "e1", "a", "b", "encode", "1", EquivalenceKind.OBJECTIVE_EQUIVALENT
    ))
    d = g.to_dict()
    assert "nodes" in d
    assert "edges" in d
    assert len(d["nodes"]) == 2
    assert len(d["edges"]) == 1
    assert d["schema_version"] == "0.2"


# --- Policy schema validation ---

def test_policy_record_valid():
    record = {
        "schema_version": "wqt-policy-v0.1",
        "framework": "qiskit",
        "challenge_id": "test-001",
        "state_id": "s0",
        "next_state_id": "s1",
        "step_index": 0,
        "stage": "layout",
        "action": {"stage": "layout", "name": "sabre", "parameters": {}},
        "success": True,
        "selectable": True,
        "verification": {"equivalence": "exact", "verified": True},
        "metrics_before": {"depth": 4},
        "metrics_after": {"depth": 6},
        "kept_in_beam": True,
        "terminal": False,
    }
    errors = validate_policy_record(record)
    assert errors == [], f"Valid record has errors: {errors}"


def test_policy_record_missing_required_field():
    record = {
        "schema_version": "wqt-policy-v0.1",
        "framework": "qiskit",
        # missing challenge_id
        "state_id": "s0",
        "next_state_id": "s1",
        "step_index": 0,
        "stage": "layout",
        "action": {"stage": "layout", "name": "sabre", "parameters": {}},
        "success": True,
        "selectable": True,
        "verification": {},
        "metrics_before": {},
        "metrics_after": {},
        "kept_in_beam": True,
        "terminal": False,
    }
    errors = validate_policy_record(record)
    assert len(errors) > 0, "Should detect missing challenge_id"


def test_policy_record_wrong_schema_version():
    record = {
        "schema_version": "wqt-policy-v0.2",  # wrong version
        "framework": "qiskit",
        "challenge_id": "test-001",
        "state_id": "s0",
        "next_state_id": "s1",
        "step_index": 0,
        "stage": "layout",
        "action": {"stage": "layout", "name": "sabre", "parameters": {}},
        "success": True,
        "selectable": True,
        "verification": {},
        "metrics_before": {},
        "metrics_after": {},
        "kept_in_beam": True,
        "terminal": False,
    }
    errors = validate_policy_record(record)
    assert len(errors) > 0, "Should detect wrong schema version"


# --- Pareto utilities ---

def test_pareto_dominates_basic():
    obj = (Objective("depth"), Objective("size"))
    a = {"depth": 4, "size": 10}
    b = {"depth": 6, "size": 12}
    assert pareto_dominates(a, b, obj), "a should dominate b"
    assert not pareto_dominates(b, a, obj), "b should not dominate a"


def test_pareto_front_incomparable():
    obj = (Objective("depth"), Objective("size"))
    items = [
        {"depth": 4, "size": 10},
        {"depth": 6, "size": 8},
        {"depth": 8, "size": 12},
    ]
    front = pareto_front(items, lambda x: x, obj)
    assert items[2] not in front, "dominated item should not be in front"
    assert items[0] in front
    assert items[1] in front


# --- Beam search determinism ---

def test_beam_search_deterministic_rerun():
    search = DeterministicBeamSearch(
        stages=("layout", "routing"),
        beam_width=2,
        objectives=(Objective("cost"),),
    )

    def actions(stage, prefix):
        return [Action(stage, "x"), Action(stage, "y"), Action(stage, "z")]

    def evaluate(prefix):
        score = sum(hash(a.name) % 5 for a in prefix)
        return Evaluation(success=True, metrics={"cost": score}, verification={"equivalence": "exact"})

    r1 = search.run(challenge_id="c", actions=actions, evaluate=evaluate)
    r2 = search.run(challenge_id="c", actions=actions, evaluate=evaluate)
    assert r1.best.state_id == r2.best.state_id, "beam search must be deterministic"
    assert [s.state_id for s in r1.states] == [s.state_id for s in r2.states]


def test_beam_search_retains_pruned_actions():
    search = DeterministicBeamSearch(
        stages=("a", "b"),
        beam_width=1,
        objectives=(Objective("cost"),),
    )

    def actions(stage, prefix):
        return [Action(stage, "good"), Action(stage, "bad")]

    def evaluate(prefix):
        score = sum(0 if a.name == "good" else 100 for a in prefix)
        return Evaluation(success=True, metrics={"cost": score}, verification={"equivalence": "exact"})

    result = search.run(challenge_id="c", actions=actions, evaluate=evaluate)
    pruned = [s for s in result.states if not s.kept and s.evaluation is not None]
    assert len(pruned) > 0, "pruned actions must be retained in states"
    records = result.records(framework="test")
    pruned_records = [r for r in records if not r["kept_in_beam"]]
    assert len(pruned_records) > 0, "pruned actions must appear in records"


# --- Equivalence semantics ---

def test_equivalence_kinds_distinct():
    assert EquivalenceKind.EXACT != EquivalenceKind.UNKNOWN
    assert EquivalenceKind.UNKNOWN != EquivalenceKind.INVALID
    assert EquivalenceKind.SAME_PROBLEM_DIFFERENT_DYNAMICS != EquivalenceKind.EXACT


def test_search_state_kind_exists():
    assert RepresentationKind.SEARCH_STATE.value == "search_state"
