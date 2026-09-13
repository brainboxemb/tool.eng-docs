"""Domain-neutral assembly of Markdown and already-produced assets."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path, PurePosixPath
from urllib.parse import unquote, urlsplit
import json
import os
import shutil

import yaml
from jsonschema import Draft202012Validator

from .manifests import load_manifest


@dataclass(frozen=True)
class Asset:
    id: str
    source: Path
    published_path: Path
    manifest: Path
    producer: dict
    metadata: dict


@dataclass(frozen=True)
class BuiltDocument:
    id: str
    source: Path
    output: Path
    title: str
    body: str


def _load_schema(name: str):
    path = Path(str(files("eng_docs").joinpath("schemas", name)))
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_config(data, path: Path) -> None:
    errors = sorted(
        Draft202012Validator(_load_schema("assembly.schema.json")).iter_errors(data),
        key=lambda error: list(error.path),
    )
    if not errors:
        return
    lines = [f"{path}: invalid assembly configuration"]
    for error in errors:
        location = ".".join(str(value) for value in error.path) or "<root>"
        lines.append(f"  {location}: {error.message}")
    raise ValueError("\n".join(lines))


def _relative_path(value: str, field: str) -> Path:
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{field} must be a relative path without '..': {value}")
    if not path.parts:
        return Path()
    return Path(*path.parts)


def _title_of(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def _safe_output(out_root: Path, relative: Path) -> Path:
    target = (out_root / relative).resolve()
    root = out_root.resolve()
    if target != root and root not in target.parents:
        raise ValueError(f"output escapes assembly root: {relative}")
    return target


def _asset_lookup(assets: list[Asset], target: str) -> Asset | None:
    parsed = urlsplit(target)
    path = unquote(parsed.path).replace("\\", "/").rstrip("/")
    if not path:
        return None

    matches: list[tuple[int, Asset]] = []
    for asset in assets:
        published = asset.published_path.as_posix().lstrip("/")
        if path == published or path.endswith("/" + published):
            specificity = len(PurePosixPath(published).parts)
            matches.append((specificity, asset))

    if not matches:
        return None

    best_specificity = max(specificity for specificity, _ in matches)
    best = [asset for specificity, asset in matches if specificity == best_specificity]
    if len(best) > 1:
        ids = ", ".join(asset.id for asset in best)
        raise ValueError(f"asset link is ambiguous for {target!r}: {ids}")
    return best[0]


def _rewrite_target(target: str, *, document_output: Path, out_root: Path, assets: list[Asset]) -> str:
    asset = _asset_lookup(assets, target)
    if asset is None:
        return target
    local = _safe_output(out_root, asset.published_path)
    relative = os.path.relpath(local, start=document_output.parent).replace(os.sep, "/")
    parsed = urlsplit(target)
    if parsed.query:
        relative += "?" + parsed.query
    if parsed.fragment:
        relative += "#" + parsed.fragment
    return relative


def _find_unescaped(text: str, char: str, start: int) -> int:
    index = start
    while index < len(text):
        if text[index] == "\\":
            index += 2
            continue
        if text[index] == char:
            return index
        index += 1
    return -1


def _destination_span(line: str, open_paren: int) -> tuple[int, int] | None:
    index = open_paren + 1
    while index < len(line) and line[index] in " \t":
        index += 1
    if index >= len(line):
        return None
    if line[index] == "<":
        end = _find_unescaped(line, ">", index + 1)
        if end < 0:
            return None
        return index + 1, end

    start = index
    depth = 0
    while index < len(line):
        char = line[index]
        if char == "\\":
            index += 2
            continue
        if char == "(":
            depth += 1
        elif char == ")":
            if depth == 0:
                return start, index
            depth -= 1
        elif char in " \t" and depth == 0:
            return start, index
        index += 1
    return None


def _rewrite_markdown_line(line: str, rewrite) -> str:
    replacements: list[tuple[int, int, str]] = []
    index = 0
    while index < len(line):
        if line[index] == "`":
            count = 1
            while index + count < len(line) and line[index + count] == "`":
                count += 1
            marker = "`" * count
            end = line.find(marker, index + count)
            index = len(line) if end < 0 else end + count
            continue

        label_start = -1
        if line.startswith("![", index):
            label_start = index + 1
        elif line[index] == "[":
            label_start = index
        if label_start < 0:
            index += 1
            continue

        close = _find_unescaped(line, "]", label_start + 1)
        if close < 0:
            break
        cursor = close + 1
        while cursor < len(line) and line[cursor] in " \t":
            cursor += 1
        if cursor >= len(line) or line[cursor] != "(":
            index = close + 1
            continue
        span = _destination_span(line, cursor)
        if span is None:
            index = cursor + 1
            continue
        start, end = span
        original = line[start:end]
        replacement = rewrite(original)
        if replacement != original:
            replacements.append((start, end, replacement))
        index = end + 1

    result = line
    for start, end, replacement in reversed(replacements):
        result = result[:start] + replacement + result[end:]
    return result


def rewrite_markdown(text: str, *, document_output: Path, out_root: Path, assets: list[Asset]) -> str:
    """Rewrite ordinary inline Markdown links while leaving fenced code untouched."""

    result: list[str] = []
    fence: str | None = None
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip()
        marker = None
        if stripped.startswith("```"):
            marker = "```"
        elif stripped.startswith("~~~"):
            marker = "~~~"
        if marker:
            if fence is None:
                fence = marker
            elif fence == marker:
                fence = None
            result.append(line)
            continue
        if fence is not None:
            result.append(line)
            continue
        result.append(
            _rewrite_markdown_line(
                line,
                lambda target: _rewrite_target(
                    target,
                    document_output=document_output,
                    out_root=out_root,
                    assets=assets,
                ),
            )
        )
    return "".join(result)


def _load_assets(project_root: Path, out_root: Path, entries: list[dict]) -> list[Asset]:
    assets: list[Asset] = []
    ids: set[str] = set()
    published_paths: set[Path] = set()
    manifest_output = out_root / "_manifests"

    for number, entry in enumerate(entries, 1):
        manifest_rel = _relative_path(entry["path"], "asset manifest path")
        manifest_path = (project_root / manifest_rel).resolve()
        if not manifest_path.is_file():
            raise ValueError(f"asset manifest does not exist: {manifest_path}")
        data = load_manifest(manifest_path)
        prefix = _relative_path(entry["publish_prefix"], "publish_prefix")
        manifest_output.mkdir(parents=True, exist_ok=True)
        shutil.copy2(manifest_path, manifest_output / f"{number:02d}-{manifest_path.name}")

        for item in data["assets"]:
            asset_path = _relative_path(item["path"], f"asset path for {item['id']}")
            source = (manifest_path.parent / asset_path).resolve()
            if not source.is_file():
                raise ValueError(f"manifest asset does not exist: {source}")
            published = prefix / asset_path
            if item["id"] in ids:
                raise ValueError(f"duplicate asset id: {item['id']}")
            if published in published_paths:
                raise ValueError(f"duplicate published asset path: {published.as_posix()}")
            ids.add(item["id"])
            published_paths.add(published)
            asset = Asset(
                id=item["id"],
                source=source,
                published_path=published,
                manifest=manifest_path,
                producer=data["producer"],
                metadata=item,
            )
            assets.append(asset)
            target = _safe_output(out_root, published)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    return assets


def _as_book_section(document: BuiltDocument, book_output: Path) -> str:
    lines = document.body.splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    shifted = []
    fenced = False
    marker = None
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            current = "```" if stripped.startswith("```") else "~~~"
            if not fenced:
                fenced = True
                marker = current
            elif marker == current:
                fenced = False
                marker = None
            shifted.append(line)
            continue
        if not fenced and line.startswith("#"):
            line = "#" + line
        shifted.append(line)
    source_ref = os.path.relpath(document.output, start=book_output.parent).replace(os.sep, "/")
    return (
        f"## {document.title}\n\n"
        f"**Source document:** [{document.output.name}]({source_ref})\n\n"
        + "\n".join(shifted).strip()
        + "\n"
    )


def assemble(project_root: Path, config_path: Path, out_root: Path) -> dict:
    """Assemble self-contained Markdown review/publication output."""

    project_root = project_root.resolve()
    config_path = config_path.resolve()
    out_root = out_root.resolve()
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    _validate_config(data, config_path)

    if out_root.exists():
        shutil.rmtree(out_root)
    out_root.mkdir(parents=True, exist_ok=True)

    assets = _load_assets(project_root, out_root, data.get("asset_manifests", []))
    documents: dict[str, BuiltDocument] = {}
    document_outputs: set[Path] = set()

    for spec in data["documents"]:
        if spec["id"] in documents:
            raise ValueError(f"duplicate document id: {spec['id']}")
        source_rel = _relative_path(spec["source"], f"document source for {spec['id']}")
        if "output" in spec:
            output_rel = _relative_path(spec["output"], f"document output for {spec['id']}")
        else:
            output_rel = Path("documents") / source_rel.name
        if output_rel in document_outputs:
            raise ValueError(f"duplicate document output path: {output_rel.as_posix()}")
        document_outputs.add(output_rel)
        source = (project_root / source_rel).resolve()
        if not source.is_file():
            raise ValueError(f"document source does not exist: {source}")
        output = _safe_output(out_root, output_rel)
        output.parent.mkdir(parents=True, exist_ok=True)
        source_text = source.read_text(encoding="utf-8")
        body = rewrite_markdown(source_text, document_output=output, out_root=out_root, assets=assets)
        generated = (
            "<!-- Generated review/output copy. Edit the source document, not this copy. -->\n\n"
            + body.rstrip()
            + "\n"
        )
        output.write_text(generated, encoding="utf-8")
        documents[spec["id"]] = BuiltDocument(
            id=spec["id"],
            source=source,
            output=output,
            title=_title_of(body, spec["id"]),
            body=body,
        )

    for index_spec in data.get("indexes", []):
        output_rel = _relative_path(index_spec["output"], "index output")
        output = _safe_output(out_root, output_rel)
        output.parent.mkdir(parents=True, exist_ok=True)
        lines = [f"# {index_spec['title']}", ""]
        if index_spec.get("intro"):
            lines.extend([index_spec["intro"], ""])
        for section in index_spec["sections"]:
            lines.extend([f"## {section['title']}", ""])
            for item in section["items"]:
                if "document" in item:
                    document_id = item["document"]
                    if document_id not in documents:
                        raise ValueError(f"index references unknown document: {document_id}")
                    document = documents[document_id]
                    target = os.path.relpath(document.output, start=output.parent).replace(os.sep, "/")
                    lines.append(f"- [{document.title}]({target})")
                else:
                    lines.append(f"- [{item['label']}]({item['target']})")
            lines.append("")
        output.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    for book_spec in data.get("books", []):
        output_rel = _relative_path(book_spec["output"], "book output")
        output = _safe_output(out_root, output_rel)
        output.parent.mkdir(parents=True, exist_ok=True)
        selected = []
        for document_id in book_spec["documents"]:
            if document_id not in documents:
                raise ValueError(f"book references unknown document: {document_id}")
            selected.append(documents[document_id])
        lines = [f"# {book_spec['title']}", ""]
        if book_spec.get("description"):
            lines.extend([book_spec["description"], ""])
        lines.extend(["## Contents", ""])
        for document in selected:
            target = os.path.relpath(document.output, start=output.parent).replace(os.sep, "/")
            lines.append(f"- [{document.title}]({target})")
        lines.extend(["", "---", ""])
        for document in selected:
            lines.append(_as_book_section(document, output))
            lines.extend(["", "---", ""])
        output.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")

    return {
        "documents": len(documents),
        "assets": len(assets),
        "indexes": len(data.get("indexes", [])),
        "books": len(data.get("books", [])),
    }
