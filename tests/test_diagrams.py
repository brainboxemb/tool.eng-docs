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

    svg_text = svg.read_text(encoding="utf-8")
    drawio_text = drawio.read_text(encoding="utf-8")
    assert "Source" in svg_text
    assert "secondary explanation" in svg_text
    assert 'font-size="11"' in svg_text
    assert "Target" in drawio_text
    assert "secondary explanation" in drawio_text
    assert "font-size:11px" in drawio_text
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


def test_structured_items_and_group_edge_endpoint_render(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    example = Path(__file__).parents[1] / "examples" / "structured-layer.yaml"
    (source / example.name).write_text(example.read_text(encoding="utf-8"), encoding="utf-8")

    out = tmp_path / "out"
    generate(source, SCHEMA, THEME, out)

    svg = out / "structured-layer.svg"
    drawio = out / "structured-layer.drawio"
    ET.parse(svg)
    tree = ET.parse(drawio)

    svg_text = svg.read_text(encoding="utf-8")
    root = ET.parse(svg).getroot()
    assert "• Browser" in svg_text
    assert "• Terminals" in svg_text
    assert "└─ Local" in svg_text
    assert "└─ Remote" in svg_text
    assert 'data-notation="component"' in svg_text
    component_glyph = next(
        element
        for element in root.iter()
        if element.tag.endswith("g") and element.attrib.get("data-notation") == "component"
    )
    assert any(
        child.tag.endswith("rect") and child.attrib.get("width") == "20"
        for child in component_glyph
    )
    packaging_glyph = next(
        element
        for element in root.iter()
        if element.tag.endswith("g") and element.attrib.get("data-notation") == "packaging-component"
    )
    packaging_body = next(child for child in packaging_glyph if child.tag.endswith("path"))
    # Package tab belongs at the upper-left: rise immediately from the left edge,
    # then run across the tab before dropping back to the body top.
    assert " v-4 h11 l3,4 " in packaging_body.attrib["d"]
    assert " h8 l3,-4 " not in packaging_body.attrib["d"]
    packaging_tabs = [child for child in packaging_glyph if child.tag.endswith("rect")]
    assert len(packaging_tabs) == 2
    assert all(child.attrib.get("width") == "8" for child in packaging_tabs)
    assert all(child.attrib.get("height") == "4" for child in packaging_tabs)
    # Packaging-component is one integrated package/component outline: it must
    # not contain a second complete component body rectangle.
    assert not any(child.attrib.get("width") == "12" for child in packaging_tabs)
    assert svg_text.count('data-notation="packaging-component"') >= 2
    assert "«class»" in svg_text
    assert "- sessionId" in svg_text
    # Structured cards start near the top of their node instead of centering
    # the complete title/subtitle/item stack vertically.
    entry_label = next(element for element in root.iter() if element.tag.endswith("text") and element.text == "Entry points")
    assert float(entry_label.attrib["y"]) < 150

    edge = tree.find(".//mxCell[@id='edge-1']")
    assert edge is not None
    assert edge.attrib["source"] == "entrypoints"
    assert edge.attrib["target"] == "group-application-layer"
    service = tree.find(".//mxCell[@id='service']")
    assert service is not None
    assert "shape=component;" in service.attrib["style"]
    assert "container=1;" in service.attrib["style"]
    package = tree.find(".//mxCell[@id='group-application-layer']")
    assert package is not None
    assert "shape=component;" in package.attrib["style"]
    assert "container=1;" in package.attrib["style"]
    state = tree.find(".//mxCell[@id='state']")
    assert state is not None
    assert "rounded=0;" in state.attrib["style"]
    assert "«class»" in state.attrib["value"]
    assert "- sessionId" in state.attrib["value"]



def test_group_component_notation_remains_backwards_compatible(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    text = (FIXTURES / "layered-architecture.yaml").read_text(encoding="utf-8")
    text = text.replace("kind: group-primary", "kind: group-primary\n    notation: component", 1)
    (source / "layered-architecture.yaml").write_text(text, encoding="utf-8")
    out = tmp_path / "out"
    generate(source, SCHEMA, THEME, out)
    svg_text = (out / "layered-architecture.svg").read_text(encoding="utf-8")
    tree = ET.parse(out / "layered-architecture.drawio")
    assert 'data-notation="component"' in svg_text
    group = tree.find(".//mxCell[@id='group-interface-layer']")
    assert group is not None
    assert "shape=component;" in group.attrib["style"]

def test_missing_edge_reference_is_rejected():
    data = load_yaml(FIXTURES / "simple-flow.yaml")
    data["edges"][0]["to"] = "missing"
    with pytest.raises(ValueError, match="edge references missing endpoint"):
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
