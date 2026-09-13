"""Generic manifests for already-produced documentation assets."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path
import json
import mimetypes

import yaml
from jsonschema import Draft202012Validator

from . import __version__


LIFECYCLES = {"build", "design-doc", "verification", "docs"}
RELATIONSHIPS = {
    "generate-inline",
    "producer-source",
    "reference-existing",
    "reference-evidence",
}


def _load_schema(name: str):
    path = Path(str(files("eng_docs").joinpath("schemas", name)))
    return json.loads(path.read_text(encoding="utf-8"))


def _validate(data, schema_name: str, path: Path) -> None:
    errors = sorted(
        Draft202012Validator(_load_schema(schema_name)).iter_errors(data),
        key=lambda error: list(error.path),
    )
    if not errors:
        return
    lines = [f"{path}: invalid asset manifest"]
    for error in errors:
        location = ".".join(str(value) for value in error.path) or "<root>"
        lines.append(f"  {location}: {error.message}")
    raise ValueError("\n".join(lines))


def _matches(path: Path, patterns: list[str]) -> bool:
    if not patterns:
        return True
    value = path.as_posix()
    return any(path.match(pattern) or Path(value).match(pattern) for pattern in patterns)


def build_manifest(
    source_dir: Path,
    out_path: Path,
    *,
    producer: str,
    source_revision: str,
    lifecycle: str,
    relationship: str,
    producer_version: str | None = None,
    include: list[str] | None = None,
) -> dict:
    """Describe an existing output tree without taking ownership of its build."""

    source_dir = source_dir.resolve()
    out_path = out_path.resolve()
    if not source_dir.is_dir():
        raise ValueError(f"asset source directory does not exist: {source_dir}")
    if lifecycle not in LIFECYCLES:
        raise ValueError(f"unknown asset lifecycle: {lifecycle}")
    if relationship not in RELATIONSHIPS:
        raise ValueError(f"unknown asset relationship: {relationship}")
    if not producer.strip() or not source_revision.strip():
        raise ValueError("producer and source revision must be non-empty")

    patterns = include or []
    assets = []
    for path in sorted(source_dir.rglob("*")):
        if not path.is_file() or path.resolve() == out_path:
            continue
        relative = path.relative_to(source_dir)
        if not _matches(relative, patterns):
            continue
        kind = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        assets.append(
            {
                "id": f"{producer}:{relative.as_posix()}",
                "kind": kind,
                "lifecycle": lifecycle,
                "relationship": relationship,
                "path": relative.as_posix(),
            }
        )

    data = {
        "schema_version": 1,
        "producer": {
            "name": producer,
            "version": producer_version or __version__,
            "source_revision": source_revision,
        },
        "assets": assets,
    }
    _validate(data, "asset-manifest.schema.json", out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return data


def load_manifest(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    _validate(data, "asset-manifest.schema.json", path)
    return data
