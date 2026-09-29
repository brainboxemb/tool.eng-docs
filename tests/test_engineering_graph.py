import json
from pathlib import Path

import pytest

from eng_docs.engineering_graph import build_graph, render_review


ROOT = Path(__file__).resolve().parents[1]
NEEDS = ROOT / "examples/graph/needs.json"
DIAGRAMS = ROOT / "examples/graph/diagrams"
RELATIONS = ["derived_from", "satisfies", "verifies"]


def test_domain_neutral_needs_example_builds_deterministically():
    kwargs = dict(
        needs_path=NEEDS,
        diagrams_root=DIAGRAMS,
        relation_types=RELATIONS,
        source_revision="example-sha",
    )
    first = build_graph(**kwargs)
    second = build_graph(**kwargs)

    assert first == second
    assert first["source_graph"] == {
        "kind": "sphinx-needs",
        "project": "tool.eng-docs graph example",
        "version": "1.0",
    }
    assert first["object_count"] == 5
    assert first["relation_count"] == 3
    assert [item["id"] for item in first["objects"]] == [
        "GOAL-1",
        "REQ-1",
        "Service",
        "VC-1",
        "Worker",
    ]
    assert {
        (item["from"], item["type"], item["to"])
        for item in first["relations"]
    } == {
        ("REQ-1", "derived_from", "GOAL-1"),
        ("Service", "satisfies", "REQ-1"),
        ("VC-1", "verifies", "REQ-1"),
    }

    service = next(item for item in first["objects"] if item["id"] == "Service")
    assert len(service["diagram_refs"]) == 1
    assert service["diagram_refs"][0]["diagram_id"] == "graph-example"
    assert service["diagram_refs"][0]["node_id"] == "service"

    worker = next(item for item in first["objects"] if item["id"] == "Worker")
    assert len(worker["diagram_refs"]) == 1
    assert worker["diagram_refs"][0]["diagram_id"] == "graph-example"
    assert worker["diagram_refs"][0]["node_id"] == "service"

    review = render_review(first)
    assert "### Authored outgoing" in review
    assert "### Generated incoming" in review
    assert "### Diagram references" in review
    assert "satisfies <- **Service**" in review
    assert "verifies <- **VC-1**" in review


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def load_example() -> dict:
    return json.loads(NEEDS.read_text(encoding="utf-8"))


def test_only_requested_relation_fields_are_normalized():
    graph = build_graph(
        NEEDS,
        relation_types=["derived_from"],
        source_revision="example-sha",
    )

    assert graph["relation_count"] == 1
    assert graph["relations"][0]["type"] == "derived_from"


def test_unknown_relation_target_fails(tmp_path):
    data = load_example()
    data["versions"]["1.0"]["needs"]["REQ-1"]["derived_from"] = ["MISSING"]
    path = tmp_path / "needs.json"
    write_json(path, data)

    with pytest.raises(ValueError, match="unknown derived_from target MISSING"):
        build_graph(path, relation_types=["derived_from"])


def test_unknown_diagram_object_fails(tmp_path):
    diagrams = tmp_path / "diagrams"
    diagrams.mkdir()
    (diagrams / "system.yaml").write_text(
        "diagram:\n"
        "  id: bad-diagram\n"
        "nodes:\n"
        "  - id: missing\n"
        "    object_id: MissingObject\n"
        "    label: Missing\n"
        "    kind: service\n"
        "    layout: {x: 10, y: 10, w: 100, h: 50}\n"
        "groups: []\n"
        "edges: []\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="does not resolve to a Need"):
        build_graph(NEEDS, diagrams_root=diagrams)


def test_unknown_nested_diagram_object_fails(tmp_path):
    diagrams = tmp_path / "diagrams"
    diagrams.mkdir()
    (diagrams / "system.yaml").write_text(
        "diagram:\n"
        "  id: bad-nested-diagram\n"
        "nodes:\n"
        "  - id: container\n"
        "    label: Container\n"
        "    kind: service\n"
        "    items:\n"
        "      - label: Missing\n"
        "        object_id: MissingNestedObject\n"
        "    layout: {x: 10, y: 10, w: 100, h: 50}\n"
        "groups: []\n"
        "edges: []\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="does not resolve to a Need"):
        build_graph(NEEDS, diagrams_root=diagrams)


def test_mismatched_embedded_need_id_fails(tmp_path):
    data = load_example()
    data["versions"]["1.0"]["needs"]["REQ-1"]["id"] = "OTHER"
    path = tmp_path / "needs.json"
    write_json(path, data)

    with pytest.raises(ValueError, match="does not match embedded id"):
        build_graph(path)


def test_repeated_relation_field_fails():
    with pytest.raises(ValueError, match="must not be repeated"):
        build_graph(
            NEEDS,
            relation_types=["derived_from", "derived_from"],
        )
