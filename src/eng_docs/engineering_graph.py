"""Normalize a Sphinx-Needs export into the reusable engineering graph."""

from __future__ import annotations

from importlib.resources import files
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import yaml


def _need_source(need: dict) -> str:
    docname = need.get("docname")
    doctype = need.get("doctype", "")
    lineno = need.get("lineno")

    if isinstance(docname, str) and docname:
        suffix = doctype if isinstance(doctype, str) else ""
        path = f"{docname}{suffix}"
    else:
        path = "unknown"

    if isinstance(lineno, int) and lineno > 0:
        return f"{path}:{lineno}"
    return path


def _load_needs(path: Path) -> tuple[dict, dict[str, dict]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path}: invalid Sphinx-Needs JSON: {exc}") from exc

    current = data.get("current_version")
    versions = data.get("versions")
    if not isinstance(current, str) or not current:
        raise ValueError(f"{path}: missing current_version")
    if not isinstance(versions, dict) or current not in versions:
        raise ValueError(f"{path}: current_version {current!r} is not present in versions")

    version_data = versions[current]
    if not isinstance(version_data, dict):
        raise ValueError(f"{path}: version {current!r} must be an object")

    needs = version_data.get("needs")
    if not isinstance(needs, dict):
        raise ValueError(f"{path}: version {current!r} has no needs object")

    normalized: dict[str, dict] = {}
    for object_id, need in needs.items():
        if not isinstance(object_id, str) or not object_id:
            raise ValueError(f"{path}: Need IDs must be non-empty strings")
        if not isinstance(need, dict):
            raise ValueError(f"{path}: Need {object_id!r} must be an object")
        if need.get("id") not in (None, object_id):
            raise ValueError(
                f"{path}: Need key {object_id!r} does not match embedded id {need.get('id')!r}"
            )
        object_type = need.get("type")
        if not isinstance(object_type, str) or not object_type:
            raise ValueError(f"{path}: Need {object_id!r} has no type")
        normalized[object_id] = need

    source_graph = {
        "kind": "sphinx-needs",
        "project": data.get("project"),
        "version": current,
    }
    return source_graph, normalized


def _relation_rows(
    needs: dict[str, dict],
    relation_types: list[str],
) -> list[dict]:
    rows: list[dict] = []
    for object_id in sorted(needs):
        need = needs[object_id]
        source = _need_source(need)
        for relation_type in relation_types:
            targets = need.get(relation_type, [])
            if targets is None:
                targets = []
            if not isinstance(targets, list) or not all(
                isinstance(target, str) and target for target in targets
            ):
                raise ValueError(
                    f"{source}: Need {object_id} field {relation_type} must be a list of ids"
                )
            for target in targets:
                if target not in needs:
                    raise ValueError(
                        f"{source}: Need {object_id} has unknown {relation_type} target {target}"
                    )
                rows.append(
                    {
                        "from": object_id,
                        "type": relation_type,
                        "to": target,
                        "source": source,
                    }
                )

    rows.sort(key=lambda item: (item["from"], item["type"], item["to"], item["source"]))
    return rows


def _diagram_refs(diagrams_root: Path | None, objects: dict[str, dict]) -> None:
    if diagrams_root is None:
        return
    if not diagrams_root.is_dir():
        raise ValueError(f"diagram source directory does not exist: {diagrams_root}")

    for path in sorted(diagrams_root.rglob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            continue
        nodes = data.get("nodes", [])
        if not isinstance(nodes, list):
            continue

        lines = path.read_text(encoding="utf-8").splitlines()
        search_from = 0
        for node in nodes:
            if not isinstance(node, dict):
                continue
            object_id = node.get("object_id")
            if object_id is None:
                continue
            if not isinstance(object_id, str) or not object_id:
                raise ValueError(f"{path}: diagram object_id must be a non-empty string")
            if object_id not in objects:
                raise ValueError(
                    f"{path}: diagram object_id {object_id} does not resolve to a Need"
                )

            line_number = 1
            needle = f"object_id: {object_id}"
            for index in range(search_from, len(lines)):
                if needle in lines[index]:
                    line_number = index + 1
                    search_from = index + 1
                    break

            ref = {
                "source": f"{path.as_posix()}:{line_number}",
                "diagram_id": data.get("diagram", {}).get("id")
                if isinstance(data.get("diagram"), dict)
                else None,
                "node_id": node.get("id"),
            }
            objects[object_id]["diagram_refs"].append(ref)

    for obj in objects.values():
        obj["diagram_refs"].sort(
            key=lambda item: (
                item["source"],
                item.get("diagram_id") or "",
                item.get("node_id") or "",
            )
        )


def build_graph(
    needs_path: Path,
    *,
    relation_types: list[str] | None = None,
    diagrams_root: Path | None = None,
    source_revision: str | None = None,
) -> dict:
    if not needs_path.is_file():
        raise ValueError(f"Sphinx-Needs export does not exist: {needs_path}")

    relation_types = relation_types or []
    if any(not isinstance(item, str) or not item for item in relation_types):
        raise ValueError("relation types must be non-empty strings")
    if len(set(relation_types)) != len(relation_types):
        raise ValueError("relation types must not be repeated")

    source_graph, needs = _load_needs(needs_path)

    objects: dict[str, dict] = {}
    for object_id in sorted(needs):
        need = needs[object_id]
        objects[object_id] = {
            "id": object_id,
            "type": need["type"],
            "type_name": need.get("type_name"),
            "title": need.get("title"),
            "source": _need_source(need),
            "content": need.get("content"),
            "diagram_refs": [],
        }

    relations = _relation_rows(needs, relation_types)
    _diagram_refs(diagrams_root, objects)

    return {
        "schema": "brainboxemb.engineering-graph",
        "schema_version": 1,
        "source_revision": source_revision,
        "source_graph": source_graph,
        "object_count": len(objects),
        "relation_count": len(relations),
        "objects": [objects[key] for key in sorted(objects)],
        "relations": relations,
    }


def incoming_relations(graph: dict, object_id: str) -> list[dict]:
    return [
        relation
        for relation in graph["relations"]
        if relation["to"] == object_id
    ]


def render_review(graph: dict) -> str:
    objects = {item["id"]: item for item in graph["objects"]}
    outgoing = {key: [] for key in objects}
    incoming = {key: [] for key in objects}
    for relation in graph["relations"]:
        outgoing[relation["from"]].append(relation)
        incoming[relation["to"]].append(relation)

    source_graph = graph.get("source_graph", {})
    lines = [
        "# Engineering graph review",
        "",
        f"Source revision: {graph.get('source_revision') or 'unknown'}",
        (
            "Source graph: "
            f"{source_graph.get('kind', 'unknown')} "
            f"{source_graph.get('project') or ''} "
            f"{source_graph.get('version') or ''}"
        ).rstrip(),
        "",
        "Engineering objects and outgoing relations come from the Sphinx-Needs export.",
        "Incoming relations below are derived from those outgoing relations.",
        "Diagram identities are references to existing engineering objects.",
        "",
        "## Overview",
        "",
        "| Object | Type | Authored outgoing | Generated incoming | Diagram refs |",
        "| --- | --- | ---: | ---: | ---: |",
    ]

    for object_id in sorted(objects):
        anchor = object_id.lower().replace("_", "-")
        obj = objects[object_id]
        lines.append(
            f"| [{object_id}](#{anchor}) | {obj['type']} | "
            f"{len(outgoing[object_id])} | {len(incoming[object_id])} | "
            f"{len(obj.get('diagram_refs', []))} |"
        )

    for object_id in sorted(objects):
        obj = objects[object_id]
        type_text = obj["type"]
        if obj.get("type_name"):
            type_text += f" ({obj['type_name']})"

        lines += [
            "",
            f"## {object_id}",
            "",
            f"Type: {type_text}  ",
            f"Title: {obj.get('title') or ''}  ",
            f"Source: {obj['source']}",
            "",
            "### Authored outgoing",
            "",
        ]

        if outgoing[object_id]:
            for relation in outgoing[object_id]:
                lines.append(f"- {relation['type']} -> **{relation['to']}**")
        else:
            lines.append("_None._")

        lines += ["", "### Generated incoming", ""]
        if incoming[object_id]:
            for relation in sorted(
                incoming[object_id],
                key=lambda item: (item["type"], item["from"]),
            ):
                lines.append(f"- {relation['type']} <- **{relation['from']}**")
        else:
            lines.append("_None._")

        lines += ["", "### Diagram references", ""]
        refs = obj.get("diagram_refs", [])
        if refs:
            for ref in refs:
                detail = []
                if ref.get("diagram_id"):
                    detail.append(f"diagram={ref['diagram_id']}")
                if ref.get("node_id"):
                    detail.append(f"node={ref['node_id']}")
                suffix = f" ({', '.join(detail)})" if detail else ""
                lines.append(f"- {ref['source']}{suffix}")
        else:
            lines.append("_None._")

    return "\n".join(lines) + "\n"


def _validate_graph_schema(graph: dict) -> None:
    schema_path = Path(
        str(files("eng_docs").joinpath("schemas/engineering-graph.schema.json"))
    )
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(graph)


def write_graph(
    needs_path: Path,
    out_path: Path,
    *,
    relation_types: list[str] | None = None,
    diagrams_root: Path | None = None,
    review_path: Path | None = None,
    source_revision: str | None = None,
) -> dict:
    graph = build_graph(
        needs_path,
        relation_types=relation_types,
        diagrams_root=diagrams_root,
        source_revision=source_revision,
    )
    _validate_graph_schema(graph)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(graph, indent=2) + "\n", encoding="utf-8")

    if review_path is not None:
        review_path.parent.mkdir(parents=True, exist_ok=True)
        review_path.write_text(render_review(graph), encoding="utf-8")

    return graph
