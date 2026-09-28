from pathlib import Path

import pytest

from eng_docs.engineering_graph import build_graph, render_review


ROOT = Path(__file__).resolve().parents[1]


def test_domain_neutral_example_builds_deterministically():
    kwargs = dict(
        root=ROOT,
        docs_root=Path("examples/graph/docs"),
        diagrams_root=Path("examples/graph/diagrams"),
        model_path=Path("examples/graph/model.yml"),
        source_revision="example-sha",
    )
    first = build_graph(**kwargs)
    second = build_graph(**kwargs)

    assert first == second
    assert first["object_count"] == 4
    assert first["relation_count"] == 3
    assert [item["id"] for item in first["objects"]] == ["GOAL-1", "REQ-1", "Service", "VC-1"]
    assert {(item["from"], item["type"], item["to"]) for item in first["relations"]} == {
        ("REQ-1", "derived_from", "GOAL-1"),
        ("Service", "satisfies", "REQ-1"),
        ("VC-1", "verifies", "REQ-1"),
    }

    review = render_review(first)
    assert "### Authored input" in review
    assert "### Generated incoming" in review
    assert "satisfies <- **Service**" in review
    assert "verifies <- **VC-1**" in review


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_duplicate_object_id_fails(tmp_path):
    write(tmp_path / "docs/a.md", '<a id="REQ-1"></a>\n<!-- eng {"type":"requirement"} -->\n')
    write(tmp_path / "docs/b.md", '<a id="REQ-1"></a>\n<!-- eng {"type":"requirement"} -->\n')

    with pytest.raises(ValueError, match="duplicate engineering id REQ-1"):
        build_graph(tmp_path, Path("docs"))


def test_unknown_relation_target_fails(tmp_path):
    write(
        tmp_path / "docs/a.md",
        '<a id="REQ-1"></a>\n'
        '<!-- eng {"type":"requirement","relations":{"derived_from":["Missing"]}} -->\n',
    )

    with pytest.raises(ValueError, match="unknown derived_from target Missing"):
        build_graph(tmp_path, Path("docs"))


def test_unknown_relation_extension_owner_fails(tmp_path):
    write(
        tmp_path / "docs/a.md",
        '<!-- eng-rel {"id":"MissingDesign","relations":{"satisfies":[]}} -->\n',
    )

    with pytest.raises(ValueError, match="eng-rel owner does not exist: MissingDesign"):
        build_graph(tmp_path, Path("docs"))


def test_consumer_model_rejects_invalid_relation_source_type(tmp_path):
    write(
        tmp_path / "model.yml",
        "schema_version: 1\n"
        "object_types: [requirement, design]\n"
        "relations:\n"
        "  satisfies:\n"
        "    from: [design]\n"
        "    to: [requirement]\n",
    )
    write(
        tmp_path / "docs/a.md",
        '<a id="REQ-1"></a>\n'
        '<!-- eng {"type":"requirement","relations":{"satisfies":["REQ-2"]}} -->\n'
        '<a id="REQ-2"></a>\n'
        '<!-- eng {"type":"requirement"} -->\n',
    )

    with pytest.raises(ValueError, match="does not allow source type requirement"):
        build_graph(tmp_path, Path("docs"), model_path=Path("model.yml"))


def test_consumer_model_rejects_unknown_relation_type(tmp_path):
    write(
        tmp_path / "model.yml",
        "schema_version: 1\n"
        "object_types: [requirement]\n"
        "relations: {}\n",
    )
    write(
        tmp_path / "docs/a.md",
        '<a id="REQ-1"></a>\n'
        '<!-- eng {"type":"requirement","relations":{"unknown":["REQ-2"]}} -->\n'
        '<a id="REQ-2"></a>\n'
        '<!-- eng {"type":"requirement"} -->\n',
    )

    with pytest.raises(ValueError, match="unknown relation type unknown"):
        build_graph(tmp_path, Path("docs"), model_path=Path("model.yml"))
