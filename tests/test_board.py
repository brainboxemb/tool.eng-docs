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
    assert "RESULT" in svg
    assert "END DEMO" in svg
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
    data = source()
    data["board"]["sections"][0]["heading"] = "A deliberately longer section heading"
    path = tmp_path / "heading.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    generate(path, SCHEMA, tmp_path / "heading-out")
    svg = (tmp_path / "heading-out/board.svg").read_text(encoding="utf-8")
    heading_index = svg.index("A DELIBERATELY LONGER SECTION HEADING")
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

def test_two_column_sections_share_row_and_save_vertical_space():
    data = source()
    two_col = layout_board(data)
    assert two_col["section_columns"] == 2
    assert len(two_col["section_rows"]) == 1
    assert len(two_col["section_rows"][0][0]) == 2

    one_col_source = copy.deepcopy(data)
    one_col_source["board"]["section_columns"] = 1
    one_col = layout_board(one_col_source)
    assert len(one_col["section_rows"]) == 2
    assert two_col["required_height"] < one_col["required_height"]


def test_section_columns_default_to_one():
    data = source()
    data["board"].pop("section_columns", None)
    layout = layout_board(data)
    assert layout["section_columns"] == 1

def test_board_uses_compact_outer_margin():
    layout = layout_board(source())
    assert layout["required_height"] < 700

def test_header_meta_shares_card_header_without_making_id_non_bold(tmp_path):
    data = source()
    card = data["board"]["groups"][0]["cards"][1]
    assert card["header_meta"] == ["~1d · after D01"]
    layout = layout_board(data)
    rendered = layout["groups"][0]["rows"][0][0][1]
    assert rendered["header_meta"] == ("~1d · after D01",)

    path = tmp_path / "header.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    generate(path, SCHEMA, tmp_path / "header-out")
    svg = (tmp_path / "header-out/board.svg").read_text(encoding="utf-8")
    id_pos = svg.index(">D02</text>")
    header_pos = svg.index(">~1d · after D01</text>")
    assert 'font-weight="bold"' in svg[svg.rfind("<text", 0, id_pos):id_pos]
    assert 'font-weight="normal"' in svg[svg.rfind("<text", 0, header_pos):header_pos]


def test_single_line_header_meta_is_more_compact_than_bottom_meta():
    data = source()
    card = data["board"]["groups"][1]["cards"][0]
    compact = layout_board(data)["groups"][1]["rows"][0][0][0]["height"]

    bottom_source = copy.deepcopy(data)
    bottom_card = bottom_source["board"]["groups"][1]["cards"][0]
    bottom_card["meta"] = list(bottom_card.pop("header_meta"))
    bottom = layout_board(bottom_source)["groups"][1]["rows"][0][0][0]["height"]
    assert compact < bottom

def test_group_heading_tone_does_not_change_heading_color(tmp_path):
    data = source()
    data["board"]["groups"][0]["tone"] = "danger"
    path = tmp_path / "neutral-group-heading.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    generate(path, SCHEMA, tmp_path / "neutral-group-heading-out")
    svg = (tmp_path / "neutral-group-heading-out/board.svg").read_text(encoding="utf-8")
    heading = "DOCUMENTATION / DECISIONS"
    pos = svg.index(heading)
    text_start = svg.rfind("<text", 0, pos)
    tag = svg[text_start:pos]
    assert 'fill="#626a72"' in tag

def test_all_board_headings_render_uppercase_with_shared_heading_size(tmp_path):
    data = source()
    path = tmp_path / "uppercase-headings.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    generate(path, SCHEMA, tmp_path / "uppercase-headings-out")
    svg = (tmp_path / "uppercase-headings-out/board.svg").read_text(encoding="utf-8")

    for heading in (
        "PURPOSE",
        "RESULT",
        "END DEMO",
        "DOCUMENTATION",
        "DOCUMENTATION / DECISIONS",
        "APPLICATION / PRODUCT",
        "VERIFICATION / TEST",
        "PLANNING CHANGES",
    ):
        pos = svg.index(f">{heading}</text>")
        text_start = svg.rfind("<text", 0, pos)
        tag = svg[text_start:pos]
        assert 'font-size="8.00"' in tag
        assert 'font-weight="bold"' in tag

def test_board_marker_leads_title_and_meta_values_form_one_status_line(tmp_path):
    data = source()
    layout = layout_board(data)
    assert layout["title_x_offset"] > 0
    assert layout["meta_lines"][0] == (
        "ACTIVE | orig ~3d · rem ~2d | forecast end 18 Oct"
    )

    path = tmp_path / "leading-marker.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    generate(path, SCHEMA, tmp_path / "leading-marker-out")
    svg = (tmp_path / "leading-marker-out/board.svg").read_text(encoding="utf-8")

    marker_pos = svg.index(">4</text>")
    title_pos = svg.index(">Engineering detail board</text>")
    assert marker_pos < title_pos

    marker_text_start = svg.rfind("<text", 0, marker_pos)
    marker_tag = svg[marker_text_start:marker_pos]
    assert 'font-size="14.00"' in marker_tag
    assert 'font-weight="bold"' in marker_tag

    assert "ACTIVE | orig ~3d · rem ~2d | forecast end 18 Oct" in svg

