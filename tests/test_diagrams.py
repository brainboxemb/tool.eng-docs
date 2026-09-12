from importlib.resources import files
from pathlib import Path
import json
import xml.etree.ElementTree as ET

import pytest

from eng_docs.diagrams import generate, load_yaml, validate_refs, validate_source


FIXTURES = Path(__file__).parent / "fixtures"
PACKAGE = files("eng_docs")
SCHEMA = Path(str(PACKAGE.joinpath("schemas/diagram.schema.json")))
THEME = Path(str(PACKAGE.joinpath("themes/default.yaml")))


def _render_fixture(tmp_path, fixture_name):
    source = tmp_path / "source"
    source.mkdir()
    fixture = FIXTURES / fixture_name
    (source / fixture.name).write_text(fixture.read_text(encoding="utf-8"), encoding="utf-8")
    out = tmp_path / "out"
    generate(source, SCHEMA, THEME, out)
    return out


def test_simple_flow_generates_parseable_deterministic_outputs(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "simple-flow.yaml").write_text((FIXTURES / "simple-flow.yaml").read_text(encoding="utf-8"), encoding="utf-8")

    first = tmp_path / "first"
    second = tmp_path / "second"
    generate(source, SCHEMA, THEME, first)
    generate(source, SCHEMA, THEME, second)

    svg = first / "simple-flow.svg"
    drawio = first / "simple-flow.drawio"
    ET.parse(svg)
    ET.parse(drawio)

    assert "Source" in svg.read_text(encoding="utf-8")
    assert "Target" in drawio.read_text(encoding="utf-8")
    assert svg.read_bytes() == (second / "simple-flow.svg").read_bytes()
    assert drawio.read_bytes() == (second / "simple-flow.drawio").read_bytes()


def test_layered_fixture_preserves_groups_and_semantic_labels(tmp_path):
    out = _render_fixture(tmp_path, "layered-architecture.yaml")
    svg = out / "layered-architecture.svg"
    drawio = out / "layered-architecture.drawio"

    ET.parse(svg)
    tree = ET.parse(drawio)
    xml = drawio.read_text(encoding="utf-8")

    assert "Interface layer" in svg.read_text(encoding="utf-8")
    assert "Application coordinator" in xml
    assert tree.getroot().tag == "mxfile"
    assert tree.findall(".//mxCell[@id='group-interface-layer']")
    assert tree.findall(".//mxCell[@id='coordinator']")


def test_routing_fixture_keeps_waypoints_anchors_dashed_edges_and_labels(tmp_path):
    out = _render_fixture(tmp_path, "routing-stress.yaml")
    svg = out / "routing-stress.svg"
    drawio = out / "routing-stress.drawio"

    ET.parse(svg)
    tree = ET.parse(drawio)
    svg_text = svg.read_text(encoding="utf-8")
    drawio_text = drawio.read_text(encoding="utf-8")

    assert "routed request" in svg_text
    assert 'stroke-dasharray="7 5"' in svg_text
    assert "dashed=1" in drawio_text
    assert "exitX=1" in drawio_text
    assert "entryX=0" in drawio_text
    assert len(tree.findall(".//Array[@as='points']/mxPoint")) >= 8


def test_missing_edge_reference_is_rejected():
    data = load_yaml(FIXTURES / "simple-flow.yaml")
    data["edges"][0]["to"] = "missing"
    with pytest.raises(ValueError, match="edge references missing node"):
        validate_refs(data, load_yaml(THEME), FIXTURES / "simple-flow.yaml")


def test_missing_group_reference_is_rejected():
    data = load_yaml(FIXTURES / "layered-architecture.yaml")
    data["nodes"][0]["group"] = "missing-group"
    with pytest.raises(ValueError, match="references missing group"):
        validate_refs(data, load_yaml(THEME), FIXTURES / "layered-architecture.yaml")


def test_duplicate_node_id_is_rejected():
    data = load_yaml(FIXTURES / "simple-flow.yaml")
    data["nodes"].append(dict(data["nodes"][0]))
    with pytest.raises(ValueError, match="duplicate node id"):
        validate_refs(data, load_yaml(THEME), FIXTURES / "simple-flow.yaml")


def test_duplicate_group_id_is_rejected():
    data = load_yaml(FIXTURES / "layered-architecture.yaml")
    data["groups"].append(dict(data["groups"][0]))
    with pytest.raises(ValueError, match="duplicate group id"):
        validate_refs(data, load_yaml(THEME), FIXTURES / "layered-architecture.yaml")


def test_unknown_kind_is_rejected():
    data = load_yaml(FIXTURES / "simple-flow.yaml")
    data["nodes"][0]["kind"] = "unknown-kind"
    with pytest.raises(ValueError, match="unknown kind"):
        validate_refs(data, load_yaml(THEME), FIXTURES / "simple-flow.yaml")


def test_schema_invalid_source_is_rejected():
    data = load_yaml(FIXTURES / "simple-flow.yaml")
    del data["diagram"]["width"]
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="invalid diagram source"):
        validate_source(data, schema, FIXTURES / "simple-flow.yaml")


def test_invalid_anchor_position_is_rejected():
    data = load_yaml(FIXTURES / "simple-flow.yaml")
    data["edges"][0]["from_anchor"] = {"side": "right", "position": 1.5}
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="invalid diagram source"):
        validate_source(data, schema, FIXTURES / "simple-flow.yaml")
