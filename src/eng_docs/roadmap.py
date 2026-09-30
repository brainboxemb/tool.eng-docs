"""Generic RoadmapView validation and SVG/PDF rendering."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import html, json, math, textwrap

import yaml
from jsonschema import Draft202012Validator
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas

PW, PH = landscape(A4)
MARGIN, FOOTER, GAP, ROW_GAP, PAD = 18.0, 22.0, 10.0, 12.0, 9.0
TITLE, BODY, SMALL, HEADING, LINE = 11.5, 8.5, 7.5, 8.0, 1.25
MARKER_H, CHIP_H = 24.0, 16.0
CARD_STROKE, RULE = "#b8c0c8", "#d9dde1"
PALETTES = {
    "neutral": ("#f6f7f8", "#697077", "#2f3337"),
    "active": ("#e8f1fb", "#4b78a8", "#244b73"),
    "success": ("#eaf5e7", "#5a8750", "#31582b"),
    "warning": ("#fff4d6", "#a77a19", "#6a4b00"),
    "danger": ("#fdeaea", "#b14c4c", "#7a2929"),
    "muted": ("#f1f1f1", "#888888", "#555555"),
    "mature": ("#eaf5e7", "#5a8750", "#31582b"),
    "draft": ("#fff4d6", "#a77a19", "#6a4b00"),
}

@dataclass(frozen=True)
class Card:
    item: dict; x: float; y: float; width: float; height: float
    title_lines: tuple[str, ...]; primary_meta_lines: tuple[str, ...]
    secondary_meta_lines: tuple[str, ...]; sections: tuple
    badge_heading: str | None; badge_rows: tuple

@dataclass(frozen=True)
class Page:
    number: int; cards: tuple[Card, ...]

@dataclass(frozen=True)
class Layout:
    title: str; subtitle: str | None; title_lines: tuple[str, ...]
    subtitle_lines: tuple[str, ...]; header_height: float
    page_width: float; page_height: float; columns: int; pages: tuple[Page, ...]


def load_schema(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validate_source(data, schema, path: Path):
    errors = sorted(Draft202012Validator(schema).iter_errors(data), key=lambda e: list(e.path))
    if errors:
        lines = [f"{path}: invalid roadmap source"]
        for err in errors:
            loc = ".".join(str(x) for x in err.path) or "<root>"
            lines.append(f"  {loc}: {err.message}")
        raise ValueError("\n".join(lines))
    ids = [item["id"] for item in data["roadmap"]["items"]]
    dup = sorted(i for i in set(ids) if ids.count(i) > 1)
    if dup:
        raise ValueError(f"{path}: duplicate roadmap item id: {dup}")


def _lh(size): return size * LINE

def _wrap(text, width, size, bold=False):
    chars = max(8, int(width / (size * (0.60 if bold else 0.54))))
    return tuple(textwrap.wrap(str(text), width=chars, break_long_words=True,
                               break_on_hyphens=False, replace_whitespace=True) or [""])

def _chip_width(label): return 12.0 + len(label) * SMALL * 0.55

def _marker_width(label): return max(MARKER_H, 10.0 + len(label) * 7.0)

def _palette(tone): return PALETTES.get(tone or "neutral", PALETTES["neutral"])

def _hex(value):
    value = value.lstrip("#")
    return tuple(int(value[i:i+2], 16) / 255.0 for i in (0, 2, 4))


def _badge_rows(badges, width):
    usable, rows, row, used = width - 2 * PAD, [], [], 0.0
    for badge in badges:
        bw = _chip_width(badge["label"]); needed = bw if not row else bw + 6.0
        if row and used + needed > usable:
            rows.append(tuple(row)); row, used, needed = [], 0.0, bw
        row.append(badge); used += needed
    if row: rows.append(tuple(row))
    return tuple(rows)


def _measure(item, width):
    inner = width - 2 * PAD
    state, marker = item.get("state"), item.get("marker")
    badges, badge_heading = item.get("badges", []), item.get("badge_heading")

    state_w = max(38.0, _chip_width(state["label"])) if state else 0.0
    marker_w = _marker_width(marker) if marker else 0.0
    if state_w > inner or marker_w > inner:
        return (math.inf, (), (), (), (), (), None)
    if marker and state and marker_w + state_w + 10.0 > inner:
        return (math.inf, (), (), (), (), (), None)
    if any(_chip_width(b["label"]) > inner for b in badges):
        return (math.inf, (), (), (), (), (), None)

    meta = item.get("meta", [])
    primary = _wrap(meta[0], max(72.0, inner * 0.48), SMALL, True) if meta else ()
    secondary = tuple(
        line for value in meta[1:] for line in _wrap(value, inner, SMALL)
    )

    header_present = bool(marker or state or primary)
    h = 2 * PAD
    if header_present:
        header_h = MARKER_H
        if state:
            header_h = max(header_h, CHIP_H)
        if primary:
            header_h = max(header_h, CHIP_H + 3.0 + len(primary) * _lh(SMALL))
        h += header_h + 7.0

    titles = _wrap(item["title"], inner, TITLE, True)
    h += len(titles) * _lh(TITLE)
    if secondary:
        h += 5.0 + len(secondary) * _lh(SMALL)

    sections = []
    for section in item.get("sections", []):
        bullets = tuple(_wrap(b, inner - 12.0, BODY) for b in section["bullets"])
        sections.append((section["heading"], bullets))
        h += 11.0 + _lh(HEADING) + 4.0
        h += sum(len(lines) * _lh(BODY) + 3.0 for lines in bullets)

    rows = _badge_rows(badges, width)
    if rows:
        h += 11.0
        if badge_heading:
            h += _lh(HEADING) + 4.0
        h += len(rows) * 20.0

    return h, titles, primary, secondary, tuple(sections), rows, badge_heading


def _header(roadmap):
    usable = PW - 2 * MARGIN
    titles = _wrap(roadmap["title"], usable, 17.0, True)
    subs = _wrap(roadmap["subtitle"], usable, 9.0) if roadmap.get("subtitle") else ()
    h = 20.0 + len(titles) * _lh(17.0) + (5.0 + len(subs) * _lh(9.0) if subs else 0.0)
    return titles, subs, h


def _width(cols): return (PW - 2 * MARGIN - (cols - 1) * GAP) / cols


def choose_columns(items, header_height=58.0):
    available = PH - 2 * MARGIN - header_height - FOOTER
    for cols in (3, 2, 1):
        if all(_measure(i, _width(cols))[0] <= available for i in items): return cols
    tallest = max((_measure(i, _width(1))[0], i["id"]) for i in items)
    raise ValueError("roadmap item cannot fit on one landscape A4 page even at full card width: "
                     f"{tallest[1]!r} requires {tallest[0]:.1f}pt, available {available:.1f}pt")


def layout_roadmap(data):
    road, items = data["roadmap"], data["roadmap"]["items"]
    title_lines, subtitle_lines, header = _header(road)
    cols = choose_columns(items, header)
    width = _width(cols)
    first_y, bottom = MARGIN + header, PH - MARGIN - FOOTER
    pages, cards, y, number = [], [], first_y, 1
    for start in range(0, len(items), cols):
        row_items = items[start:start+cols]
        measured = [_measure(i, width) for i in row_items]
        row_h = max(m[0] for m in measured)
        if cards and y + row_h > bottom:
            pages.append(Page(number, tuple(cards)))
            number += 1
            cards, y = [], first_y
        for col, (item, m) in enumerate(zip(row_items, measured)):
            h, titles, primary, secondary, sections, rows, badge_heading = m
            cards.append(Card(
                item, MARGIN + col * (width + GAP), y, width, h,
                titles, primary, secondary, sections, badge_heading, rows
            ))
        y += row_h + ROW_GAP
    if cards:
        pages.append(Page(number, tuple(cards)))
    return Layout(
        road["title"], road.get("subtitle"), title_lines, subtitle_lines,
        header, PW, PH, cols, tuple(pages)
    )


def _svg_text(parts, x, y, lines, size, weight="normal",
              fill="#2f3337", anchor="start"):
    for n, line in enumerate(lines):
        parts.append(
            f'<text x="{x:.2f}" y="{y+n*_lh(size):.2f}" '
            f'text-anchor="{anchor}" '
            f'font-family="Arial,Helvetica,sans-serif" font-size="{size:.2f}" '
            f'font-weight="{weight}" fill="{fill}">{html.escape(str(line))}</text>'
        )


def _svg_section_heading(parts, x, y, width, heading):
    _svg_text(parts, x, y + HEADING, [heading], HEADING, "bold", "#4b5b6b")
    rule_x = x + min(width * 0.45, 92.0)
    parts.append(
        f'<line x1="{rule_x:.2f}" y1="{y+5.0:.2f}" '
        f'x2="{x+width:.2f}" y2="{y+5.0:.2f}" '
        f'stroke="{RULE}" stroke-width="1"/>'
    )


def _svg_page(layout, page):
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="297mm" height="210mm" '
        f'viewBox="0 0 {PW:.2f} {PH:.2f}">',
        '<rect width="100%" height="100%" fill="white"/>'
    ]
    title_y = MARGIN + 17.0
    _svg_text(parts, MARGIN, title_y, layout.title_lines, 17.0, "bold")
    if layout.subtitle_lines:
        _svg_text(
            parts, MARGIN,
            title_y + len(layout.title_lines) * _lh(17.0) + 5.0,
            layout.subtitle_lines, 9.0, fill="#666666"
        )

    for card in page.cards:
        item = card.item
        state, marker = item.get("state"), item.get("marker")
        parts.append(
            f'<rect x="{card.x:.2f}" y="{card.y:.2f}" width="{card.width:.2f}" '
            f'height="{card.height:.2f}" rx="6" fill="#fff" '
            f'stroke="{CARD_STROKE}" stroke-width="1"/>'
        )
        cursor = card.y + PAD
        header_bottom = cursor

        if marker:
            mw = _marker_width(marker)
            parts.append(
                f'<rect x="{card.x+PAD:.2f}" y="{cursor:.2f}" width="{mw:.2f}" '
                f'height="{MARKER_H:.2f}" rx="5" fill="#f3f5f7" stroke="#8b96a1"/>'
            )
            _svg_text(
                parts, card.x + PAD + mw / 2, cursor + 16.2, [marker],
                10.5, "bold", "#2f3337", "middle"
            )
            header_bottom = max(header_bottom, cursor + MARKER_H)

        right = card.x + card.width - PAD
        if state:
            fill, stroke, text_fill = _palette(state.get("tone"))
            bw = max(38.0, _chip_width(state["label"]))
            parts.append(
                f'<rect x="{right-bw:.2f}" y="{cursor:.2f}" width="{bw:.2f}" '
                f'height="{CHIP_H:.2f}" rx="8" fill="{fill}" stroke="{stroke}"/>'
            )
            _svg_text(
                parts, right - bw / 2, cursor + 11.4, [state["label"]],
                SMALL, "bold", text_fill, "middle"
            )
            header_bottom = max(header_bottom, cursor + CHIP_H)

        if card.primary_meta_lines:
            primary_y = cursor + (CHIP_H + 3.0 if state else 0.0) + SMALL
            _svg_text(
                parts, right, primary_y, card.primary_meta_lines,
                SMALL, "bold", "#555f68", "end"
            )
            header_bottom = max(
                header_bottom,
                primary_y + (len(card.primary_meta_lines) - 1) * _lh(SMALL)
            )

        if marker or state or card.primary_meta_lines:
            cursor = header_bottom + 7.0

        _svg_text(
            parts, card.x + PAD, cursor + TITLE,
            card.title_lines, TITLE, "bold"
        )
        cursor += len(card.title_lines) * _lh(TITLE)

        if card.secondary_meta_lines:
            cursor += 5.0
            _svg_text(
                parts, card.x + PAD, cursor + SMALL,
                card.secondary_meta_lines, SMALL, fill="#6a7279"
            )
            cursor += len(card.secondary_meta_lines) * _lh(SMALL)

        inner = card.width - 2 * PAD
        for heading, bullets in card.sections:
            cursor += 11.0
            _svg_section_heading(parts, card.x + PAD, cursor, inner, heading)
            cursor += _lh(HEADING) + 4.0
            for lines in bullets:
                parts.append(
                    f'<circle cx="{card.x+PAD+3:.2f}" cy="{cursor+4.1:.2f}" '
                    f'r="1.55" fill="#6a8bb0"/>'
                )
                _svg_text(parts, card.x + PAD + 10, cursor + BODY, lines, BODY)
                cursor += len(lines) * _lh(BODY) + 3.0

        if card.badge_rows:
            cursor += 11.0
            if card.badge_heading:
                _svg_section_heading(
                    parts, card.x + PAD, cursor, inner, card.badge_heading
                )
                cursor += _lh(HEADING) + 4.0
            for row in card.badge_rows:
                bx = card.x + PAD
                for badge in row:
                    bf, bs, bt = _palette(badge.get("tone"))
                    bw = _chip_width(badge["label"])
                    parts.append(
                        f'<rect x="{bx:.2f}" y="{cursor:.2f}" width="{bw:.2f}" '
                        f'height="{CHIP_H:.2f}" rx="5" fill="{bf}" stroke="{bs}"/>'
                    )
                    _svg_text(
                        parts, bx + bw / 2, cursor + 11.4, [badge["label"]],
                        SMALL, "bold", bt, "middle"
                    )
                    bx += bw + 6
                cursor += 20.0

    _svg_text(
        parts, PW-MARGIN-48, PH-14,
        [f"Page {page.number}/{len(layout.pages)}"], SMALL, fill="#777"
    )
    return "\n".join(parts + ["</svg>"]) + "\n"



def render_svg(layout, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True); page_dir = out_dir/"roadmap"; page_dir.mkdir(exist_ok=True)
    svgs = []
    for page in layout.pages:
        svg = _svg_page(layout, page); (page_dir/f"roadmap-page-{page.number:02d}.svg").write_text(svg, encoding="utf-8"); svgs.append(svg)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{297*len(svgs)}mm" height="210mm" '
             f'viewBox="0 0 {PW*len(svgs):.2f} {PH:.2f}">', '<rect width="100%" height="100%" fill="#eee"/>']
    for n, svg in enumerate(svgs):
        inner = "\n".join(svg.splitlines()[1:-1])
        parts.append(f'<g transform="translate({n*PW:.2f},0)">{inner}</g>')
    (out_dir/"roadmap.svg").write_text("\n".join(parts+["</svg>"])+"\n", encoding="utf-8")


def _pdf_text(c, x, top, lines, size, bold=False,
              fill=(.18,.20,.22), align="left"):
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


def _pdf_section_heading(c, x, top, width, heading):
    _pdf_text(c, x, top + HEADING, [heading], HEADING, True, (.29,.36,.42))
    rule_x = x + min(width * 0.45, 92.0)
    c.setStrokeColorRGB(*_hex(RULE))
    c.setLineWidth(1.0)
    c.line(rule_x, PH - (top + 5.0), x + width, PH - (top + 5.0))


def render_pdf(layout, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(path), pagesize=(PW,PH))
    for page in layout.pages:
        title_y = MARGIN + 17
        _pdf_text(c, MARGIN, title_y, layout.title_lines, 17, True)
        if layout.subtitle_lines:
            _pdf_text(
                c, MARGIN,
                title_y + len(layout.title_lines) * _lh(17) + 5,
                layout.subtitle_lines, 9, fill=(.4,.4,.4)
            )

        for card in page.cards:
            item = card.item
            state, marker = item.get("state"), item.get("marker")
            c.setStrokeColorRGB(*_hex(CARD_STROKE))
            c.setFillColorRGB(1,1,1)
            c.roundRect(
                card.x, PH-card.y-card.height, card.width, card.height,
                6, stroke=1, fill=1
            )

            cursor = card.y + PAD
            header_bottom = cursor
            if marker:
                mw = _marker_width(marker)
                c.setFillColorRGB(*_hex("#f3f5f7"))
                c.setStrokeColorRGB(*_hex("#8b96a1"))
                c.roundRect(
                    card.x + PAD, PH-cursor-MARKER_H, mw, MARKER_H,
                    5, stroke=1, fill=1
                )
                _pdf_text(
                    c, card.x + PAD + mw / 2, cursor + 16.2, [marker],
                    10.5, True, align="center"
                )
                header_bottom = max(header_bottom, cursor + MARKER_H)

            right = card.x + card.width - PAD
            if state:
                fill, stroke, text_fill = _palette(state.get("tone"))
                bw = max(38.0, _chip_width(state["label"]))
                c.setFillColorRGB(*_hex(fill))
                c.setStrokeColorRGB(*_hex(stroke))
                c.roundRect(
                    right-bw, PH-cursor-CHIP_H, bw, CHIP_H,
                    8, stroke=1, fill=1
                )
                _pdf_text(
                    c, right - bw / 2, cursor + 11.4, [state["label"]],
                    SMALL, True, _hex(text_fill), "center"
                )
                header_bottom = max(header_bottom, cursor + CHIP_H)

            if card.primary_meta_lines:
                primary_y = cursor + (CHIP_H + 3.0 if state else 0.0) + SMALL
                _pdf_text(
                    c, right, primary_y, card.primary_meta_lines,
                    SMALL, True, (.33,.37,.41), "right"
                )
                header_bottom = max(
                    header_bottom,
                    primary_y + (len(card.primary_meta_lines) - 1) * _lh(SMALL)
                )

            if marker or state or card.primary_meta_lines:
                cursor = header_bottom + 7.0

            _pdf_text(
                c, card.x + PAD, cursor + TITLE,
                card.title_lines, TITLE, True
            )
            cursor += len(card.title_lines) * _lh(TITLE)

            if card.secondary_meta_lines:
                cursor += 5.0
                _pdf_text(
                    c, card.x + PAD, cursor + SMALL,
                    card.secondary_meta_lines, SMALL, fill=(.42,.45,.48)
                )
                cursor += len(card.secondary_meta_lines) * _lh(SMALL)

            inner = card.width - 2 * PAD
            for heading, bullets in card.sections:
                cursor += 11.0
                _pdf_section_heading(c, card.x + PAD, cursor, inner, heading)
                cursor += _lh(HEADING) + 4.0
                for lines in bullets:
                    c.setFillColorRGB(*_hex("#6a8bb0"))
                    c.circle(
                        card.x + PAD + 3, PH-(cursor+4.1),
                        1.55, stroke=0, fill=1
                    )
                    _pdf_text(
                        c, card.x + PAD + 10,
                        cursor + BODY, lines, BODY
                    )
                    cursor += len(lines) * _lh(BODY) + 3.0

            if card.badge_rows:
                cursor += 11.0
                if card.badge_heading:
                    _pdf_section_heading(
                        c, card.x + PAD, cursor, inner, card.badge_heading
                    )
                    cursor += _lh(HEADING) + 4.0
                for row in card.badge_rows:
                    bx = card.x + PAD
                    for badge in row:
                        bf, bs, bt = _palette(badge.get("tone"))
                        bw = _chip_width(badge["label"])
                        c.setFillColorRGB(*_hex(bf))
                        c.setStrokeColorRGB(*_hex(bs))
                        c.roundRect(
                            bx, PH-cursor-CHIP_H, bw, CHIP_H,
                            5, stroke=1, fill=1
                        )
                        _pdf_text(
                            c, bx + bw / 2, cursor + 11.4,
                            [badge["label"]], SMALL, True,
                            _hex(bt), "center"
                        )
                        bx += bw + 6
                    cursor += 20

        _pdf_text(
            c, PW-MARGIN-48, PH-14,
            [f"Page {page.number}/{len(layout.pages)}"],
            SMALL, fill=(.47,.47,.47)
        )
        c.showPage()
    c.save()



def generate(source: Path, schema_path: Path, out_dir: Path):
    if not source.is_file(): raise ValueError(f"roadmap source file does not exist: {source}")
    data=yaml.safe_load(source.read_text(encoding="utf-8")); validate_source(data, load_schema(schema_path), source)
    layout=layout_roadmap(data); render_svg(layout,out_dir); render_pdf(layout,out_dir/"roadmap.pdf"); return layout
