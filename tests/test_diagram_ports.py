from importlib.resources import files
from pathlib import Path
import json
import xml.etree.ElementTree as ET

import pytest

from eng_docs.diagrams import generate, load_yaml, validate_refs, validate_source


PACKAGE = files("eng_docs")
SCHEMA = Path(str(PACKAGE.joinpath("schemas/diagram.schema.json")))
THEME = Path(str(PACKAGE.joinpath("themes/default.yaml")))
EXAMPLE = Path(__file__).parents[1] / "examples" / "interface-ports.yaml"


def test_interface_ports_example_generates_attached_svg_and_drawio_ports(tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    (source / EXAMPLE.name).write_text(
        EXAMPLE.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    first = tmp_path / "first"
    second = tmp_path / "second"
    generate(source, SCHEMA, THEME, first)
    generate(source, SCHEMA, THEME, second)

    svg = first / "interface-ports.svg"
    drawio = first / "interface-ports.drawio"
    svg_root = ET.parse(svg).getroot()
    drawio_root = ET.parse(drawio)

    ports = [
        element
        for element in svg_root.iter()
        if element.tag.endswith("g")
        and element.attrib.get("data-notation") == "port"
    ]
    assert {
        (port.attrib["data-port-id"], port.attrib["data-port-side"])
        for port in ports
    } == {
        ("http", "top"),
        ("events", "top"),
        ("tcp", "top"),
    }

    http_port = next(port for port in ports if port.attrib["data-port-id"] == "http")
    http_rect = next(
        element for element in http_port
        if element.tag.endswith("rect")
    )
    assert float(http_rect.attrib["x"]) == pytest.approx(201.8)
    assert float(http_rect.attrib["y"]) == pytest.approx(185.0)
    assert float(http_rect.attrib["width"]) == pytest.approx(10.0)
    assert float(http_rect.attrib["height"]) == pytest.approx(10.0)
    assert any(
        element.tag.endswith("text") and element.text == "HTTP"
        for element in http_port
    )

    http_cell = drawio_root.find(".//mxCell[@id='remote-adapter-port-http']")
    events_cell = drawio_root.find(".//mxCell[@id='remote-adapter-port-events']")
    tcp_cell = drawio_root.find(".//mxCell[@id='terminal-adapter-port-tcp']")
    assert http_cell is not None
    assert events_cell is not None
    assert tcp_cell is not None

    assert http_cell.attrib["parent"] == "remote-adapter"
    assert http_cell.attrib["data-notation"] == "port"
    assert http_cell.attrib["data-port-id"] == "http"
    assert http_cell.attrib["data-port-side"] == "top"
    assert "portConstraint=north" in http_cell.attrib["style"]
    assert "verticalLabelPosition=top" in http_cell.attrib["style"]

    geometry = http_cell.find("./mxGeometry")
    assert geometry is not None
    assert geometry.attrib["relative"] == "1"
    assert float(geometry.attrib["x"]) == pytest.approx(0.32)
    assert float(geometry.attrib["y"]) == pytest.approx(0.0)
    offset = geometry.find("./mxPoint[@as='offset']")
    assert offset is not None
    assert float(offset.attrib["x"]) == pytest.approx(-5.0)
    assert float(offset.attrib["y"]) == pytest.approx(-5.0)

    assert svg.read_bytes() == (second / "interface-ports.svg").read_bytes()
    assert drawio.read_bytes() == (second / "interface-ports.drawio").read_bytes()


def test_duplicate_port_ids_are_rejected():
    data = load_yaml(EXAMPLE)
    data["nodes"][0]["ports"][1]["id"] = "http"
    with pytest.raises(ValueError, match="duplicate port id"):
        validate_refs(data, load_yaml(THEME), EXAMPLE)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("side", "center"),
        ("position", -0.1),
        ("position", 1.1),
    ],
)
def test_invalid_port_layout_is_rejected_by_schema(field, value):
    data = load_yaml(EXAMPLE)
    data["nodes"][0]["ports"][0][field] = value
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="invalid diagram source"):
        validate_source(data, schema, EXAMPLE)
