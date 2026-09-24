"""Declarative engineering-diagram validation and rendering."""

from __future__ import annotations

from pathlib import Path
import html
import json
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
    overlap = set(group_ids) & set(node_ids)
    if overlap:
        raise ValueError(f"{path}: ids reused by group and node: {sorted(overlap)}")

    known_groups = set(group_ids)
    known_nodes = set(node_ids)
    kinds = theme.get("kinds", {})
    for item in [*data["groups"], *data["nodes"]]:
        if item["kind"] not in kinds:
            raise ValueError(f"{path}: unknown kind {item['kind']!r} on {item['id']}")
    for node in data["nodes"]:
        if node.get("group") and node["group"] not in known_groups:
            raise ValueError(f"{path}: node {node['id']} references missing group {node['group']}")
    for edge in data["edges"]:
        if edge["from"] not in known_nodes or edge["to"] not in known_nodes:
            raise ValueError(f"{path}: edge references missing node: {edge['from']} -> {edge['to']}")


def _style(theme, kind):
    return theme["kinds"][kind]


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


def _svg_node_text(parts, node, theme, family):
    r = node["layout"]
    label = str(node["label"])
    subtitle = node.get("subtitle")
    x = r["x"] + r["w"] / 2
    center_y = r["y"] + r["h"] / 2
    node_size = theme["font"]["node_size"]

    if not subtitle:
        _svg_text(parts, label, x, center_y, node_size, family)
        return

    subtitle_size = theme["font"].get("node_subtitle_size", max(9, node_size - 3))
    label_lines = label.splitlines() or [""]
    subtitle_lines = str(subtitle).splitlines() or [""]
    label_height = len(label_lines) * node_size * 1.28
    subtitle_height = len(subtitle_lines) * subtitle_size * 1.28
    gap = 5
    total_height = label_height + gap + subtitle_height
    top = center_y - total_height / 2

    label_center = top + label_height / 2
    subtitle_center = top + label_height + gap + subtitle_height / 2
    _svg_text(parts, label, x, label_center, node_size, family)
    _svg_text(parts, subtitle, x, subtitle_center, subtitle_size, family)


def _drawio_node_value(node, theme):
    label = html.escape(str(node["label"])).replace("\n", "<br>")
    subtitle = node.get("subtitle")
    if not subtitle:
        return label
    subtitle_size = theme["font"].get(
        "node_subtitle_size",
        max(9, theme["font"]["node_size"] - 3),
    )
    subtitle_html = html.escape(str(subtitle)).replace("\n", "<br>")
    return (
        f'{label}<br><span style="font-size:{subtitle_size}px">'
        f'{subtitle_html}</span>'
    )


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
        parts.append(
            f'<rect x="{r["x"]}" y="{r["y"]}" width="{r["w"]}" height="{r["h"]}" '
            f'rx="10" ry="10" fill="{s["fill"]}" stroke="{s["stroke"]}" stroke-width="2"/>'
        )
        _svg_text(parts, group["label"], r["x"] + 16, r["y"] + 22, theme["font"]["group_title_size"], family, "bold", "start")

    nodes = {n["id"]: n for n in data["nodes"]}
    for edge in data["edges"]:
        source = nodes[edge["from"]]
        target = nodes[edge["to"]]
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
        parts.append(
            f'<rect x="{r["x"]}" y="{r["y"]}" width="{r["w"]}" height="{r["h"]}" '
            f'rx="8" ry="8" fill="{s["fill"]}" stroke="{s["stroke"]}" stroke-width="2"/>'
        )
        _svg_node_text(parts, node, theme, family)

    parts.append("</svg>")
    out.write_text("\n".join(parts) + "\n", encoding="utf-8")


def _drawio_node_style(theme, kind, group=False):
    s = _style(theme, kind)
    result = (
        "rounded=1;whiteSpace=wrap;html=1;"
        f"fillColor={s['fill']};strokeColor={s['stroke']};fontFamily=Helvetica;"
    )
    if group:
        result += "verticalAlign=top;align=left;spacingTop=8;spacingLeft=10;fontStyle=1;fontSize=17;"
    else:
        result += "fontSize=14;"
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
        cell = ET.SubElement(
            root, "mxCell", id=f"group-{group['id']}", value=group["label"],
            style=_drawio_node_style(theme, group["kind"], True), vertex="1", parent="1"
        )
        ET.SubElement(cell, "mxGeometry", x=str(r["x"]), y=str(r["y"]), width=str(r["w"]), height=str(r["h"]), **{"as": "geometry"})

    for node in data["nodes"]:
        r = node["layout"]
        cell = ET.SubElement(
            root, "mxCell", id=node["id"], value=_drawio_node_value(node, theme),
            style=_drawio_node_style(theme, node["kind"]), vertex="1", parent="1"
        )
        ET.SubElement(cell, "mxGeometry", x=str(r["x"]), y=str(r["y"]), width=str(r["w"]), height=str(r["h"]), **{"as": "geometry"})

    for i, edge in enumerate(data["edges"], 1):
        edge_style = "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;html=1;endArrow=block;endFill=1;"
        edge_style += _drawio_anchor_style(edge.get("from_anchor"), "exit")
        edge_style += _drawio_anchor_style(edge.get("to_anchor"), "entry")
        if edge.get("dashed"):
            edge_style += "dashed=1;"
        cell = ET.SubElement(
            root, "mxCell", id=f"edge-{i}", value=edge.get("label", ""), style=edge_style,
            edge="1", parent="1", source=edge["from"], target=edge["to"]
        )
        geom = ET.SubElement(cell, "mxGeometry", relative="1", **{"as": "geometry"})
        if edge.get("route"):
            points = ET.SubElement(geom, "Array", **{"as": "points"})
            for point in edge["route"]:
                ET.SubElement(points, "mxPoint", x=str(point["x"]), y=str(point["y"]))

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
        validate_refs(data, theme, path)
        diagram_id = data["diagram"]["id"]
        render_svg(data, theme, out_dir / f"{diagram_id}.svg")
        render_drawio(data, theme, out_dir / f"{diagram_id}.drawio")
        generated.append(data["diagram"])

    return generated
