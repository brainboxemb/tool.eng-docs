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
MARGIN, FOOTER, GAP, ROW_GAP, PAD = 30.0, 22.0, 14.0, 14.0, 12.0
TITLE, BODY, SMALL, HEADING, LINE = 12.0, 8.5, 7.5, 8.0, 1.25
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
    title_lines: tuple[str, ...]; meta_lines: tuple[str, ...]
    sections: tuple; badge_rows: tuple

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
    inner, state, badges = width - 2 * PAD, item.get("state"), item.get("badges", [])
    if state and _chip_width(state["label"]) > inner: return (math.inf, (), (), (), ())
    if any(_chip_width(b["label"]) > inner for b in badges): return (math.inf, (), (), (), ())
    titles = _wrap(item["title"], inner, TITLE, True)
    h = 2 * PAD + len(titles) * _lh(TITLE) + (23.0 if state else 0.0)
    meta = tuple(line for value in item.get("meta", []) for line in _wrap(value, inner, SMALL))
    if meta: h += 5.0 + len(meta) * _lh(SMALL)
    sections = []
    for section in item.get("sections", []):
        bullets = tuple(_wrap(b, inner - 12.0, BODY) for b in section["bullets"])
        sections.append((section["heading"], bullets)); h += 10.0 + _lh(HEADING)
        h += sum(len(lines) * _lh(BODY) + 3.0 for lines in bullets)
    rows = _badge_rows(badges, width)
    if rows: h += 8.0 + len(rows) * 20.0
    return h, titles, meta, tuple(sections), rows


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
    cols, width = choose_columns(items, header), None
    width = _width(cols); first_y = MARGIN + header; bottom = PH - MARGIN - FOOTER
    pages, cards, y, number = [], [], first_y, 1
    for start in range(0, len(items), cols):
        row_items = items[start:start+cols]; measured = [_measure(i, width) for i in row_items]
        row_h = max(m[0] for m in measured)
        if cards and y + row_h > bottom:
            pages.append(Page(number, tuple(cards))); number += 1; cards, y = [], first_y
        for col, (item, m) in enumerate(zip(row_items, measured)):
            h, titles, meta, sections, rows = m
            cards.append(Card(item, MARGIN + col * (width + GAP), y, width, h,
                              titles, meta, sections, rows))
        y += row_h + ROW_GAP
    if cards: pages.append(Page(number, tuple(cards)))
    return Layout(road["title"], road.get("subtitle"), title_lines, subtitle_lines,
                  header, PW, PH, cols, tuple(pages))


def _svg_text(parts, x, y, lines, size, weight="normal", fill="#2f3337"):
    for n, line in enumerate(lines):
        parts.append(f'<text x="{x:.2f}" y="{y+n*_lh(size):.2f}" '
                     f'font-family="Arial,Helvetica,sans-serif" font-size="{size:.2f}" '
                     f'font-weight="{weight}" fill="{fill}">{html.escape(str(line))}</text>')


def _svg_page(layout, page):
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="297mm" height="210mm" '
             f'viewBox="0 0 {PW:.2f} {PH:.2f}">', '<rect width="100%" height="100%" fill="white"/>']
    title_y = MARGIN + 17.0; _svg_text(parts, MARGIN, title_y, layout.title_lines, 17.0, "bold")
    if layout.subtitle_lines:
        _svg_text(parts, MARGIN, title_y + len(layout.title_lines)*_lh(17.0) + 5.0,
                  layout.subtitle_lines, 9.0, fill="#666666")
    for card in page.cards:
        state = card.item.get("state") or {}; fill, stroke, text_fill = _palette(state.get("tone"))
        parts.append(f'<rect x="{card.x:.2f}" y="{card.y:.2f}" width="{card.width:.2f}" '
                     f'height="{card.height:.2f}" rx="7" fill="#fff" stroke="{stroke}"/>')
        cursor = card.y + PAD + TITLE; _svg_text(parts, card.x+PAD, cursor, card.title_lines, TITLE, "bold")
        cursor += len(card.title_lines)*_lh(TITLE)
        if state:
            label, bw = state["label"], max(38.0, _chip_width(state["label"])); cursor += 4.0
            parts.append(f'<rect x="{card.x+PAD:.2f}" y="{cursor:.2f}" width="{bw:.2f}" height="16" '
                         f'rx="8" fill="{fill}" stroke="{stroke}"/>')
            _svg_text(parts, card.x+PAD+7, cursor+11.5, [label], SMALL, "bold", text_fill); cursor += 18.0
        if card.meta_lines:
            cursor += 4.0; _svg_text(parts, card.x+PAD, cursor+SMALL, card.meta_lines, SMALL, fill="#666")
            cursor += len(card.meta_lines)*_lh(SMALL)
        for heading, bullets in card.sections:
            cursor += 9.0; _svg_text(parts, card.x+PAD, cursor+HEADING, [heading], HEADING, "bold", "#4b5b6b")
            cursor += _lh(HEADING)+2.0
            for lines in bullets:
                parts.append(f'<circle cx="{card.x+PAD+3:.2f}" cy="{cursor+4.1:.2f}" r="1.6" fill="#4b78a8"/>')
                _svg_text(parts, card.x+PAD+10, cursor+BODY, lines, BODY); cursor += len(lines)*_lh(BODY)+3.0
        if card.badge_rows:
            cursor += 7.0
            for row in card.badge_rows:
                bx = card.x+PAD
                for badge in row:
                    bf, bs, bt = _palette(badge.get("tone")); bw = _chip_width(badge["label"])
                    parts.append(f'<rect x="{bx:.2f}" y="{cursor:.2f}" width="{bw:.2f}" height="16" '
                                 f'rx="5" fill="{bf}" stroke="{bs}"/>')
                    _svg_text(parts, bx+6, cursor+11.5, [badge["label"]], SMALL, "bold", bt); bx += bw+6
                cursor += 20.0
    _svg_text(parts, PW-MARGIN-48, PH-14, [f"Page {page.number}/{len(layout.pages)}"], SMALL, fill="#777")
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


def _pdf_text(c, x, top, lines, size, bold=False, fill=(.18,.20,.22)):
    c.setFont("Helvetica-Bold" if bold else "Helvetica", size); c.setFillColorRGB(*fill); y = PH-top
    for line in lines: c.drawString(x, y, str(line)); y -= _lh(size)


def render_pdf(layout, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True); c = canvas.Canvas(str(path), pagesize=(PW,PH))
    for page in layout.pages:
        title_y=MARGIN+17; _pdf_text(c,MARGIN,title_y,layout.title_lines,17,True)
        if layout.subtitle_lines: _pdf_text(c,MARGIN,title_y+len(layout.title_lines)*_lh(17)+5,layout.subtitle_lines,9,fill=(.4,.4,.4))
        for card in page.cards:
            state=card.item.get("state") or {}; _,stroke,_=_palette(state.get("tone")); c.setStrokeColorRGB(*_hex(stroke)); c.setFillColorRGB(1,1,1)
            c.roundRect(card.x,PH-card.y-card.height,card.width,card.height,7,stroke=1,fill=1)
            cursor=card.y+PAD+TITLE; _pdf_text(c,card.x+PAD,cursor,card.title_lines,TITLE,True); cursor+=len(card.title_lines)*_lh(TITLE)
            if state:
                label=state["label"]; fill,stroke,text=_palette(state.get("tone")); bw=max(38,_chip_width(label)); cursor+=4
                c.setFillColorRGB(*_hex(fill)); c.setStrokeColorRGB(*_hex(stroke)); c.roundRect(card.x+PAD,PH-cursor-16,bw,16,8,stroke=1,fill=1)
                _pdf_text(c,card.x+PAD+7,cursor+11.5,[label],SMALL,True,_hex(text)); cursor+=18
            if card.meta_lines:
                cursor+=4; _pdf_text(c,card.x+PAD,cursor+SMALL,card.meta_lines,SMALL,fill=(.4,.4,.4)); cursor+=len(card.meta_lines)*_lh(SMALL)
            for heading,bullets in card.sections:
                cursor+=9; _pdf_text(c,card.x+PAD,cursor+HEADING,[heading],HEADING,True,(.29,.36,.42)); cursor+=_lh(HEADING)+2
                for lines in bullets:
                    c.setFillColorRGB(.29,.47,.66); c.circle(card.x+PAD+3,PH-(cursor+4.1),1.6,stroke=0,fill=1)
                    _pdf_text(c,card.x+PAD+10,cursor+BODY,lines,BODY); cursor+=len(lines)*_lh(BODY)+3
            if card.badge_rows:
                cursor+=7
                for row in card.badge_rows:
                    bx=card.x+PAD
                    for badge in row:
                        bf,bs,bt=_palette(badge.get("tone")); bw=_chip_width(badge["label"]); c.setFillColorRGB(*_hex(bf)); c.setStrokeColorRGB(*_hex(bs))
                        c.roundRect(bx,PH-cursor-16,bw,16,5,stroke=1,fill=1); _pdf_text(c,bx+6,cursor+11.5,[badge["label"]],SMALL,True,_hex(bt)); bx+=bw+6
                    cursor+=20
        _pdf_text(c,PW-MARGIN-48,PH-14,[f"Page {page.number}/{len(layout.pages)}"],SMALL,fill=(.47,.47,.47)); c.showPage()
    c.save()


def generate(source: Path, schema_path: Path, out_dir: Path):
    if not source.is_file(): raise ValueError(f"roadmap source file does not exist: {source}")
    data=yaml.safe_load(source.read_text(encoding="utf-8")); validate_source(data, load_schema(schema_path), source)
    layout=layout_roadmap(data); render_svg(layout,out_dir); render_pdf(layout,out_dir/"roadmap.pdf"); return layout
