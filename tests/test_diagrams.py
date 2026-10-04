from importlib.resources import files
from pathlib import Path
import json
import xml.etree.ElementTree as ET

import pytest

from eng_docs.diagrams import generate, load_yaml, validate_refs, validate_sequence_refs, validate_source


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


def test_engineering_object_id_is_preserved_in_svg_and_drawio(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    example = Path(__file__).parents[1] / "examples" / "minimal-flow.yaml"
    (source / example.name).write_text(
        example.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    out = tmp_path / "out"
    generate(source, SCHEMA, THEME, out)

    svg_root = ET.parse(out / "minimal-flow.svg").getroot()
    identities = {
        element.attrib["data-engineering-id"]
        for element in svg_root.iter()
        if element.tag.endswith("g") and "data-engineering-id" in element.attrib
    }
    assert identities == {"example.client", "example.service"}

    drawio_root = ET.parse(out / "minimal-flow.drawio")
    client = drawio_root.find(".//mxCell[@id='client']")
    service = drawio_root.find(".//mxCell[@id='service']")
    assert client is not None
    assert service is not None
    assert client.attrib["data-engineering-id"] == "example.client"
    assert service.attrib["data-engineering-id"] == "example.service"


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


def test_automatic_routing_avoids_intermediate_component_in_svg_and_drawio(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    example = Path(__file__).parents[1] / "examples" / "obstacle-routing.yaml"
    (source / example.name).write_text(
        example.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    out = tmp_path / "out"
    generate(source, SCHEMA, THEME, out)

    svg_root = ET.parse(out / "obstacle-routing.svg").getroot()
    polylines = [
        element
        for element in svg_root.iter()
        if element.tag.endswith("polyline")
    ]
    assert len(polylines) == 1
    svg_points = [
        tuple(float(value) for value in pair.split(","))
        for pair in polylines[0].attrib["points"].split()
    ]
    assert len(svg_points) >= 6

    blocker = (310.0, 135.0, 450.0, 225.0)
    left, top, right, bottom = blocker
    for first, second in zip(svg_points, svg_points[1:]):
        if first[0] == second[0]:
            assert not (
                left < first[0] < right
                and max(min(first[1], second[1]), top)
                < min(max(first[1], second[1]), bottom)
            )
        elif first[1] == second[1]:
            assert not (
                top < first[1] < bottom
                and max(min(first[0], second[0]), left)
                < min(max(first[0], second[0]), right)
            )
        else:
            pytest.fail("generated obstacle route must remain orthogonal")

    drawio_root = ET.parse(out / "obstacle-routing.drawio")
    edge = drawio_root.find(".//mxCell[@id='edge-1']")
    assert edge is not None
    assert "exitX=1" in edge.attrib["style"]
    assert "entryX=0" in edge.attrib["style"]
    waypoints = edge.findall("./mxGeometry/Array[@as='points']/mxPoint")
    assert len(waypoints) >= 4
    assert any(
        float(point.attrib["y"]) < top or float(point.attrib["y"]) > bottom
        for point in waypoints
    )


def test_single_authored_anchor_aligns_inferred_opposite_anchor(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / "aligned-anchor.yaml").write_text(
        """diagram:
  id: aligned-anchor
  title: Aligned anchor
  width: 650
  height: 360

groups: []

nodes:
  - id: source
    label: Source
    kind: component
    layout: {x: 400, y: 80, w: 100, h: 50}
  - id: target
    label: Target
    kind: service
    layout: {x: 50, y: 240, w: 500, h: 60}

edges:
  - from: source
    to: target
    from_anchor: {side: bottom, position: 0.75}
""",
        encoding="utf-8",
    )

    out = tmp_path / "out"
    generate(source, SCHEMA, THEME, out)

    svg_root = ET.parse(out / "aligned-anchor.svg").getroot()
    polyline = next(
        element
        for element in svg_root.iter()
        if element.tag.endswith("polyline")
    )
    svg_points = [
        tuple(float(value) for value in pair.split(","))
        for pair in polyline.attrib["points"].split()
    ]
    assert svg_points == [(475.0, 130.0), (475.0, 240.0)]

    drawio_root = ET.parse(out / "aligned-anchor.drawio")
    edge = drawio_root.find(".//mxCell[@id='edge-1']")
    assert edge is not None
    assert "exitX=0.75;exitY=1" in edge.attrib["style"]
    assert "entryX=0.85;entryY=0" in edge.attrib["style"]


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
    nested_identities = {
        element.attrib["data-engineering-id"]
        for element in root.iter()
        if element.tag.endswith("g") and "data-engineering-id" in element.attrib
    }
    assert {"example.interface", "example.terminals", "example.worker"}.issubset(nested_identities)
    interface_group = tree.find(".//mxCell[@id='group-interface-layer']")
    assert interface_group is not None
    assert interface_group.attrib["data-engineering-id"] == "example.interface"
    assert "stable boundary" in interface_group.attrib["value"]
    assert "boundaryId" not in interface_group.attrib["value"]
    assert "state" not in interface_group.attrib["value"]
    assert "stable boundary" in svg_text
    assert "- boundaryId" in svg_text
    assert "- state" in svg_text
    assert 'data-group-properties="true"' in svg_text
    property_rect = next(
        element
        for element in root.iter()
        if element.tag.endswith("rect")
        and element.attrib.get("data-group-properties") == "true"
    )
    assert property_rect.attrib["x"] == "90.0"
    assert property_rect.attrib["width"] == "260.0"

    property_cell = tree.find(".//mxCell[@id='group-interface-layer-properties']")
    assert property_cell is not None
    assert "- boundaryId" in property_cell.attrib["value"]
    assert "- state" in property_cell.attrib["value"]
    assert "shape=component" not in property_cell.attrib["style"]
    assert "fillColor=#ffffff" in property_cell.attrib["style"]
    property_geometry = property_cell.find("mxGeometry")
    assert property_geometry is not None
    assert property_geometry.attrib["width"] == "260"
    entrypoints = tree.find(".//mxCell[@id='entrypoints']")
    service_cell = tree.find(".//mxCell[@id='service']")
    assert entrypoints is not None
    assert service_cell is not None
    assert 'data-engineering-id="example.terminals"' in entrypoints.attrib["value"]
    assert 'data-engineering-id="example.worker"' in service_cell.attrib["value"]
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



def test_polygon_group_example_renders_native_svg_and_drawio_polygon(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    example = Path(__file__).parents[1] / "examples" / "polygon-group.yaml"
    (source / example.name).write_text(
        example.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    first = tmp_path / "first"
    second = tmp_path / "second"
    generate(source, SCHEMA, THEME, first)
    generate(source, SCHEMA, THEME, second)

    svg = first / "polygon-group.svg"
    drawio = first / "polygon-group.drawio"
    svg_root = ET.parse(svg).getroot()
    drawio_tree = ET.parse(drawio)

    rounded_paths = [
        element
        for element in svg_root.iter()
        if element.tag.endswith("path")
        and element.attrib.get("data-outline") == "polygon"
    ]
    sharp_polygons = [
        element
        for element in svg_root.iter()
        if element.tag.endswith("polygon")
        and element.attrib.get("data-outline") == "polygon"
    ]
    assert len(rounded_paths) == 1
    assert len(sharp_polygons) == 1
    assert rounded_paths[0].attrib["d"].startswith("M ")
    assert " Q " in rounded_paths[0].attrib["d"]
    assert sharp_polygons[0].attrib["points"].startswith("70.0,275.1")
    assert sharp_polygons[0].attrib["stroke-linejoin"] == "round"

    upper = drawio_tree.find(".//mxCell[@id='group-upper-area']")
    lower = drawio_tree.find(".//mxCell[@id='group-lower-area']")
    assert upper is not None
    assert lower is not None
    assert "shape=mxgraph.basic.polygon;" in upper.attrib["style"]
    assert "polyCoords=[[0.0,0.0],[1.0,0.0]" in upper.attrib["style"]
    assert "rounded=1;" in upper.attrib["style"]
    assert "rounded=1;" not in lower.attrib["style"]
    assert "polyline=0;" in lower.attrib["style"]
    assert "spacingTop=53;" in lower.attrib["style"]

    lower_label = next(
        element
        for element in svg_root.iter()
        if element.tag.endswith("text") and element.text == "Lower responsibility"
    )
    assert float(lower_label.attrib["y"]) == 297.0

    assert svg.read_bytes() == (second / "polygon-group.svg").read_bytes()
    assert drawio.read_bytes() == (second / "polygon-group.drawio").read_bytes()


def test_group_label_offset_rejects_negative_values():
    data = load_yaml(FIXTURES / "layered-architecture.yaml")
    data["groups"][0]["label_offset"] = {"x": 0, "y": -1}
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="invalid diagram source"):
        validate_source(data, schema, FIXTURES / "layered-architecture.yaml")


def test_polygon_group_rejects_notation():
    data = load_yaml(FIXTURES / "layered-architecture.yaml")
    data["groups"][0]["outline"] = {
        "points": [
            {"x": 0.0, "y": 0.0},
            {"x": 1.0, "y": 0.0},
            {"x": 1.0, "y": 1.0},
        ]
    }
    data["groups"][0]["notation"] = "component"
    with pytest.raises(ValueError, match="cannot combine outline with notation"):
        validate_refs(data, load_yaml(THEME), FIXTURES / "layered-architecture.yaml")


def test_polygon_group_requires_distinct_points():
    data = load_yaml(FIXTURES / "layered-architecture.yaml")
    data["groups"][0]["outline"] = {
        "points": [
            {"x": 0.0, "y": 0.0},
            {"x": 0.0, "y": 0.0},
            {"x": 1.0, "y": 1.0},
        ]
    }
    with pytest.raises(ValueError, match="at least three distinct points"):
        validate_refs(data, load_yaml(THEME), FIXTURES / "layered-architecture.yaml")


def test_polygon_group_rejects_negative_corner_radius():
    data = load_yaml(FIXTURES / "layered-architecture.yaml")
    data["groups"][0]["outline"] = {
        "corner_radius": -1,
        "points": [
            {"x": 0.0, "y": 0.0},
            {"x": 1.0, "y": 0.0},
            {"x": 1.0, "y": 1.0},
        ],
    }
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="invalid diagram source"):
        validate_source(data, schema, FIXTURES / "layered-architecture.yaml")


def test_polygon_group_rejects_point_outside_layout_box():
    data = load_yaml(FIXTURES / "layered-architecture.yaml")
    data["groups"][0]["outline"] = {
        "points": [
            {"x": 0.0, "y": 0.0},
            {"x": 1.2, "y": 0.0},
            {"x": 1.0, "y": 1.0},
        ]
    }
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="invalid diagram source"):
        validate_source(data, schema, FIXTURES / "layered-architecture.yaml")


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


def test_group_object_id_participates_in_duplicate_validation():
    data = load_yaml(Path(__file__).parents[1] / "examples" / "structured-layer.yaml")
    data["nodes"][0]["object_id"] = data["groups"][0]["object_id"]
    with pytest.raises(ValueError, match="duplicate diagram object_id"):
        validate_refs(data, load_yaml(THEME), FIXTURES / "structured-layer.yaml")


def test_non_positive_group_properties_width_is_rejected_by_schema():
    data = load_yaml(Path(__file__).parents[1] / "examples" / "structured-layer.yaml")
    data["groups"][0]["properties_width"] = 0
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="invalid diagram source"):
        validate_source(data, schema, FIXTURES / "structured-layer.yaml")


def test_empty_group_properties_are_rejected_by_schema():
    data = load_yaml(Path(__file__).parents[1] / "examples" / "structured-layer.yaml")
    data["groups"][0]["properties"] = []
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="invalid diagram source"):
        validate_source(data, schema, FIXTURES / "structured-layer.yaml")


def test_empty_group_property_is_rejected_by_schema():
    data = load_yaml(Path(__file__).parents[1] / "examples" / "structured-layer.yaml")
    data["groups"][0]["properties"] = [""]
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="invalid diagram source"):
        validate_source(data, schema, FIXTURES / "structured-layer.yaml")


def test_empty_group_object_id_is_rejected_by_schema():
    data = load_yaml(Path(__file__).parents[1] / "examples" / "structured-layer.yaml")
    data["groups"][0]["object_id"] = ""
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="invalid diagram source"):
        validate_source(data, schema, FIXTURES / "structured-layer.yaml")


def test_duplicate_node_object_id_is_rejected():
    data = load_yaml(FIXTURES / "simple-flow.yaml")
    data["nodes"][0]["object_id"] = "example.shared"
    data["nodes"][1]["object_id"] = "example.shared"
    with pytest.raises(ValueError, match="duplicate diagram object_id"):
        validate_refs(data, load_yaml(THEME), FIXTURES / "simple-flow.yaml")


def test_duplicate_nested_item_object_id_is_rejected():
    data = load_yaml(Path(__file__).parents[1] / "examples" / "structured-layer.yaml")
    data["nodes"][0]["items"][1]["object_id"] = "example.shared"
    data["nodes"][1]["items"][0]["object_id"] = "example.shared"
    with pytest.raises(ValueError, match="duplicate diagram object_id"):
        validate_refs(data, load_yaml(THEME), FIXTURES / "structured-layer.yaml")


def test_empty_nested_item_object_id_is_rejected_by_schema():
    data = load_yaml(Path(__file__).parents[1] / "examples" / "structured-layer.yaml")
    data["nodes"][0]["items"][1]["object_id"] = ""
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="invalid diagram source"):
        validate_source(data, schema, FIXTURES / "structured-layer.yaml")


def test_empty_node_object_id_is_rejected_by_schema():
    data = load_yaml(FIXTURES / "simple-flow.yaml")
    data["nodes"][0]["object_id"] = ""
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="invalid diagram source"):
        validate_source(data, schema, FIXTURES / "simple-flow.yaml")


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


def test_sequence_example_generates_native_uml_deterministic_outputs(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    example = Path(__file__).parents[1] / "examples" / "sequence-flow.yaml"
    (source / example.name).write_text(
        example.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    first = tmp_path / "first"
    second = tmp_path / "second"
    generate(source, SCHEMA, THEME, first)
    generate(source, SCHEMA, THEME, second)

    svg = first / "sequence-flow.svg"
    drawio = first / "sequence-flow.drawio"
    svg_root = ET.parse(svg).getroot()
    drawio_root = ET.parse(drawio)

    svg_text = svg.read_text(encoding="utf-8")
    drawio_text = drawio.read_text(encoding="utf-8")

    assert "Asynchronous work sequence" in svg_text
    assert ">process queued work</text>" in svg_text
    assert ">using current state</text>" in svg_text
    assert 'font-size="13"' in svg_text
    assert "stored" in drawio_text
    assert len([
        element for element in svg_root.iter()
        if element.attrib.get("data-sequence-lifeline")
    ]) == 3
    assert len([
        element for element in svg_root.iter()
        if element.attrib.get("data-sequence-message")
    ]) == 5
    assert len([
        element for element in svg_root.iter()
        if element.attrib.get("data-sequence-activation")
    ]) >= 2
    assert any(
        element.attrib.get("data-sequence-self-message") == "true"
        for element in svg_root.iter()
    )

    lifeline = drawio_root.find(".//mxCell[@id='sequence-participant-worker']")
    assert lifeline is not None
    assert "shape=umlLifeline" in lifeline.attrib["style"]
    assert "perimeter=lifelinePerimeter" in lifeline.attrib["style"]

    activations = [
        element for element in drawio_root.findall(".//mxCell")
        if element.attrib.get("id", "").startswith("sequence-activation-")
    ]
    assert len(activations) >= 2
    assert all("points=[]" in item.attrib["style"] for item in activations)
    assert all("shape=mxgraph.uml.activation" not in item.attrib["style"] for item in activations)

    persisted = drawio_root.find(".//mxCell[@id='sequence-message-3']")
    returned = drawio_root.find(".//mxCell[@id='sequence-message-4']")
    async_message = drawio_root.find(".//mxCell[@id='sequence-message-1']")
    self_message = drawio_root.find(".//mxCell[@id='sequence-message-2']")
    assert persisted is not None
    assert returned is not None
    assert async_message is not None
    assert self_message is not None
    assert "endArrow=block" in persisted.attrib["style"]
    assert "endArrow=open" in async_message.attrib["style"]
    assert "dashed=1" in returned.attrib["style"]
    assert "orthogonalEdgeStyle" in self_message.attrib["style"]
    assert "fontSize=13" in self_message.attrib["style"]
    assert "<br>" in self_message.attrib["value"]

    lifeline_svg = next(
        element for element in svg_root.iter()
        if element.attrib.get("data-sequence-lifeline") == "worker"
    )
    assert float(lifeline_svg.attrib["y2"]) < 500

    wrapped_text = [
        element.text
        for element in svg_root.iter()
        if element.tag.endswith("text")
    ]
    assert "persist validated immutable" in wrapped_text
    assert "work item to durable store" in wrapped_text

    assert svg.read_bytes() == (second / "sequence-flow.svg").read_bytes()
    assert drawio.read_bytes() == (second / "sequence-flow.drawio").read_bytes()


def test_sequence_rejects_missing_participant_reference():
    data = load_yaml(Path(__file__).parents[1] / "examples" / "sequence-flow.yaml")
    data["messages"][0]["to"] = "missing"
    with pytest.raises(ValueError, match="missing participant"):
        validate_sequence_refs(
            data,
            load_yaml(THEME),
            Path("sequence-flow.yaml"),
        )


def test_sequence_rejects_duplicate_participant_id():
    data = load_yaml(Path(__file__).parents[1] / "examples" / "sequence-flow.yaml")
    data["participants"][1]["id"] = data["participants"][0]["id"]
    with pytest.raises(ValueError, match="duplicate sequence participant id"):
        validate_sequence_refs(
            data,
            load_yaml(THEME),
            Path("sequence-flow.yaml"),
        )


def test_sequence_rejects_unknown_participant_kind():
    data = load_yaml(Path(__file__).parents[1] / "examples" / "sequence-flow.yaml")
    data["participants"][0]["kind"] = "not-a-theme-kind"
    with pytest.raises(ValueError, match="unknown kind"):
        validate_sequence_refs(
            data,
            load_yaml(THEME),
            Path("sequence-flow.yaml"),
        )


def test_sequence_accepts_self_message():
    data = load_yaml(Path(__file__).parents[1] / "examples" / "sequence-flow.yaml")
    validate_sequence_refs(
        data,
        load_yaml(THEME),
        Path("sequence-flow.yaml"),
    )


def test_ui_wireframe_example_generates_editable_svg_and_drawio(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    example = Path(__file__).parents[1] / "examples" / "ui-wireframe.yaml"
    (source / example.name).write_text(
        example.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    first = tmp_path / "first"
    second = tmp_path / "second"
    generate(source, SCHEMA, THEME, first)
    generate(source, SCHEMA, THEME, second)

    svg = first / "ui-wireframe.svg"
    drawio = first / "ui-wireframe.drawio"
    svg_root = ET.parse(svg).getroot()
    drawio_root = ET.parse(drawio)

    notations = {
        element.attrib["data-notation"]
        for element in svg_root.iter()
        if "data-notation" in element.attrib
        and element.attrib["data-notation"].startswith("wireframe-")
    }
    assert notations == {
        "wireframe-panel",
        "wireframe-tabs",
        "wireframe-input",
        "wireframe-button",
        "wireframe-table",
        "wireframe-status",
    }

    location = drawio_root.find(".//mxCell[@id='location']")
    submit = drawio_root.find(".//mxCell[@id='submit']")
    history = drawio_root.find(".//mxCell[@id='history']")
    status = drawio_root.find(".//mxCell[@id='connection']")
    tabs = drawio_root.find(".//mxCell[@id='tabs']")

    assert location is not None
    assert submit is not None
    assert history is not None
    assert status is not None
    assert tabs is not None

    assert location.attrib["data-notation"] == "wireframe-input"
    assert "verticalAlign=top" in location.attrib["style"]
    assert "border:1px solid" in location.attrib["value"]
    assert submit.attrib["data-notation"] == "wireframe-button"
    assert "arcSize=18" in submit.attrib["style"]
    assert history.attrib["data-notation"] == "wireframe-table"
    assert "sample-001" in history.attrib["value"]
    assert status.attrib["data-notation"] == "wireframe-status"
    assert "arcSize=50" in status.attrib["style"]
    assert tabs.attrib["data-notation"] == "wireframe-tabs"
    assert "<b>Control</b>" in tabs.attrib["value"]
    assert "<b>Overview</b>" not in tabs.attrib["value"]

    assert svg.read_bytes() == (second / "ui-wireframe.svg").read_bytes()
    assert drawio.read_bytes() == (second / "ui-wireframe.drawio").read_bytes()
