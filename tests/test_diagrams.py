from importlib.resources import files
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from eng_docs.diagrams import generate, load_yaml, validate_refs


FIXTURES = Path(__file__).parent / "fixtures"
PACKAGE = files("eng_docs")
SCHEMA = Path(str(PACKAGE.joinpath("schemas/diagram.schema.json")))
THEME = Path(str(PACKAGE.joinpath("themes/default.yaml")))


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


def test_missing_edge_reference_is_rejected():
    data = load_yaml(FIXTURES / "simple-flow.yaml")
    data["edges"][0]["to"] = "missing"
    with pytest.raises(ValueError, match="edge references missing node"):
        validate_refs(data, load_yaml(THEME), FIXTURES / "simple-flow.yaml")


def test_unknown_kind_is_rejected():
    data = load_yaml(FIXTURES / "simple-flow.yaml")
    data["nodes"][0]["kind"] = "unknown-kind"
    with pytest.raises(ValueError, match="unknown kind"):
        validate_refs(data, load_yaml(THEME), FIXTURES / "simple-flow.yaml")
