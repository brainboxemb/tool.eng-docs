"""Generic print-friendly BoardView validation and SVG/PDF rendering."""
from __future__ import annotations

from pathlib import Path
import html
import json
import math
import textwrap

import yaml
from jsonschema import Draft202012Validator
from reportlab.lib.pagesizes import A4, portrait
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from .presentation_style import (
    CARD_BACKGROUND,
    CARD_STROKE,
    PAGE_BACKGROUND,
    RULE,
    TEXT,
    TEXT_MUTED,
    hex_rgb,
    palette,
)

PW, PH = portrait(A4)
MARGIN, FOOTER, GAP, PAD = 16.0, 18.0, 8.0, 8.0
BLOCK_GAP, GROUP_GAP = 7.0, 9.0
COLS = 3
TITLE, BODY, SMALL, HEADING, CARD_TITLE, LINE = 16.0, 8.0, 7.0, 8.0, 9.5, 1.25
CHIP_H = 15.0
MARKER_H = 24.0


def load_schema(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate_source(data, schema, path: Path):
    errors = sorted(
        Draft202012Validator(schema).iter_errors(data),
        key=lambda e: list(e.path),
    )
    if errors:
        lines = [f"{path}: invalid board source"]
        for err in errors:
            loc = ".".join(str(x) for x in err.path) or "<root>"
            lines.append(f"  {loc}: {err.message}")
        raise ValueError("\n".join(lines))

    ids = [
        card["id"]
        for group in data["board"].get("groups", [])
        for card in group.get("cards", [])
    ]
    dup = sorted(i for i in set(ids) if ids.count(i) > 1)
    if dup:
        raise ValueError(f"{path}: duplicate board card id: {dup}")


def _lh(size):
    return size * LINE


def _wrap(value, width, size, bold=False):
    chars = max(8, int(width / (size * (0.60 if bold else 0.54))))
    return tuple(
        textwrap.wrap(
            str(value),
            width=chars,
            break_long_words=True,
            break_on_hyphens=False,
            replace_whitespace=True,
        )
        or [""]
    )


def _chip_width(label):
    return 12.0 + len(label) * SMALL * 0.55


def _marker_width(label):
    return max(MARKER_H, 10.0 + len(label) * 7.0)


def _heading_rule_start(x, width, heading):
    text_width = stringWidth(str(heading), "Helvetica-Bold", HEADING)
    start = x + text_width + 10.0
    return start if start < x + width - 20.0 else None


def _badge_rows(badges, width):
    rows, row, used = [], [], 0.0
    for badge in badges:
        bw = _chip_width(badge["label"])
        needed = bw if not row else bw + 6.0
        if row and used + needed > width:
            rows.append(tuple(row))
            row, used, needed = [], 0.0, bw
        if bw > width:
            raise ValueError(
                f"board badge cannot fit available width: {badge['label']!r}"
            )
        row.append(badge)
        used += needed
    if row:
        rows.append(tuple(row))
    return tuple(rows)


def _section_layout(section, width):
    bullets = tuple(_wrap(value, width - 10.0, BODY) for value in section["bullets"])
    height = _lh(HEADING) + 7.0
    height += sum(len(lines) * _lh(BODY) + 3.0 for lines in bullets)
    return {
        "heading": section["heading"],
        "bullets": bullets,
        "height": height,
    }


def _summary_layout(summary, width):
    lines = _wrap(summary["text"], width, BODY)
    return {
        "heading": summary["heading"],
        "lines": lines,
        "height": _lh(HEADING) + 7.0 + len(lines) * _lh(BODY),
    }


def _card_layout(card, width):
    inner = width - 2 * PAD
    state = card.get("state")
    state_width = _chip_width(state["label"]) if state else 0.0
    if state and state_width > inner * 0.55:
        raise ValueError(
            f"board card state label too wide for card {card['id']!r}: "
            f"{state['label']!r}"
        )

    id_width = stringWidth(str(card["id"]), "Helvetica-Bold", SMALL)
    header_text = " | ".join(card.get("header_meta", []))
    header_width = inner - id_width - 8.0
    if state:
        header_width -= state_width + 8.0
    if header_text and header_width < 24.0:
        raise ValueError(
            f"board card header metadata has insufficient width for card {card['id']!r}"
        )
    header_meta = _wrap(header_text, header_width, SMALL) if header_text else ()
    header_height = max(CHIP_H, len(header_meta) * _lh(SMALL))

    title = _wrap(card["title"], inner, CARD_TITLE, True)
    meta = tuple(
        line
        for value in card.get("meta", [])
        for line in _wrap(value, inner, SMALL)
    )
    height = 2 * PAD + header_height + 5.0 + len(title) * _lh(CARD_TITLE)
    if meta:
        height += 5.0 + len(meta) * _lh(SMALL)
    return {
        "id": card["id"],
        "id_width": id_width,
        "header_meta": header_meta,
        "header_height": header_height,
        "title": title,
        "state": state,
        "meta": meta,
        "height": max(52.0, height),
    }


def layout_board(data):
    board = data["board"]
    usable = PW - 2 * MARGIN
    marker = board.get("marker")
    marker_w = _marker_width(marker) if marker else 0.0
    title_width = usable - (marker_w + 12.0 if marker else 0.0)
    if title_width < 120.0:
        raise ValueError("board marker leaves insufficient width for title")
    title_lines = _wrap(board["title"], title_width, TITLE, True)
    meta_lines = tuple(
        line for value in board.get("meta", []) for line in _wrap(value, usable, SMALL)
    )

    cursor = MARGIN + max(
        len(title_lines) * _lh(TITLE),
        MARKER_H if marker else 0.0,
    )
    if meta_lines:
        cursor += 5.0 + len(meta_lines) * _lh(SMALL)
    cursor += BLOCK_GAP

    summary = None
    if board.get("summary"):
        summary = _summary_layout(board["summary"], usable)
        cursor += summary["height"] + BLOCK_GAP

    section_columns = int(board.get("section_columns", 1))
    section_width = (usable - (section_columns - 1) * GAP) / section_columns
    section_rows = []
    source_sections = board.get("sections", [])
    for start in range(0, len(source_sections), section_columns):
        row = tuple(
            _section_layout(section, section_width)
            for section in source_sections[start:start + section_columns]
        )
        row_h = max(section["height"] for section in row)
        section_rows.append((row, row_h))
        cursor += row_h + BLOCK_GAP

    badge_section = None
    if board.get("badge_section"):
        src = board["badge_section"]
        rows = _badge_rows(src["badges"], usable)
        badge_section = {
            "heading": src["heading"],
            "rows": rows,
            "height": _lh(HEADING) + 7.0 + len(rows) * 19.0,
        }
        cursor += badge_section["height"] + BLOCK_GAP

    card_width = (usable - (COLS - 1) * GAP) / COLS
    groups = []
    for group in board.get("groups", []):
        cards = [_card_layout(card, card_width) for card in group["cards"]]
        rows = []
        for start in range(0, len(cards), COLS):
            row = cards[start:start + COLS]
            row_h = max(item["height"] for item in row)
            rows.append((tuple(row), row_h))
        height = _lh(HEADING) + 8.0
        height += sum(row_h for _, row_h in rows)
        height += GAP * max(0, len(rows) - 1)
        groups.append({
            "heading": group["heading"],
            "tone": group.get("tone"),
            "rows": tuple(rows),
            "height": height,
        })
        cursor += height + GROUP_GAP

    trailing = []
    for section in board.get("trailing_sections", []):
        layout = _section_layout(section, usable)
        trailing.append(layout)
        cursor += layout["height"] + BLOCK_GAP

    required = cursor + FOOTER
    if required > PH - MARGIN:
        raise ValueError(
            "board view cannot fit on one A4 portrait page: "
            f"requires {required:.1f}pt, available {PH - MARGIN:.1f}pt"
        )

    return {
        "marker": marker,
        "marker_width": marker_w,
        "title_lines": title_lines,
        "meta_lines": meta_lines,
        "summary": summary,
        "section_columns": section_columns,
        "section_width": section_width,
        "section_rows": tuple(section_rows),
        "badge_section": badge_section,
        "groups": tuple(groups),
        "trailing_sections": tuple(trailing),
        "card_width": card_width,
        "required_height": required,
    }


def _svg_text(parts, x, y, lines, size, weight="normal", fill=TEXT, anchor="start"):
    for n, line in enumerate(lines):
        parts.append(
            f'<text x="{x:.2f}" y="{y+n*_lh(size):.2f}" text-anchor="{anchor}" '
            f'font-family="Arial,Helvetica,sans-serif" font-size="{size:.2f}" '
            f'font-weight="{weight}" fill="{fill}">{html.escape(str(line))}</text>'
        )


def _svg_heading(parts, x, y, width, heading, tone=None):
    display_heading = str(heading).upper()
    color = palette(tone)[1] if tone else TEXT_MUTED
    _svg_text(parts, x, y + HEADING, [display_heading], HEADING, "bold", color)
    rule_x = _heading_rule_start(x, width, display_heading)
    if rule_x is not None:
        parts.append(
            f'<line x1="{rule_x:.2f}" y1="{y+5.0:.2f}" '
            f'x2="{x+width:.2f}" y2="{y+5.0:.2f}" '
            f'stroke="{RULE}" stroke-width="1"/>'
        )


def _svg_summary(parts, x, y, width, summary):
    _svg_heading(parts, x, y, width, summary["heading"])
    cursor = y + _lh(HEADING) + 7.0
    _svg_text(parts, x, cursor + BODY, summary["lines"], BODY)
    return y + summary["height"]


def _svg_section(parts, x, y, width, section):
    _svg_heading(parts, x, y, width, section["heading"])
    cursor = y + _lh(HEADING) + 7.0
    for lines in section["bullets"]:
        parts.append(
            f'<circle cx="{x+3:.2f}" cy="{cursor+3.9:.2f}" r="1.45" fill="#6a8bb0"/>'
        )
        _svg_text(parts, x + 10, cursor + BODY, lines, BODY)
        cursor += len(lines) * _lh(BODY) + 3.0
    return y + section["height"]


def _svg_badges(parts, x, y, width, section):
    _svg_heading(parts, x, y, width, section["heading"])
    cursor = y + _lh(HEADING) + 7.0
    for row in section["rows"]:
        bx = x
        for badge in row:
            fill, stroke, text_fill = palette(badge.get("tone"))
            bw = _chip_width(badge["label"])
            parts.append(
                f'<rect x="{bx:.2f}" y="{cursor:.2f}" width="{bw:.2f}" '
                f'height="{CHIP_H:.2f}" rx="5" fill="{fill}" stroke="{stroke}"/>'
            )
            _svg_text(
                parts, bx + bw / 2, cursor + 10.8, [badge["label"]],
                SMALL, "bold", text_fill, "middle",
            )
            bx += bw + 6.0
        cursor += 19.0
    return y + section["height"]


def _svg_card(parts, x, y, width, height, card):
    parts.append(
        f'<rect x="{x:.2f}" y="{y:.2f}" width="{width:.2f}" height="{height:.2f}" '
        f'rx="5" fill="{CARD_BACKGROUND}" stroke="{CARD_STROKE}" stroke-width="1"/>'
    )
    header_y = y + PAD + SMALL
    _svg_text(parts, x + PAD, header_y, [card["id"]], SMALL, "bold", TEXT_MUTED)
    if card["header_meta"]:
        _svg_text(
            parts,
            x + PAD + card["id_width"] + 8.0,
            header_y,
            card["header_meta"],
            SMALL,
            fill=TEXT_MUTED,
        )

    state = card["state"]
    if state:
        fill, stroke, text_fill = palette(state.get("tone"))
        bw = _chip_width(state["label"])
        parts.append(
            f'<rect x="{x+width-PAD-bw:.2f}" y="{y+PAD-3:.2f}" width="{bw:.2f}" '
            f'height="{CHIP_H:.2f}" rx="7" fill="{fill}" stroke="{stroke}"/>'
        )
        _svg_text(
            parts, x + width - PAD - bw / 2, y + PAD + 7.8,
            [state["label"]], SMALL, "bold", text_fill, "middle",
        )

    cursor = y + PAD + card["header_height"] + 5.0
    _svg_text(parts, x + PAD, cursor + CARD_TITLE, card["title"], CARD_TITLE, "bold")
    cursor += len(card["title"]) * _lh(CARD_TITLE)
    if card["meta"]:
        cursor += 5.0
        _svg_text(parts, x + PAD, cursor + SMALL, card["meta"], SMALL, fill=TEXT_MUTED)


def render_svg(layout, path: Path):
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" '
        f'viewBox="0 0 {PW:.2f} {PH:.2f}">',
        f'<rect width="100%" height="100%" fill="{PAGE_BACKGROUND}"/>',
    ]
    usable = PW - 2 * MARGIN
    y = MARGIN
    _svg_text(parts, MARGIN, y + TITLE, layout["title_lines"], TITLE, "bold")
    if layout["marker"]:
        mw = layout["marker_width"]
        mx = PW - MARGIN - mw
        parts.append(
            f'<rect x="{mx:.2f}" y="{y:.2f}" width="{mw:.2f}" '
            f'height="{MARKER_H:.2f}" rx="5" fill="#f3f5f7" stroke="#8b96a1"/>'
        )
        _svg_text(
            parts, mx + mw / 2, y + 16.2, [layout["marker"]],
            10.5, "bold", TEXT, "middle",
        )
    y += max(
        len(layout["title_lines"]) * _lh(TITLE),
        MARKER_H if layout["marker"] else 0.0,
    )
    if layout["meta_lines"]:
        y += 5.0
        _svg_text(parts, MARGIN, y + SMALL, layout["meta_lines"], SMALL, fill=TEXT_MUTED)
        y += len(layout["meta_lines"]) * _lh(SMALL)
    y += BLOCK_GAP

    if layout["summary"]:
        y = _svg_summary(parts, MARGIN, y, usable, layout["summary"]) + BLOCK_GAP

    for row, row_h in layout["section_rows"]:
        for col, section in enumerate(row):
            x = MARGIN + col * (layout["section_width"] + GAP)
            _svg_section(parts, x, y, layout["section_width"], section)
        y += row_h + BLOCK_GAP

    if layout["badge_section"]:
        y = _svg_badges(parts, MARGIN, y, usable, layout["badge_section"]) + BLOCK_GAP

    for group in layout["groups"]:
        _svg_heading(parts, MARGIN, y, usable, group["heading"])
        y += _lh(HEADING) + 8.0
        for row_index, (row, row_h) in enumerate(group["rows"]):
            for col, card in enumerate(row):
                x = MARGIN + col * (layout["card_width"] + GAP)
                _svg_card(parts, x, y, layout["card_width"], row_h, card)
            y += row_h
            if row_index + 1 < len(group["rows"]):
                y += GAP
        y += GROUP_GAP

    for section in layout["trailing_sections"]:
        y = _svg_section(parts, MARGIN, y, usable, section) + BLOCK_GAP

    parts.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def _pdf_text(c, x, top, lines, size, bold=False, fill=None, align="left"):
    fill = fill or hex_rgb(TEXT)
    c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
    c.setFillColorRGB(*fill)
    y = PH - top
    for line in lines:
        if align == "right":
            c.drawRightString(x, y, str(line))
        elif align == "center":
            c.drawCentredString(x, y, str(line))
        else:
            c.drawString(x, y, str(line))
        y -= _lh(size)


def _pdf_heading(c, x, top, width, heading, tone=None):
    display_heading = str(heading).upper()
    color = hex_rgb(palette(tone)[1] if tone else TEXT_MUTED)
    _pdf_text(c, x, top + HEADING, [display_heading], HEADING, True, color)
    rule_x = _heading_rule_start(x, width, display_heading)
    if rule_x is not None:
        c.setStrokeColorRGB(*hex_rgb(RULE))
        c.setLineWidth(1.0)
        c.line(rule_x, PH - (top + 5.0), x + width, PH - (top + 5.0))


def _pdf_summary(c, x, top, width, summary):
    _pdf_heading(c, x, top, width, summary["heading"])
    cursor = top + _lh(HEADING) + 7.0
    _pdf_text(c, x, cursor + BODY, summary["lines"], BODY)
    return top + summary["height"]


def _pdf_section(c, x, top, width, section):
    _pdf_heading(c, x, top, width, section["heading"])
    cursor = top + _lh(HEADING) + 7.0
    for lines in section["bullets"]:
        c.setFillColorRGB(*hex_rgb("#6a8bb0"))
        c.circle(x + 3, PH - (cursor + 3.9), 1.45, stroke=0, fill=1)
        _pdf_text(c, x + 10, cursor + BODY, lines, BODY)
        cursor += len(lines) * _lh(BODY) + 3.0
    return top + section["height"]


def _pdf_badges(c, x, top, width, section):
    _pdf_heading(c, x, top, width, section["heading"])
    cursor = top + _lh(HEADING) + 7.0
    for row in section["rows"]:
        bx = x
        for badge in row:
            fill, stroke, text_fill = palette(badge.get("tone"))
            bw = _chip_width(badge["label"])
            c.setFillColorRGB(*hex_rgb(fill))
            c.setStrokeColorRGB(*hex_rgb(stroke))
            c.roundRect(bx, PH-cursor-CHIP_H, bw, CHIP_H, 5, stroke=1, fill=1)
            _pdf_text(
                c, bx + bw / 2, cursor + 10.8, [badge["label"]],
                SMALL, True, hex_rgb(text_fill), "center",
            )
            bx += bw + 6.0
        cursor += 19.0
    return top + section["height"]


def _pdf_card(c, x, top, width, height, card):
    c.setFillColorRGB(*hex_rgb(CARD_BACKGROUND))
    c.setStrokeColorRGB(*hex_rgb(CARD_STROKE))
    c.roundRect(x, PH-top-height, width, height, 5, stroke=1, fill=1)
    header_top = top + PAD + SMALL
    _pdf_text(c, x + PAD, header_top, [card["id"]], SMALL, True, hex_rgb(TEXT_MUTED))
    if card["header_meta"]:
        _pdf_text(
            c,
            x + PAD + card["id_width"] + 8.0,
            header_top,
            card["header_meta"],
            SMALL,
            fill=hex_rgb(TEXT_MUTED),
        )

    state = card["state"]
    if state:
        fill, stroke, text_fill = palette(state.get("tone"))
        bw = _chip_width(state["label"])
        c.setFillColorRGB(*hex_rgb(fill))
        c.setStrokeColorRGB(*hex_rgb(stroke))
        c.roundRect(
            x + width - PAD - bw, PH - (top + PAD - 3) - CHIP_H,
            bw, CHIP_H, 7, stroke=1, fill=1,
        )
        _pdf_text(
            c, x + width - PAD - bw / 2, top + PAD + 7.8,
            [state["label"]], SMALL, True, hex_rgb(text_fill), "center",
        )

    cursor = top + PAD + card["header_height"] + 5.0
    _pdf_text(c, x + PAD, cursor + CARD_TITLE, card["title"], CARD_TITLE, True)
    cursor += len(card["title"]) * _lh(CARD_TITLE)
    if card["meta"]:
        cursor += 5.0
        _pdf_text(c, x + PAD, cursor + SMALL, card["meta"], SMALL, fill=hex_rgb(TEXT_MUTED))


def render_pdf(layout, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(path), pagesize=(PW, PH))
    usable = PW - 2 * MARGIN
    y = MARGIN
    _pdf_text(c, MARGIN, y + TITLE, layout["title_lines"], TITLE, True)
    if layout["marker"]:
        mw = layout["marker_width"]
        mx = PW - MARGIN - mw
        c.setFillColorRGB(*hex_rgb("#f3f5f7"))
        c.setStrokeColorRGB(*hex_rgb("#8b96a1"))
        c.roundRect(mx, PH-y-MARKER_H, mw, MARKER_H, 5, stroke=1, fill=1)
        _pdf_text(
            c, mx + mw / 2, y + 16.2, [layout["marker"]],
            10.5, True, align="center",
        )
    y += max(
        len(layout["title_lines"]) * _lh(TITLE),
        MARKER_H if layout["marker"] else 0.0,
    )
    if layout["meta_lines"]:
        y += 5.0
        _pdf_text(c, MARGIN, y + SMALL, layout["meta_lines"], SMALL, fill=hex_rgb(TEXT_MUTED))
        y += len(layout["meta_lines"]) * _lh(SMALL)
    y += BLOCK_GAP

    if layout["summary"]:
        y = _pdf_summary(c, MARGIN, y, usable, layout["summary"]) + BLOCK_GAP

    for row, row_h in layout["section_rows"]:
        for col, section in enumerate(row):
            x = MARGIN + col * (layout["section_width"] + GAP)
            _pdf_section(c, x, y, layout["section_width"], section)
        y += row_h + BLOCK_GAP

    if layout["badge_section"]:
        y = _pdf_badges(c, MARGIN, y, usable, layout["badge_section"]) + BLOCK_GAP

    for group in layout["groups"]:
        _pdf_heading(c, MARGIN, y, usable, group["heading"])
        y += _lh(HEADING) + 8.0
        for row_index, (row, row_h) in enumerate(group["rows"]):
            for col, card in enumerate(row):
                x = MARGIN + col * (layout["card_width"] + GAP)
                _pdf_card(c, x, y, layout["card_width"], row_h, card)
            y += row_h
            if row_index + 1 < len(group["rows"]):
                y += GAP
        y += GROUP_GAP

    for section in layout["trailing_sections"]:
        y = _pdf_section(c, MARGIN, y, usable, section) + BLOCK_GAP

    c.showPage()
    c.save()


def generate(source: Path, schema_path: Path, out_dir: Path):
    if not source.is_file():
        raise ValueError(f"board source file does not exist: {source}")
    data = yaml.safe_load(source.read_text(encoding="utf-8"))
    validate_source(data, load_schema(schema_path), source)
    layout = layout_board(data)
    out_dir.mkdir(parents=True, exist_ok=True)
    render_svg(layout, out_dir / "board.svg")
    render_pdf(layout, out_dir / "board.pdf")
    return layout
