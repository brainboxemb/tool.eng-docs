"""Reusable engineering-graph extraction and review generation."""

from __future__ import annotations

from importlib.resources import files
import json
from pathlib import Path
import re

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
import yaml


ENG_RE = re.compile(r"<!-- eng (\{.*\}) -->")
ENG_REL_RE = re.compile(r"<!-- eng-rel (\{.*\}) -->")
ANCHOR_RE = re.compile(r'<a id="([^"]+)"></a>')


def _source_path(root: Path, path: Path, line: int) -> str:
    try:
        relative = path.resolve().relative_to(root.resolve())
        text = relative.as_posix()
    except ValueError:
        text = path.as_posix()
    return f"{text}:{line}"


def _parse_metadata(raw: str, source: str, kind: str) -> dict:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{source}: invalid {kind} JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{source}: {kind} metadata must be a JSON object")
    return value


def _relation_rows(owner: str, metadata: dict, source: str) -> list[dict]:
    relations = metadata.get("relations", {})
    if not isinstance(relations, dict):
        raise ValueError(f"{source}: relations must be an object")

    rows = []
    for relation_type, targets in relations.items():
        if not isinstance(relation_type, str) or not relation_type:
            raise ValueError(f"{source}: relation type must be a non-empty string")
        if not isinstance(targets, list) or not all(isinstance(item, str) and item for item in targets):
            raise ValueError(f"{source}: relation {relation_type} must be a list of ids")
        for target in targets:
            rows.append(
                {
                    "from": owner,
                    "type": relation_type,
                    "to": target,
                    "source": source,
                }
            )
    return rows


def _add_authoring(obj: dict, source: str, raw: str) -> None:
    obj.setdefault("authoring", []).append({"source": source, "input": raw})


def _load_model(path: Path | None) -> dict | None:
    if path is None:
        return None
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    schema_path = Path(str(files("eng_docs").joinpath("schemas/engineering-graph-model.schema.json")))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    try:
        Draft202012Validator(schema).validate(data)
    except ValidationError as exc:
        raise ValueError(f"invalid engineering graph model: {exc.message}") from exc

    if data.get("diagram_object_type") and data["diagram_object_type"] not in data["object_types"]:
        raise ValueError("diagram_object_type must be declared in object_types")
    return data


def _validate_model(objects: dict[str, dict], relations: list[dict], model: dict | None) -> None:
    if model is None:
        return

    allowed_types = set(model["object_types"])
    relation_specs = model["relations"]

    for obj in objects.values():
        if obj["type"] not in allowed_types:
            raise ValueError(f'{obj["source"]}: unknown object type {obj["type"]}')

    for relation in relations:
        relation_type = relation["type"]
        if relation_type not in relation_specs:
            raise ValueError(f'{relation["source"]}: unknown relation type {relation_type}')
        spec = relation_specs[relation_type]
        source_type = objects[relation["from"]]["type"]
        target_type = objects[relation["to"]]["type"]
        if source_type not in spec["from"]:
            raise ValueError(
                f'{relation["source"]}: relation {relation_type} does not allow source type {source_type}'
            )
        if target_type not in spec["to"]:
            raise ValueError(
                f'{relation["source"]}: relation {relation_type} does not allow target type {target_type}'
            )


def build_graph(
    root: Path,
    docs_root: Path,
    *,
    diagrams_root: Path | None = None,
    model_path: Path | None = None,
    source_revision: str | None = None,
) -> dict:
    root = root.resolve()
    docs_root = docs_root if docs_root.is_absolute() else root / docs_root
    diagrams_root = (
        diagrams_root
        if diagrams_root is None or diagrams_root.is_absolute()
        else root / diagrams_root
    )
    model_path = model_path if model_path is None or model_path.is_absolute() else root / model_path

    if not docs_root.is_dir():
        raise ValueError(f"Markdown source directory does not exist: {docs_root}")
    if diagrams_root is not None and not diagrams_root.is_dir():
        raise ValueError(f"diagram source directory does not exist: {diagrams_root}")
    if model_path is not None and not model_path.is_file():
        raise ValueError(f"engineering graph model does not exist: {model_path}")

    model = _load_model(model_path)
    diagram_object_type = model.get("diagram_object_type", "diagram-node") if model else "diagram-node"

    objects: dict[str, dict] = {}
    relations: list[dict] = []
    extensions: list[tuple[str, dict, str, str]] = []

    for path in sorted(docs_root.rglob("*.md")):
        lines = path.read_text(encoding="utf-8").splitlines()
        current_anchor = None
        for line_number, line in enumerate(lines, 1):
            stripped = line.strip()

            anchor_match = ANCHOR_RE.fullmatch(stripped)
            if anchor_match:
                current_anchor = anchor_match.group(1)

            object_match = ENG_RE.fullmatch(stripped)
            if object_match:
                source = _source_path(root, path, line_number)
                if not current_anchor:
                    raise ValueError(f"{source}: eng metadata requires a preceding stable anchor")
                metadata = _parse_metadata(object_match.group(1), source, "eng")
                object_type = metadata.get("type")
                if not isinstance(object_type, str) or not object_type:
                    raise ValueError(f"{source}: eng metadata requires a non-empty type")
                if current_anchor in objects:
                    raise ValueError(f"{source}: duplicate engineering id {current_anchor}")
                objects[current_anchor] = {
                    "id": current_anchor,
                    "type": object_type,
                    "source": source,
                    "authoring": [],
                }
                _add_authoring(objects[current_anchor], source, stripped)
                relations.extend(_relation_rows(current_anchor, metadata, source))
                continue

            extension_match = ENG_REL_RE.fullmatch(stripped)
            if extension_match:
                source = _source_path(root, path, line_number)
                metadata = _parse_metadata(extension_match.group(1), source, "eng-rel")
                owner = metadata.get("id")
                if not isinstance(owner, str) or not owner:
                    raise ValueError(f"{source}: eng-rel requires a non-empty id")
                extensions.append((owner, metadata, source, stripped))

    if diagrams_root is not None:
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
                if not object_id:
                    continue
                if not isinstance(object_id, str):
                    raise ValueError(f"{path}: diagram object_id must be a string")
                if object_id in objects:
                    raise ValueError(f"{path}: duplicate engineering id {object_id}")

                line_number = 1
                needle = f"object_id: {object_id}"
                for index in range(search_from, len(lines)):
                    if needle in lines[index]:
                        line_number = index + 1
                        search_from = index + 1
                        break
                source = _source_path(root, path, line_number)
                objects[object_id] = {
                    "id": object_id,
                    "type": diagram_object_type,
                    "source": source,
                    "authoring": [],
                }
                _add_authoring(objects[object_id], source, f"object_id: {object_id}")

    for owner, metadata, source, raw in extensions:
        if owner not in objects:
            raise ValueError(f"{source}: eng-rel owner does not exist: {owner}")
        _add_authoring(objects[owner], source, raw)
        relations.extend(_relation_rows(owner, metadata, source))

    for relation in relations:
        if relation["to"] not in objects:
            raise ValueError(
                f'{relation["source"]}: unknown {relation["type"]} target {relation["to"]}'
            )

    relations.sort(key=lambda item: (item["from"], item["type"], item["to"], item["source"]))
    _validate_model(objects, relations, model)

    return {
        "schema": "brainboxemb.engineering-graph",
        "schema_version": 1,
        "source_revision": source_revision,
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

    lines = [
        "# Engineering graph review",
        "",
        f"Source revision: {graph.get('source_revision') or 'unknown'}",
        "",
        "This view separates authored source from generated inverse context.",
        "",
        "- **Authored input** is the exact hidden Markdown/YAML identity or relation input.",
        "- **Authored outgoing** is normalized from that source.",
        "- **Generated incoming** is derived from other objects and is not authored again.",
        "",
        "## Overview",
        "",
        "| Object | Type | Authored outgoing | Generated incoming |",
        "| --- | --- | ---: | ---: |",
    ]

    for object_id in sorted(objects):
        anchor = object_id.lower().replace("_", "-")
        lines.append(
            f"| [{object_id}](#{anchor}) | {objects[object_id]['type']} | "
            f"{len(outgoing[object_id])} | {len(incoming[object_id])} |"
        )

    for object_id in sorted(objects):
        obj = objects[object_id]
        lines += [
            "",
            f"## {object_id}",
            "",
            f"Type: {obj['type']}  ",
            f"Primary source: {obj['source']}",
            "",
            "### Authored input",
            "",
        ]
        for authored in obj.get("authoring", []):
            lines += [
                f"Source: {authored['source']}",
                "",
                "~~~text",
                authored["input"],
                "~~~",
                "",
            ]

        lines += ["### Authored outgoing", ""]
        if outgoing[object_id]:
            for relation in outgoing[object_id]:
                lines.append(f"- {relation['type']} -> **{relation['to']}**")
        else:
            lines.append("_None._")

        lines += ["", "### Generated incoming", ""]
        if incoming[object_id]:
            for relation in sorted(incoming[object_id], key=lambda item: (item["type"], item["from"])):
                lines.append(f"- {relation['type']} <- **{relation['from']}**")
        else:
            lines.append("_None._")

    return "\n".join(lines) + "\n"


def _validate_graph_schema(graph: dict) -> None:
    schema_path = Path(str(files("eng_docs").joinpath("schemas/engineering-graph.schema.json")))
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(graph)


def write_graph(
    root: Path,
    docs_root: Path,
    out_path: Path,
    *,
    diagrams_root: Path | None = None,
    model_path: Path | None = None,
    review_path: Path | None = None,
    source_revision: str | None = None,
) -> dict:
    graph = build_graph(
        root,
        docs_root,
        diagrams_root=diagrams_root,
        model_path=model_path,
        source_revision=source_revision,
    )
    _validate_graph_schema(graph)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(graph, indent=2) + "\n", encoding="utf-8")
    if review_path is not None:
        review_path.parent.mkdir(parents=True, exist_ok=True)
        review_path.write_text(render_review(graph), encoding="utf-8")
    return graph
