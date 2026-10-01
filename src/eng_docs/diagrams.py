"""Declarative engineering-diagram validation and rendering."""

from __future__ import annotations

from pathlib import Path
import html
import json
import textwrap
import xml.etree.ElementTree as ET

import yaml
from jsonschema import Draft202012Validator


def load_yaml(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def validate_source(data, schema, path: Path):
    errors = sorted(Draft202012Validator(schema).iter_errors(data), key=lambda e: list(e.path))
    if errors:
        lines = [f"{path}: invalid diagram source"]
        for err in errors:
            loc = ".".join(str(x) for x in err.path) or "<root>"
            lines.append(f"  {loc}: {err.message}")
        raise ValueError("\n".join(lines))


def validate_refs(data, theme, path: Path):
    group_ids = [g["id"] for g in data["groups"]]
    node_ids = [n["id"] for n in data["nodes"]]
    if len(set(group_ids)) != len(group_ids):
        raise ValueError(f"{path}: duplicate group id")
    if len(set(node_ids)) != len(node_ids):
        raise ValueError(f"{path}: duplicate node id")
    def item_object_ids(items):
        result = []
        for item in items or []:
            if isinstance(item, str):
                continue
            if item.get("object_id"):
                result.append(item["object_id"])
            result.extend(item_object_ids(item.get("items", [])))
        return result

    object_ids = [
        group["object_id"]
        for group in data["groups"]
        if group.get("object_id")
    ]
    for node in data["nodes"]:
        if node.get("object_id"):
            object_ids.append(node["object_id"])
        object_ids.extend(item_object_ids(node.get("items", [])))
    if len(set(object_ids)) != len(object_ids):
        duplicates = sorted(
            object_id for object_id in set(object_ids)
            if object_ids.count(object_id) > 1
        )
        raise ValueError(f"{path}: duplicate diagram object_id: {duplicates}")
    overlap = set(group_ids) & set(node_ids)
    if overlap:
        raise ValueError(f"{path}: ids reused by group and node: {sorted(overlap)}")

    known_groups = set(group_ids)
    known_nodes = set(node_ids)
    known_endpoints = known_groups | known_nodes
    kinds = theme.get("kinds", {})
    for item in [*data["groups"], *data["nodes"]]:
        if item["kind"] not in kinds:
            raise ValueError(f"{path}: unknown kind {item['kind']!r} on {item['id']}")
    for group in data["groups"]:
        if group.get("outline") and group.get("notation"):
            raise ValueError(
                f"{path}: group {group['id']} cannot combine outline with notation"
            )
        if group.get("outline"):
            points = {
                (point["x"], point["y"])
                for point in group["outline"]["points"]
            }
            if len(points) < 3:
                raise ValueError(
                    f"{path}: group {group['id']} outline needs at least three distinct points"
                )
    for node in data["nodes"]:
        if node.get("group") and node["group"] not in known_groups:
            raise ValueError(f"{path}: node {node['id']} references missing group {node['group']}")
    for edge in data["edges"]:
        if edge["from"] not in known_endpoints or edge["to"] not in known_endpoints:
            raise ValueError(
                f"{path}: edge references missing endpoint: {edge['from']} -> {edge['to']}"
            )


def _style(theme, kind):
    return theme["kinds"][kind]


def _outline_canvas_points(group):
    """Map normalized group outline coordinates into the group's layout box."""
    r = group["layout"]
    return [
        (
            r["x"] + point["x"] * r["w"],
            r["y"] + point["y"] * r["h"],
        )
        for point in group.get("outline", {}).get("points", [])
    ]


def _rounded_outline_path(points, corner_radius):
    """Return an SVG path for a polygon with rounded vertices."""
    if not points:
        return ""
    if corner_radius <= 0:
        return " ".join(
            [f"M {points[0][0]:.1f} {points[0][1]:.1f}"]
            + [f"L {x:.1f} {y:.1f}" for x, y in points[1:]]
            + ["Z"]
        )

    def toward(start, end, distance):
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        length = (dx * dx + dy * dy) ** 0.5
        if length == 0:
            return start
        scale = min(distance, length / 2) / length
        return start[0] + dx * scale, start[1] + dy * scale

    rounded = []
    count = len(points)
    for index, current in enumerate(points):
        previous = points[(index - 1) % count]
        following = points[(index + 1) % count]
        entry = toward(current, previous, corner_radius)
        exit_point = toward(current, following, corner_radius)
        rounded.append((entry, current, exit_point))

    commands = [
        f"M {rounded[-1][2][0]:.1f} {rounded[-1][2][1]:.1f}"
    ]
    for entry, current, exit_point in rounded:
        commands.append(f"L {entry[0]:.1f} {entry[1]:.1f}")
        commands.append(
            f"Q {current[0]:.1f} {current[1]:.1f} "
            f"{exit_point[0]:.1f} {exit_point[1]:.1f}"
        )
    commands.append("Z")
    return " ".join(commands)


def _drawio_outline_coords(outline):
    return json.dumps(
        [
            [point["x"], point["y"]]
            for point in outline["points"]
        ],
        separators=(",", ":"),
    )


def _center(item):
    r = item["layout"]
    return r["x"] + r["w"] / 2, r["y"] + r["h"] / 2


def _simplify_polyline(points):
    cleaned = []
    for point in points:
        if cleaned and point == cleaned[-1]:
            continue
        cleaned.append(point)

    simplified = []
    for point in cleaned:
        if len(simplified) >= 2:
            ax, ay = simplified[-2]
            bx, by = simplified[-1]
            cx, cy = point
            if (ax == bx == cx) or (ay == by == cy):
                simplified[-1] = point
                continue
        simplified.append(point)
    return simplified


def _anchor_point(item, anchor):
    r = item["layout"]
    side = anchor["side"]
    position = anchor.get("position", 0.5)
    if side == "top":
        return r["x"] + r["w"] * position, r["y"]
    if side == "right":
        return r["x"] + r["w"], r["y"] + r["h"] * position
    if side == "bottom":
        return r["x"] + r["w"] * position, r["y"] + r["h"]
    if side == "left":
        return r["x"], r["y"] + r["h"] * position
    raise ValueError(f"unknown anchor side: {side}")


def _inferred_anchor(item, target_point):
    sx, sy = _center(item)
    tx, ty = target_point
    dx, dy = tx - sx, ty - sy
    if abs(dx) >= abs(dy):
        return {"side": "right" if dx >= 0 else "left", "position": 0.5}
    return {"side": "bottom" if dy >= 0 else "top", "position": 0.5}


def _anchor_to_point(item, anchor, point):
    """Return an orthogonal path from one explicit box anchor to a point."""
    start = _anchor_point(item, anchor)
    px, py = point
    sx, sy = start
    if anchor["side"] in ("left", "right"):
        return _simplify_polyline([start, (px, sy), point])
    return _simplify_polyline([start, (sx, py), point])


def _box_to_point(item, point):
    """Return an orthogonal path from an inferred box boundary to a point."""
    return _anchor_to_point(item, _inferred_anchor(item, point), point)


def _connect_anchors(source, source_anchor, target, target_anchor):
    start = _anchor_point(source, source_anchor)
    end = _anchor_point(target, target_anchor)
    sx, sy = start
    tx, ty = end
    source_horizontal = source_anchor["side"] in ("left", "right")
    target_horizontal = target_anchor["side"] in ("left", "right")

    if sx == tx or sy == ty:
        return [start, end]
    if source_horizontal and target_horizontal:
        mid_x = (sx + tx) / 2
        return _simplify_polyline([start, (mid_x, sy), (mid_x, ty), end])
    if not source_horizontal and not target_horizontal:
        mid_y = (sy + ty) / 2
        return _simplify_polyline([start, (sx, mid_y), (tx, mid_y), end])
    if source_horizontal:
        return _simplify_polyline([start, (tx, sy), end])
    return _simplify_polyline([start, (sx, ty), end])


def _auto_orthogonal_points(source, target):
    source_anchor = _inferred_anchor(source, _center(target))
    target_anchor = _inferred_anchor(target, _center(source))
    return _connect_anchors(source, source_anchor, target, target_anchor)


def _edge_points(source, target, edge):
    route = [(p["x"], p["y"]) for p in edge.get("route", [])]
    source_anchor = edge.get("from_anchor")
    target_anchor = edge.get("to_anchor")

    if not route:
        if source_anchor or target_anchor:
            source_anchor = source_anchor or _inferred_anchor(source, _center(target))
            target_anchor = target_anchor or _inferred_anchor(target, _center(source))
            return _connect_anchors(source, source_anchor, target, target_anchor)
        return _auto_orthogonal_points(source, target)

    source_connection = (
        _anchor_to_point(source, source_anchor, route[0])
        if source_anchor
        else _box_to_point(source, route[0])
    )
    target_connection = list(
        reversed(
            _anchor_to_point(target, target_anchor, route[-1])
            if target_anchor
            else _box_to_point(target, route[-1])
        )
    )
    return _simplify_polyline(source_connection[:-1] + route + target_connection[1:])


def _label_point(points):
    segments = []
    for first, second in zip(points, points[1:]):
        length = abs(second[0] - first[0]) + abs(second[1] - first[1])
        segments.append((length, first, second))
    if not segments:
        return points[0]
    _, first, second = max(segments, key=lambda item: item[0])
    return (first[0] + second[0]) / 2, (first[1] + second[1]) / 2


def _flatten_node_items(items, depth=0):
    rows = []
    for item in items or []:
        if isinstance(item, str):
            rows.append((depth, item, None))
            continue
        rows.append((depth, item["label"], item.get("object_id")))
        rows.extend(_flatten_node_items(item.get("items", []), depth + 1))
    return rows


def _item_line(depth, label):
    marker = "• " if depth == 0 else "└─ "
    return f"{marker}{label}"


def _svg_text(parts, text, x, y, size, family, weight="normal", anchor="middle"):
    lines = str(text).splitlines() or [""]
    line_height = size * 1.28
    start = y - (len(lines) - 1) * line_height / 2
    for i, line in enumerate(lines):
        parts.append(
            f'<text x="{x:.1f}" y="{start + i * line_height:.1f}" text-anchor="{anchor}" '
            f'dominant-baseline="middle" font-family="{html.escape(family)}" '
            f'font-size="{size}" font-weight="{weight}" fill="#202124">{html.escape(line)}</text>'
        )


def _svg_component_glyph(parts, node, stroke):
    r = node["layout"]
    x = r["x"] + r["w"] - 34
    y = r["y"] + 8
    parts.append(
        f'<g data-notation="component" fill="none" stroke="{stroke}" stroke-width="1.7">'
        f'<rect x="{x + 8}" y="{y}" width="20" height="22"/>'
        f'<rect x="{x}" y="{y + 4}" width="11" height="6" fill="white"/>'
        f'<rect x="{x}" y="{y + 14}" width="11" height="6" fill="white"/>'
        '</g>'
    )


def _svg_packaging_component_glyph(parts, node, stroke):
    r = node["layout"]
    x = r["x"] + r["w"] - 36
    y = r["y"] + 7
    parts.append(
        f'<g data-notation="packaging-component" fill="none" stroke="{stroke}" stroke-width="1.6">'
        # Integrated package + component notation: the package body is also the
        # component body, with the UML component tabs crossing its left edge.
        f'<path d="M{x + 1},{y + 5} v-4 h11 l3,4 h14 v18 h-28 z" fill="white"/>'
        f'<rect x="{x - 1}" y="{y + 9}" width="8" height="4" fill="white"/>'
        f'<rect x="{x - 1}" y="{y + 15}" width="8" height="4" fill="white"/>'
        '</g>'
    )


def _svg_class_node_text(parts, node, theme, family):
    r = node["layout"]
    x = r["x"] + r["w"] / 2
    node_size = theme["font"]["node_size"]
    detail_size = theme["font"].get("node_subtitle_size", max(9, node_size - 3))
    stroke = _style(theme, node["kind"])["stroke"]

    _svg_text(parts, "«class»", x, r["y"] + 13, detail_size, family)
    _svg_text(parts, node["label"], x, r["y"] + 31, node_size, family)
    separator_y = r["y"] + 44
    parts.append(
        f'<line x1="{r["x"]}" y1="{separator_y}" x2="{r["x"] + r["w"]}" y2="{separator_y}" '
        f'stroke="{stroke}" stroke-width="1"/>'
    )

    cursor = separator_y + 14
    for depth, item_label, object_id in _flatten_node_items(node.get("items", [])):
        prefix = "- " if depth == 0 else "  - "
        if object_id:
            parts.append(
                f'<g data-engineering-id="{html.escape(object_id, quote=True)}">'
            )
        _svg_text(
            parts,
            prefix + item_label,
            r["x"] + 14 + depth * 12,
            cursor,
            detail_size,
            family,
            anchor="start",
        )
        if object_id:
            parts.append("</g>")
        cursor += detail_size * 1.45


def _svg_node_text(parts, node, theme, family):
    if node.get("notation") == "class":
        _svg_class_node_text(parts, node, theme, family)
        return

    r = node["layout"]
    label = str(node["label"])
    subtitle = node.get("subtitle")
    items = _flatten_node_items(node.get("items", []))
    x = r["x"] + r["w"] / 2
    center_y = r["y"] + r["h"] / 2
    node_size = theme["font"]["node_size"]
    subtitle_size = theme["font"].get("node_subtitle_size", max(9, node_size - 3))

    if not subtitle and not items:
        _svg_text(parts, label, x, center_y, node_size, family)
        return

    label_lines = label.splitlines() or [""]
    subtitle_lines = str(subtitle).splitlines() if subtitle else []
    label_height = len(label_lines) * node_size * 1.28
    subtitle_height = len(subtitle_lines) * subtitle_size * 1.28
    item_line_height = subtitle_size * 1.38
    items_height = len(items) * item_line_height
    gaps = 0
    if subtitle_lines:
        gaps += 5
    if items:
        gaps += 7
    total_height = label_height + subtitle_height + items_height + gaps
    # Structured nodes read like compact component cards: keep the heading at
    # the top and let the item hierarchy flow downward. Subtitle-only nodes
    # remain vertically balanced.
    top = r["y"] + 14 if items else center_y - total_height / 2

    label_center = top + label_height / 2
    _svg_text(parts, label, x, label_center, node_size, family)
    cursor = top + label_height

    if subtitle_lines:
        cursor += 5
        subtitle_center = cursor + subtitle_height / 2
        _svg_text(parts, subtitle, x, subtitle_center, subtitle_size, family)
        cursor += subtitle_height

    if items:
        cursor += 7
        item_x = r["x"] + 16
        for depth, item_label, object_id in items:
            row_y = cursor + item_line_height / 2
            if object_id:
                parts.append(
                    f'<g data-engineering-id="{html.escape(object_id, quote=True)}">'
                )
            _svg_text(
                parts,
                _item_line(depth, item_label),
                item_x + depth * 12,
                row_y,
                subtitle_size,
                family,
                anchor="start",
            )
            if object_id:
                parts.append("</g>")
            cursor += item_line_height


def _drawio_node_value(node, theme):
    label = html.escape(str(node["label"])).replace("\n", "<br>")
    if node.get("notation") == "class":
        detail_size = theme["font"].get(
            "node_subtitle_size",
            max(9, theme["font"]["node_size"] - 3),
        )
        attrs = _flatten_node_items(node.get("items", []))
        attr_rows = []
        for depth, item_label, object_id in attrs:
            row = ("&nbsp;" * (depth * 4)) + html.escape(
                ("- " if depth == 0 else "  - ") + item_label
            )
            if object_id:
                row = (
                    f'<span data-engineering-id="{html.escape(object_id, quote=True)}">'
                    f"{row}</span>"
                )
            attr_rows.append(row)
        attr_html = "<br>".join(attr_rows)
        return (
            f'<span style="font-size:{detail_size}px">«class»</span><br>'
            f'{label}<hr>'
            f'<div style="text-align:left;font-size:{detail_size}px;margin-left:10px">{attr_html}</div>'
        )
    subtitle = node.get("subtitle")
    items = _flatten_node_items(node.get("items", []))
    if not subtitle and not items:
        return label

    subtitle_size = theme["font"].get(
        "node_subtitle_size",
        max(9, theme["font"]["node_size"] - 3),
    )
    parts = [label]
    if subtitle:
        subtitle_html = html.escape(str(subtitle)).replace("\n", "<br>")
        parts.append(
            f'<span style="font-size:{subtitle_size}px">{subtitle_html}</span>'
        )
    if items:
        rows = []
        for depth, item_label, object_id in items:
            indent = "&nbsp;" * (depth * 4)
            marker = "• " if depth == 0 else "└─ "
            row = f"{indent}{html.escape(marker + item_label)}"
            if object_id:
                row = (
                    f'<span data-engineering-id="{html.escape(object_id, quote=True)}">'
                    f"{row}</span>"
                )
            rows.append(row)
        parts.append(
            f'<div style="text-align:left;font-size:{subtitle_size}px;'
            f'margin-left:12px">{"<br>".join(rows)}</div>'
        )
    return "<br>".join(parts)


def _group_properties_geometry(group, theme):
    r = group["layout"]
    properties = group.get("properties", [])
    if not properties:
        return None

    property_size = theme["font"].get(
        "node_subtitle_size",
        max(9, theme["font"]["node_size"] - 3),
    )
    label_offset = group.get("label_offset", {"x": 0, "y": 0})
    note_lines = str(group.get("note", "")).splitlines() if group.get("note") else []
    note_height = len(note_lines) * theme["font"]["note_size"] * 1.28
    top = r["y"] + 40 + label_offset["y"] + note_height
    longest = max(len(str(item)) for item in properties)
    automatic_width = max(
        150,
        min(r["w"] - 40, longest * property_size * 0.62 + 34),
    )
    width = group.get("properties_width", automatic_width)
    height = 14 + len(properties) * property_size * 1.45
    return {
        "x": r["x"] + 20 + label_offset["x"],
        "y": top,
        "w": width,
        "h": height,
        "font_size": property_size,
    }


def render_svg(data, theme, out: Path):
    d = data["diagram"]
    family = theme["font"]["family"]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{d["width"]}" height="{d["height"]}" viewBox="0 0 {d["width"]} {d["height"]}">',
        "<defs>",
        '<marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto" markerUnits="strokeWidth">',
        f'<path d="M0,0 L0,6 L9,3 z" fill="{theme["canvas"]["edge"]}"/>',
        "</marker>",
        "</defs>",
        f'<rect width="100%" height="100%" fill="{theme["canvas"]["background"]}"/>',
    ]
    _svg_text(parts, d["title"], 30, 38, theme["font"]["title_size"], family, "bold", "start")
    if d.get("note"):
        _svg_text(parts, d["note"], 30, 68, theme["font"]["note_size"], family, "normal", "start")

    for group in data["groups"]:
        r = group["layout"]
        s = _style(theme, group["kind"])
        object_id = group.get("object_id")
        if object_id:
            parts.append(
                f'<g data-engineering-id="{html.escape(object_id, quote=True)}">'
            )
        if group.get("outline"):
            outline_points = _outline_canvas_points(group)
            corner_radius = group["outline"].get("corner_radius", 0)
            if corner_radius > 0:
                path_data = _rounded_outline_path(outline_points, corner_radius)
                parts.append(
                    f'<path data-outline="polygon" d="{path_data}" '
                    f'fill="{s["fill"]}" stroke="{s["stroke"]}" stroke-width="2" '
                    f'stroke-linejoin="round"/>'
                )
            else:
                points = " ".join(
                    f"{x:.1f},{y:.1f}"
                    for x, y in outline_points
                )
                parts.append(
                    f'<polygon data-outline="polygon" points="{points}" '
                    f'fill="{s["fill"]}" stroke="{s["stroke"]}" stroke-width="2" '
                    f'stroke-linejoin="round"/>'
                )
        else:
            parts.append(
                f'<rect x="{r["x"]}" y="{r["y"]}" width="{r["w"]}" height="{r["h"]}" '
                f'rx="10" ry="10" fill="{s["fill"]}" stroke="{s["stroke"]}" stroke-width="2"/>'
            )
        if group.get("notation") == "component":
            _svg_component_glyph(parts, group, s["stroke"])
        elif group.get("notation") == "packaging-component":
            _svg_packaging_component_glyph(parts, group, s["stroke"])
        label_offset = group.get("label_offset", {"x": 0, "y": 0})
        text_x = r["x"] + 16 + label_offset["x"]
        _svg_text(
            parts,
            group["label"],
            text_x,
            r["y"] + 22 + label_offset["y"],
            theme["font"]["group_title_size"],
            family,
            "bold",
            "start",
        )
        note_bottom = r["y"] + 35 + label_offset["y"]
        if group.get("note"):
            note_size = theme["font"]["note_size"]
            note_lines = str(group["note"]).splitlines() or [""]
            note_y = (
                r["y"]
                + 45
                + label_offset["y"]
                + (len(note_lines) - 1) * note_size * 1.28 / 2
            )
            _svg_text(
                parts,
                group["note"],
                text_x,
                note_y,
                note_size,
                family,
                "normal",
                "start",
            )
            note_bottom = note_y + len(note_lines) * note_size * 1.28 / 2

        properties = group.get("properties", [])
        property_box = _group_properties_geometry(group, theme)
        if property_box:
            parts.append(
                f'<rect data-group-properties="true" '
                f'x="{property_box["x"]:.1f}" y="{property_box["y"]:.1f}" '
                f'width="{property_box["w"]:.1f}" height="{property_box["h"]:.1f}" '
                f'rx="4" ry="4" fill="{theme["canvas"]["background"]}" '
                f'stroke="{s["stroke"]}" stroke-width="1"/>'
            )
            cursor = property_box["y"] + 17
            for property_label in properties:
                _svg_text(
                    parts,
                    "- " + property_label,
                    property_box["x"] + 10,
                    cursor,
                    property_box["font_size"],
                    family,
                    "normal",
                    "start",
                )
                cursor += property_box["font_size"] * 1.45
        if object_id:
            parts.append("</g>")

    endpoints = {g["id"]: g for g in data["groups"]}
    endpoints.update({n["id"]: n for n in data["nodes"]})
    for edge in data["edges"]:
        source = endpoints[edge["from"]]
        target = endpoints[edge["to"]]
        points = _edge_points(source, target, edge)
        dash = ' stroke-dasharray="7 5"' if edge.get("dashed") else ""
        pts = " ".join(f"{x:.1f},{y:.1f}" for x, y in points)
        parts.append(
            f'<polyline points="{pts}" fill="none" stroke="{theme["canvas"]["edge"]}" stroke-width="2"{dash} marker-end="url(#arrow)"/>'
        )
        if edge.get("label"):
            mx, my = _label_point(points)
            label = edge["label"]
            width = max(80, min(190, 8 * len(label)))
            parts.append(
                f'<rect x="{mx - width / 2:.1f}" y="{my - 13:.1f}" width="{width}" height="22" '
                f'fill="{theme["canvas"]["edge_label_background"]}" opacity="0.94"/>'
            )
            _svg_text(parts, label, mx, my - 1, 12, family)

    for node in data["nodes"]:
        r = node["layout"]
        s = _style(theme, node["kind"])
        object_id = node.get("object_id")
        if object_id:
            parts.append(
                f'<g data-engineering-id="{html.escape(object_id, quote=True)}">'
            )
        parts.append(
            f'<rect x="{r["x"]}" y="{r["y"]}" width="{r["w"]}" height="{r["h"]}" '
            f'rx="8" ry="8" fill="{s["fill"]}" stroke="{s["stroke"]}" stroke-width="2"/>'
        )
        if node.get("notation") == "component":
            _svg_component_glyph(parts, node, s["stroke"])
        elif node.get("notation") == "packaging-component":
            _svg_packaging_component_glyph(parts, node, s["stroke"])
        _svg_node_text(parts, node, theme, family)
        if object_id:
            parts.append("</g>")

    parts.append("</svg>")
    out.write_text("\n".join(parts) + "\n", encoding="utf-8")


def _drawio_node_style(
    theme,
    kind,
    group=False,
    notation=None,
    outline=None,
    label_offset=None,
):
    s = _style(theme, kind)
    rounded = 1
    if outline and outline.get("corner_radius", 0) <= 0:
        rounded = 0
    result = (
        f"rounded={rounded};whiteSpace=wrap;html=1;"
        f"fillColor={s['fill']};strokeColor={s['stroke']};fontFamily=Helvetica;"
    )
    if group:
        label_offset = label_offset or {"x": 0, "y": 0}
        result += (
            "verticalAlign=top;align=left;"
            f"spacingTop={8 + label_offset['y']};"
            f"spacingLeft={10 + label_offset['x']};"
            "fontStyle=1;fontSize=17;"
        )
    else:
        result += "fontSize=14;"
    if outline:
        result += (
            "shape=mxgraph.basic.polygon;"
            f"polyCoords={_drawio_outline_coords(outline)};"
            "polyline=0;"
        )
    elif notation == "component":
        result += "shape=component;"
    elif notation == "packaging-component":
        result += "shape=component;container=1;"
    elif notation == "class":
        result += "rounded=0;verticalAlign=top;align=center;spacingTop=3;"
    return result


def _drawio_anchor_style(anchor, prefix):
    if not anchor:
        return ""
    side = anchor["side"]
    position = anchor.get("position", 0.5)
    if side == "top":
        x, y = position, 0
    elif side == "right":
        x, y = 1, position
    elif side == "bottom":
        x, y = position, 1
    elif side == "left":
        x, y = 0, position
    else:
        raise ValueError(f"unknown anchor side: {side}")
    return f"{prefix}X={x};{prefix}Y={y};{prefix}Dx=0;{prefix}Dy=0;{prefix}Perimeter=1;"


def render_drawio(data, theme, out: Path):
    d = data["diagram"]
    mxfile = ET.Element("mxfile", host="app.diagrams.net", compressed="false")
    diagram = ET.SubElement(mxfile, "diagram", id=d["id"], name=d["title"])
    model = ET.SubElement(
        diagram, "mxGraphModel", dx="1200", dy="800", grid="1", gridSize="10",
        guides="1", tooltips="1", connect="1", arrows="1", fold="1", page="1",
        pageScale="1", pageWidth=str(d["width"]), pageHeight=str(d["height"]), math="0", shadow="0"
    )
    root = ET.SubElement(model, "root")
    ET.SubElement(root, "mxCell", id="0")
    ET.SubElement(root, "mxCell", id="1", parent="0")

    for group in data["groups"]:
        r = group["layout"]
        value = html.escape(group["label"])
        if group.get("note"):
            note = "<br>".join(html.escape(line) for line in str(group["note"]).splitlines())
            value = (
                f"<b>{value}</b><br>"
                f'<span style="font-size:{theme["font"]["note_size"]}px;font-weight:normal;">'
                f"{note}</span>"
            )
        attrs = {
            "id": f"group-{group['id']}",
            "value": value,
            "style": _drawio_node_style(
                theme,
                group["kind"],
                True,
                group.get("notation"),
                group.get("outline"),
                group.get("label_offset"),
            ),
            "vertex": "1",
            "parent": "1",
        }
        if group.get("object_id"):
            attrs["data-engineering-id"] = group["object_id"]
        cell = ET.SubElement(root, "mxCell", **attrs)
        ET.SubElement(cell, "mxGeometry", x=str(r["x"]), y=str(r["y"]), width=str(r["w"]), height=str(r["h"]), **{"as": "geometry"})

        property_box = _group_properties_geometry(group, theme)
        if property_box:
            property_value = "<br>".join(
                html.escape("- " + str(item)) for item in group["properties"]
            )
            property_style = (
                "rounded=1;whiteSpace=wrap;html=1;verticalAlign=top;align=left;"
                f"fillColor={theme['canvas']['background']};strokeColor={_style(theme, group['kind'])['stroke']};"
                f"fontFamily=Helvetica;fontSize={property_box['font_size']};"
                "spacingTop=6;spacingLeft=6;fontStyle=0;"
            )
            property_cell = ET.SubElement(
                root,
                "mxCell",
                id=f"group-{group['id']}-properties",
                value=property_value,
                style=property_style,
                vertex="1",
                parent="1",
            )
            ET.SubElement(
                property_cell,
                "mxGeometry",
                x=str(property_box["x"]),
                y=str(property_box["y"]),
                width=str(property_box["w"]),
                height=str(property_box["h"]),
                **{"as": "geometry"},
            )

    for node in data["nodes"]:
        r = node["layout"]
        attrs = {
            "id": node["id"],
            "value": _drawio_node_value(node, theme),
            "style": _drawio_node_style(
                theme, node["kind"], notation=node.get("notation")
            ),
            "vertex": "1",
            "parent": "1",
        }
        if node.get("object_id"):
            attrs["data-engineering-id"] = node["object_id"]
        cell = ET.SubElement(root, "mxCell", attrs)
        ET.SubElement(cell, "mxGeometry", x=str(r["x"]), y=str(r["y"]), width=str(r["w"]), height=str(r["h"]), **{"as": "geometry"})

    group_ids = {group["id"] for group in data["groups"]}

    for i, edge in enumerate(data["edges"], 1):
        edge_style = "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;endFill=1;"
        edge_style += _drawio_anchor_style(edge.get("from_anchor"), "exit")
        edge_style += _drawio_anchor_style(edge.get("to_anchor"), "entry")
        if edge.get("dashed"):
            edge_style += "dashed=1;"
        cell = ET.SubElement(
            root, "mxCell", id=f"edge-{i}", value=edge.get("label", ""), style=edge_style,
            edge="1", parent="1",
            source=f"group-{edge['from']}" if edge["from"] in group_ids else edge["from"],
            target=f"group-{edge['to']}" if edge["to"] in group_ids else edge["to"],
        )
        geom = ET.SubElement(cell, "mxGeometry", relative="1", **{"as": "geometry"})
        if edge.get("route"):
            points = ET.SubElement(geom, "Array", **{"as": "points"})
            for point in edge["route"]:
                ET.SubElement(points, "mxPoint", x=str(point["x"]), y=str(point["y"]))

    ET.indent(mxfile, space="  ")
    out.write_text(ET.tostring(mxfile, encoding="unicode") + "\n", encoding="utf-8")



def validate_sequence_refs(data, theme, path: Path):
    participants = data["participants"]
    participant_ids = [participant["id"] for participant in participants]
    if len(set(participant_ids)) != len(participant_ids):
        raise ValueError(f"{path}: duplicate sequence participant id")

    kinds = theme.get("kinds", {})
    for participant in participants:
        if participant["kind"] not in kinds:
            raise ValueError(
                f"{path}: unknown kind {participant['kind']!r} "
                f"on sequence participant {participant['id']}"
            )

    known = set(participant_ids)
    for message in data["messages"]:
        if message["from"] not in known or message["to"] not in known:
            raise ValueError(
                f"{path}: sequence message references missing participant: "
                f"{message['from']} -> {message['to']}"
            )


_SEQUENCE_MESSAGE_FONT_SIZE = 13
_SEQUENCE_MESSAGE_BASE_GAP = 52.0
_SEQUENCE_MESSAGE_LINE_HEIGHT = _SEQUENCE_MESSAGE_FONT_SIZE * 1.28


def _wrap_sequence_source_line(source_line, max_chars):
    if len(source_line) <= max_chars:
        return [source_line]

    words = source_line.split()
    balanced = []
    for split in range(1, len(words)):
        left = " ".join(words[:split])
        right = " ".join(words[split:])
        if len(left) <= max_chars and len(right) <= max_chars:
            balanced.append((abs(len(left) - len(right)), split, left, right))

    if balanced:
        _, _, left, right = min(balanced)
        return [left, right]

    return textwrap.wrap(
        source_line,
        width=max_chars,
        break_long_words=False,
        break_on_hyphens=False,
    ) or [""]


def _wrap_sequence_message_label(label, max_width):
    """Wrap a sequence-message label using a deterministic width estimate."""
    average_char_width = _SEQUENCE_MESSAGE_FONT_SIZE * 0.56
    max_chars = max(12, int(max_width / average_char_width))
    wrapped = []
    for source_line in str(label).splitlines() or [""]:
        wrapped.extend(_wrap_sequence_source_line(source_line, max_chars))
    return wrapped


def _sequence_layout(data):
    d = data["diagram"]
    participants = data["participants"]
    messages = data["messages"]

    left = 95.0
    right = float(d["width"]) - 95.0
    count = len(participants)
    spacing = (right - left) / (count - 1)
    header_width = min(190.0, max(120.0, spacing * 0.72))
    header_height = 58.0
    header_y = 100.0
    message_start_y = 205.0
    self_message_height = 24.0

    positions = {}
    headers = []
    for index, participant in enumerate(participants):
        center_x = left + index * spacing
        positions[participant["id"]] = center_x
        headers.append(
            {
                "participant": participant,
                "x": center_x - header_width / 2,
                "y": header_y,
                "w": header_width,
                "h": header_height,
                "center_x": center_x,
            }
        )

    message_rows = []
    cursor_y = message_start_y
    for index, message in enumerate(messages):
        from_x = positions[message["from"]]
        to_x = positions[message["to"]]
        if message["from"] == message["to"]:
            max_label_width = min(260.0, max(140.0, spacing - 70.0))
        else:
            max_label_width = max(120.0, abs(to_x - from_x) - 28.0)

        label_lines = _wrap_sequence_message_label(
            message["label"],
            max_label_width,
        )
        if index:
            cursor_y += (
                _SEQUENCE_MESSAGE_BASE_GAP
                + max(0, len(label_lines) - 1) * _SEQUENCE_MESSAGE_LINE_HEIGHT
            )

        message_rows.append(
            {
                "message": message,
                "label": "\n".join(label_lines),
                "label_lines": label_lines,
                "y": cursor_y,
                "from_x": from_x,
                "to_x": to_x,
            }
        )

    if message_rows:
        last_row = message_rows[-1]
        last_extent = (
            self_message_height
            if last_row["message"]["from"] == last_row["message"]["to"]
            else 0.0
        )
        lifeline_bottom = last_row["y"] + last_extent + 35.0
    else:
        lifeline_bottom = message_start_y + 35.0

    if lifeline_bottom > float(d["height"]) - 25.0:
        raise ValueError(
            f"{d['id']}: sequence content exceeds diagram height "
            f"({lifeline_bottom:.0f} > {d['height'] - 25})"
        )

    # Synchronous calls create activation bars on the target. A matching return
    # closes the most recent activation opened by that caller. Unmatched calls
    # remain active through that participant's last interaction, which keeps the
    # notation useful for high-level flows that omit routine returns.
    activations = []
    active = {participant["id"]: [] for participant in participants}
    last_y = {
        participant["id"]: header_y + header_height
        for participant in participants
    }
    activation_index = 0

    for row in message_rows:
        message = row["message"]
        y = row["y"]
        for participant_id in {message["from"], message["to"]}:
            last_y[participant_id] = max(last_y[participant_id], y)

        kind = message.get("kind", "call")
        if kind == "call":
            participant_id = message["to"]
            frame = {
                "id": activation_index,
                "participant": participant_id,
                "caller": message["from"],
                "start_y": y - 10.0,
                "end_y": None,
                "depth": len(active[participant_id]),
            }
            activation_index += 1
            active[participant_id].append(frame)
            activations.append(frame)
        elif kind == "return":
            participant_id = message["from"]
            stack = active[participant_id]
            for stack_index in range(len(stack) - 1, -1, -1):
                if stack[stack_index]["caller"] == message["to"]:
                    frame = stack.pop(stack_index)
                    frame["end_y"] = y + 10.0
                    break

    for participant_id, stack in active.items():
        for frame in stack:
            frame["end_y"] = max(
                frame["start_y"] + 36.0,
                last_y[participant_id] + 18.0,
            )

    return {
        "headers": headers,
        "messages": message_rows,
        "activations": activations,
        "positions": positions,
        "header_width": header_width,
        "header_height": header_height,
        "header_y": header_y,
        "header_bottom": header_y + header_height,
        "lifeline_bottom": lifeline_bottom,
        "self_message_height": self_message_height,
    }


def _sequence_activation_at(layout, participant_id, y):
    matches = [
        activation
        for activation in layout["activations"]
        if activation["participant"] == participant_id
        and activation["start_y"] <= y <= activation["end_y"]
    ]
    if not matches:
        return None
    return max(matches, key=lambda activation: activation["depth"])


def _sequence_message_x(layout, participant_id, y, toward_x):
    center_x = layout["positions"][participant_id]
    activation = _sequence_activation_at(layout, participant_id, y)
    if activation is None:
        return center_x

    width = 12.0
    offset = activation["depth"] * 4.0
    activation_center = center_x + offset
    if toward_x > center_x:
        return activation_center + width / 2
    if toward_x < center_x:
        return activation_center - width / 2
    return activation_center + width / 2


def render_sequence_svg(data, theme, out: Path):
    d = data["diagram"]
    family = theme["font"]["family"]
    edge = theme["canvas"]["edge"]
    layout = _sequence_layout(data)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{d["width"]}" '
        f'height="{d["height"]}" viewBox="0 0 {d["width"]} {d["height"]}">',
        "<defs>",
        '<marker id="seq-filled-arrow" markerWidth="10" markerHeight="10" '
        'refX="9" refY="3" orient="auto" markerUnits="strokeWidth">',
        f'<path d="M0,0 L0,6 L9,3 z" fill="{edge}"/>',
        "</marker>",
        '<marker id="seq-open-arrow" markerWidth="10" markerHeight="10" '
        'refX="9" refY="3" orient="auto" markerUnits="strokeWidth">',
        f'<path d="M0,0 L9,3 L0,6" fill="none" stroke="{edge}" stroke-width="1.5"/>',
        "</marker>",
        "</defs>",
        f'<rect width="100%" height="100%" fill="{theme["canvas"]["background"]}"/>',
    ]
    _svg_text(
        parts,
        d["title"],
        30,
        38,
        theme["font"]["title_size"],
        family,
        "bold",
        "start",
    )
    if d.get("note"):
        _svg_text(
            parts,
            d["note"],
            30,
            68,
            theme["font"]["note_size"],
            family,
            "normal",
            "start",
        )

    # UML lifeline: rectangular participant head + dashed vertical lifeline.
    for header in layout["headers"]:
        participant = header["participant"]
        style = _style(theme, participant["kind"])
        parts.append(
            f'<rect x="{header["x"]:.1f}" y="{header["y"]:.1f}" '
            f'width="{header["w"]:.1f}" height="{header["h"]:.1f}" '
            f'fill="{style["fill"]}" stroke="{style["stroke"]}" stroke-width="2"/>'
        )
        _svg_text(
            parts,
            participant["label"],
            header["center_x"],
            header["y"] + header["h"] / 2,
            theme["font"]["node_size"],
            family,
        )
        parts.append(
            f'<line data-sequence-lifeline="{html.escape(participant["id"], quote=True)}" '
            f'x1="{header["center_x"]:.1f}" y1="{layout["header_bottom"]:.1f}" '
            f'x2="{header["center_x"]:.1f}" y2="{layout["lifeline_bottom"]:.1f}" '
            f'stroke="{edge}" stroke-width="1.4" stroke-dasharray="5 5"/>'
        )

    for activation in layout["activations"]:
        participant = next(
            header["participant"]
            for header in layout["headers"]
            if header["participant"]["id"] == activation["participant"]
        )
        style = _style(theme, participant["kind"])
        center_x = layout["positions"][activation["participant"]] + activation["depth"] * 4.0
        x = center_x - 6.0
        height = activation["end_y"] - activation["start_y"]
        parts.append(
            f'<rect data-sequence-activation="{activation["id"]}" '
            f'x="{x:.1f}" y="{activation["start_y"]:.1f}" '
            f'width="12.0" height="{height:.1f}" '
            f'fill="{style["fill"]}" stroke="{style["stroke"]}" stroke-width="1.4"/>'
        )

    for index, row in enumerate(layout["messages"], 1):
        message = row["message"]
        kind = message.get("kind", "call")
        dashed = ' stroke-dasharray="7 5"' if kind == "return" else ""
        marker = "seq-filled-arrow" if kind == "call" else "seq-open-arrow"
        is_self = message["from"] == message["to"]

        if is_self:
            x = _sequence_message_x(
                layout,
                message["from"],
                row["y"],
                row["from_x"] + 1.0,
            )
            loop_x = x + 42.0
            target_y = row["y"] + layout["self_message_height"]
            target_x = _sequence_message_x(
                layout,
                message["to"],
                target_y,
                row["to_x"] + 1.0,
            )
            parts.append(
                f'<path data-sequence-message="{index}" data-sequence-self-message="true" '
                f'd="M {x:.1f} {row["y"]:.1f} H {loop_x:.1f} '
                f'V {target_y:.1f} H {target_x:.1f}" '
                f'fill="none" stroke="{edge}" stroke-width="2"{dashed} '
                f'marker-end="url(#{marker})"/>'
            )
            _svg_text(
                parts,
                row["label"],
                x + 8.0,
                row["y"] - 12,
                _SEQUENCE_MESSAGE_FONT_SIZE,
                family,
                anchor="start",
            )
            continue

        from_x = _sequence_message_x(
            layout,
            message["from"],
            row["y"],
            row["to_x"],
        )
        to_x = _sequence_message_x(
            layout,
            message["to"],
            row["y"],
            row["from_x"],
        )
        parts.append(
            f'<line data-sequence-message="{index}" '
            f'x1="{from_x:.1f}" y1="{row["y"]:.1f}" '
            f'x2="{to_x:.1f}" y2="{row["y"]:.1f}" '
            f'stroke="{edge}" stroke-width="2"{dashed} '
            f'marker-end="url(#{marker})"/>'
        )
        mid_x = (from_x + to_x) / 2
        _svg_text(
            parts,
            row["label"],
            mid_x,
            row["y"] - 12,
            _SEQUENCE_MESSAGE_FONT_SIZE,
            family,
        )

    parts.append("</svg>")
    out.write_text("\n".join(parts) + "\n", encoding="utf-8")


def _drawio_sequence_edge(
    root,
    cell_id,
    value,
    style,
    x1,
    y1,
    x2,
    y2,
    waypoints=None,
):
    cell = ET.SubElement(
        root,
        "mxCell",
        id=cell_id,
        value=value,
        style=style,
        edge="1",
        parent="1",
    )
    geometry = ET.SubElement(
        cell,
        "mxGeometry",
        relative="1",
        **{"as": "geometry"},
    )
    ET.SubElement(
        geometry,
        "mxPoint",
        x=f"{x1:.1f}",
        y=f"{y1:.1f}",
        **{"as": "sourcePoint"},
    )
    ET.SubElement(
        geometry,
        "mxPoint",
        x=f"{x2:.1f}",
        y=f"{y2:.1f}",
        **{"as": "targetPoint"},
    )
    if waypoints:
        points = ET.SubElement(geometry, "Array", **{"as": "points"})
        for x, y in waypoints:
            ET.SubElement(points, "mxPoint", x=f"{x:.1f}", y=f"{y:.1f}")


def render_sequence_drawio(data, theme, out: Path):
    d = data["diagram"]
    layout = _sequence_layout(data)
    edge_color = theme["canvas"]["edge"]

    mxfile = ET.Element("mxfile", host="app.diagrams.net", compressed="false")
    diagram = ET.SubElement(mxfile, "diagram", id=d["id"], name=d["title"])
    model = ET.SubElement(
        diagram,
        "mxGraphModel",
        dx="1200",
        dy="800",
        grid="1",
        gridSize="10",
        guides="1",
        tooltips="1",
        connect="1",
        arrows="1",
        fold="1",
        page="1",
        pageScale="1",
        pageWidth=str(d["width"]),
        pageHeight=str(d["height"]),
        math="0",
        shadow="0",
    )
    root = ET.SubElement(model, "root")
    ET.SubElement(root, "mxCell", id="0")
    ET.SubElement(root, "mxCell", id="1", parent="0")

    header_by_id = {}
    for header in layout["headers"]:
        participant = header["participant"]
        style = _style(theme, participant["kind"])
        cell_id = f"sequence-participant-{participant['id']}"
        header_by_id[participant["id"]] = header
        cell = ET.SubElement(
            root,
            "mxCell",
            id=cell_id,
            value=html.escape(participant["label"]).replace("\n", "<br>"),
            style=(
                "shape=umlLifeline;perimeter=lifelinePerimeter;"
                "whiteSpace=wrap;html=1;container=1;collapsible=0;"
                "recursiveResize=0;outlineConnect=0;portConstraint=eastwest;"
                f"size={layout['header_height']:.0f};"
                f"fillColor={style['fill']};strokeColor={style['stroke']};"
                "fontFamily=Helvetica;fontSize=14;"
            ),
            vertex="1",
            parent="1",
        )
        ET.SubElement(
            cell,
            "mxGeometry",
            x=f"{header['x']:.1f}",
            y=f"{header['y']:.1f}",
            width=f"{header['w']:.1f}",
            height=f"{layout['lifeline_bottom'] - header['y']:.1f}",
            **{"as": "geometry"},
        )

    for activation in layout["activations"]:
        participant_id = activation["participant"]
        header = header_by_id[participant_id]
        participant = header["participant"]
        style = _style(theme, participant["kind"])
        x = header["w"] / 2 - 6.0 + activation["depth"] * 4.0
        y = activation["start_y"] - header["y"]
        height = activation["end_y"] - activation["start_y"]
        cell = ET.SubElement(
            root,
            "mxCell",
            id=f"sequence-activation-{activation['id']}",
            value="",
            style=(
                "points=[];html=1;whiteSpace=wrap;"
                f"fillColor={style['fill']};strokeColor={style['stroke']};"
            ),
            vertex="1",
            parent=f"sequence-participant-{participant_id}",
        )
        ET.SubElement(
            cell,
            "mxGeometry",
            x=f"{x:.1f}",
            y=f"{y:.1f}",
            width="12.0",
            height=f"{height:.1f}",
            **{"as": "geometry"},
        )

    for index, row in enumerate(layout["messages"], 1):
        message = row["message"]
        kind = message.get("kind", "call")
        if kind == "call":
            arrow = "endArrow=block;endFill=1;"
            dashed = ""
        elif kind == "async":
            arrow = "endArrow=open;endFill=0;"
            dashed = ""
        else:
            arrow = "endArrow=open;endFill=0;"
            dashed = "dashed=1;"

        is_self = message["from"] == message["to"]
        if is_self:
            x1 = _sequence_message_x(
                layout,
                message["from"],
                row["y"],
                row["from_x"] + 1.0,
            )
            loop_x = x1 + 42.0
            y2 = row["y"] + layout["self_message_height"]
            x2 = _sequence_message_x(
                layout,
                message["to"],
                y2,
                row["to_x"] + 1.0,
            )
            _drawio_sequence_edge(
                root,
                f"sequence-message-{index}",
                html.escape(row["label"]).replace("\n", "<br>"),
                (
                    "edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;"
                    "whiteSpace=wrap;fontSize=13;"
                    f"strokeColor={edge_color};{arrow}{dashed}"
                ),
                x1,
                row["y"],
                x2,
                y2,
                waypoints=[(loop_x, row["y"]), (loop_x, y2)],
            )
            continue

        from_x = _sequence_message_x(
            layout,
            message["from"],
            row["y"],
            row["to_x"],
        )
        to_x = _sequence_message_x(
            layout,
            message["to"],
            row["y"],
            row["from_x"],
        )
        _drawio_sequence_edge(
            root,
            f"sequence-message-{index}",
            html.escape(row["label"]).replace("\n", "<br>"),
            (
                "edgeStyle=none;rounded=0;html=1;"
                "whiteSpace=wrap;fontSize=13;"
                f"strokeColor={edge_color};{arrow}{dashed}"
            ),
            from_x,
            row["y"],
            to_x,
            row["y"],
        )

    ET.indent(mxfile, space="  ")
    out.write_text(ET.tostring(mxfile, encoding="unicode") + "\n", encoding="utf-8")

def generate(source_dir: Path, schema_path: Path, theme_path: Path, out_dir: Path):
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    theme = load_yaml(theme_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    generated = []

    for path in sorted(source_dir.glob("*.yaml")):
        data = load_yaml(path)
        validate_source(data, schema, path)
        diagram_type = data["diagram"].get("type", "structure")
        diagram_id = data["diagram"]["id"]

        if diagram_type == "sequence":
            validate_sequence_refs(data, theme, path)
            render_sequence_svg(data, theme, out_dir / f"{diagram_id}.svg")
            render_sequence_drawio(data, theme, out_dir / f"{diagram_id}.drawio")
        else:
            validate_refs(data, theme, path)
            render_svg(data, theme, out_dir / f"{diagram_id}.svg")
            render_drawio(data, theme, out_dir / f"{diagram_id}.drawio")

        generated.append(data["diagram"])

    return generated
