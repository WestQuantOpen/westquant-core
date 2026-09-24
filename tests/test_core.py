from westquant_core import (
    EquivalenceKind,
    RepGraph,
    Representation,
    RepresentationKind,
    TransformationRecord,
)


def test_representation_roundtrip():
    r = Representation(
        id="c0",
        kind=RepresentationKind.CIRCUIT,
        framework="test",
        payload={"n_qubits": 3},
    )
    assert Representation.from_dict(r.to_dict()) == r


def test_repgraph_accepts_valid_dag():
    g = RepGraph("g1")
    a = Representation("a", RepresentationKind.PROBLEM, {"type": "toy"})
    b = Representation("b", RepresentationKind.CIRCUIT, {"depth": 4}, semantic_root="a")
    g.add_representation(a)
    g.add_representation(b)
    g.add_transformation(TransformationRecord(
        id="e1",
        input_id="a",
        output_id="b",
        transform_id="encode.toy",
        transform_version="1",
        equivalence=EquivalenceKind.OBJECTIVE_EQUIVALENT,
    ))
    assert g.validate() == []
    assert g.children("a") == [b]


def test_repgraph_rejects_cycle():
    g = RepGraph("g1")
    a = Representation("a", RepresentationKind.CIRCUIT, {})
    b = Representation("b", RepresentationKind.CIRCUIT, {})
    g.add_representation(a)
    g.add_representation(b)
    g.add_transformation(TransformationRecord(
        "e1", "a", "b", "rewrite.a", "1", EquivalenceKind.EXACT
    ))
    try:
        g.add_transformation(TransformationRecord(
            "e2", "b", "a", "rewrite.b", "1", EquivalenceKind.EXACT
        ))
    except ValueError as exc:
        assert "acyclic" in str(exc)
    else:
        raise AssertionError("cycle was accepted")
