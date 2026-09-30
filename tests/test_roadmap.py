from pathlib import Path
import copy
import xml.etree.ElementTree as ET

import pytest
import yaml

from eng_docs.roadmap import generate, layout_roadmap, load_schema, validate_source

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples/roadmap/roadmap.yaml"
SCHEMA_PATH = ROOT / "src/eng_docs/schemas/roadmap.schema.json"

def source():
    return yaml.safe_load(EXAMPLE.read_text(encoding="utf-8"))

def test_example_generates_svg_pdf_and_pages(tmp_path):
    layout = generate(EXAMPLE, SCHEMA_PATH, tmp_path)
    assert layout.columns == 3
    assert len(layout.pages) == 1
    ET.parse(tmp_path / "roadmap.svg")
    ET.parse(tmp_path / "roadmap/roadmap-page-01.svg")
    svg = (tmp_path / "roadmap/roadmap-page-01.svg").read_text(encoding="utf-8")
    assert ">1</text>" in svg
    assert "DOCUMENT STATUS" in svg
    assert svg.index("completed") < svg.index("~2d")
    assert (tmp_path / "roadmap.pdf").read_bytes().startswith(b"%PDF")

def test_duplicate_ids_rejected(tmp_path):
    data = source()
    data["roadmap"]["items"].append(copy.deepcopy(data["roadmap"]["items"][0]))
    path = tmp_path / "duplicate.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate roadmap item id"):
        validate_source(data, load_schema(SCHEMA_PATH), path)

def test_longer_compact_text_reduces_columns_instead_of_rejecting():
    data = source()
    text = " ".join(["Compact roadmap text may wrap without changing authoritative planning."] * 20)
    data["roadmap"]["items"][0]["sections"][0]["bullets"] = [text]
    assert layout_roadmap(data).columns in (1, 2)

def test_many_items_paginate():
    data = source(); base = data["roadmap"]["items"][0]; data["roadmap"]["items"] = []
    for index in range(12):
        item = copy.deepcopy(base); item["id"] = f"item-{index}"; item["title"] = f"Roadmap item {index}"
        data["roadmap"]["items"].append(item)
    layout = layout_roadmap(data)
    assert len(layout.pages) > 1
    assert sum(len(page.cards) for page in layout.pages) == 12

def test_unrepresentable_presentation_fails_only_at_full_width():
    data = source()
    data["roadmap"]["items"][0]["sections"][0]["bullets"] = [" ".join(["content"] * 2500)]
    with pytest.raises(ValueError, match="full card width"):
        layout_roadmap(data)

def test_unknown_tone_is_allowed_and_uses_fallback(tmp_path):
    data = source(); data["roadmap"]["items"][0]["state"]["tone"] = "consumer-defined-tone"
    path = tmp_path / "custom-tone.yaml"; path.write_text(yaml.safe_dump(data), encoding="utf-8")
    assert generate(path, SCHEMA_PATH, tmp_path / "out").pages

def test_output_is_deterministic(tmp_path):
    first, second = tmp_path / "first", tmp_path / "second"
    generate(EXAMPLE, SCHEMA_PATH, first); generate(EXAMPLE, SCHEMA_PATH, second)
    assert (first / "roadmap.svg").read_bytes() == (second / "roadmap.svg").read_bytes()

def test_long_title_wraps_and_increases_header_without_clipping():
    data = source(); data["roadmap"]["title"] = " ".join(["A deliberately longer roadmap title"] * 12)
    layout = layout_roadmap(data)
    assert len(layout.title_lines) > 1
    assert layout.header_height > 58
    assert min(card.y for card in layout.pages[0].cards) >= 30 + layout.header_height

def test_long_state_label_can_force_wider_cards():
    data = source()
    data["roadmap"]["items"][0]["state"]["label"] = "A VERY LONG PRESENTATION STATE LABEL THAT NEEDS MORE CARD WIDTH"
    assert layout_roadmap(data).columns in (1, 2)

def test_marker_and_badge_heading_are_optional_for_compatibility(tmp_path):
    data = source()
    item = data["roadmap"]["items"][0]
    item.pop("marker", None)
    item.pop("badge_heading", None)
    path = tmp_path / "compat.yaml"
    path.write_text(yaml.safe_dump(data), encoding="utf-8")
    assert generate(path, SCHEMA_PATH, tmp_path / "compat-out").pages
