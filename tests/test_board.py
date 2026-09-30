from pathlib import Path
import copy
import xml.etree.ElementTree as ET

import pytest
import yaml

from eng_docs.board import generate, layout_board, load_schema, validate_source

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/board/board.yaml"
SCHEMA = ROOT / "src/eng_docs/schemas/board.schema.json"


def source():
    return yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))


def test_example_generates_print_friendly_svg_and_pdf(tmp_path):
    layout = generate(EXAMPLE, SCHEMA, tmp_path)
    assert layout["card_width"] > 160
    ET.parse(tmp_path / "board.svg")
    svg = (tmp_path / "board.svg").read_text(encoding="utf-8")
    assert "Engineering detail board" in svg
    assert ">4</text>" in svg
    assert "PURPOSE" in svg
    assert "readable descriptive summary" in svg
    assert "A deliberately longer section heading" in svg
    assert "PLANNING CHANGES" in svg
    assert 'fill="#ffffff"' in svg
    assert (tmp_path / "board.pdf").read_bytes().startswith(b"%PDF")


def test_duplicate_card_ids_rejected(tmp_path):
    data = source()
    duplicate = copy.deepcopy(data["board"]["groups"][0]["cards"][0])
    data["board"]["groups"][1]["cards"].append(duplicate)
    path = tmp_path / "duplicate.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate board card id"):
        validate_source(data, load_schema(SCHEMA), path)


def test_cards_grow_with_wrapped_meta():
    data = source()
    first = layout_board(data)
    base = first["groups"][0]["rows"][0][0][0]["height"]
    data["board"]["groups"][0]["cards"][0]["meta"] = [
        " ".join(["Longer board metadata should wrap without clipping."] * 8)
    ]
    grown = layout_board(data)
    assert grown["groups"][0]["rows"][0][0][0]["height"] > base


def test_unrepresentable_board_fails_at_page_boundary():
    data = source()
    data["board"]["groups"][0]["cards"][0]["meta"] = [
        " ".join(["content"] * 2500)
    ]
    with pytest.raises(ValueError, match="cannot fit on one A4 portrait page"):
        layout_board(data)


def test_unknown_tones_use_neutral_fallback(tmp_path):
    data = source()
    data["board"]["groups"][0]["tone"] = "consumer-tone"
    data["board"]["groups"][0]["cards"][0]["state"]["tone"] = "consumer-tone"
    path = tmp_path / "tone.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    assert generate(path, SCHEMA, tmp_path / "out")["groups"]


def test_output_is_deterministic(tmp_path):
    first = tmp_path / "first"
    second = tmp_path / "second"
    generate(EXAMPLE, SCHEMA, first)
    generate(EXAMPLE, SCHEMA, second)
    assert (first / "board.svg").read_bytes() == (second / "board.svg").read_bytes()

def test_heading_rule_starts_after_heading_text(tmp_path):
    generate(EXAMPLE, SCHEMA, tmp_path)
    svg = (tmp_path / "board.svg").read_text(encoding="utf-8")
    heading_index = svg.index("A deliberately longer section heading")
    line_index = svg.index("<line", heading_index)
    line = svg[line_index:svg.index("/>", line_index)]
    x1 = float(line.split('x1="')[1].split('"')[0])
    assert x1 > 150.0


def test_marker_and_summary_are_optional(tmp_path):
    data = source()
    data["board"].pop("marker", None)
    data["board"].pop("summary", None)
    path = tmp_path / "compat.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    assert generate(path, SCHEMA, tmp_path / "compat-out")["groups"]
