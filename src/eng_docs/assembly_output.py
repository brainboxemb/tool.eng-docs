"""Safe publication of assembled document trees.

The low-level assembly builder writes a complete tree into the supplied output
root. This wrapper keeps existing producer output available while that tree is
built, records generic assembly provenance, then replaces the final root only
after assembly succeeds.
"""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import shutil
import tempfile

import yaml

from . import __version__
from .assembly import assemble as assemble_tree
from .manifests import load_manifest


def _digest(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _display_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _write_assembly_info(
    project_root: Path,
    config_path: Path,
    staging: Path,
    *,
    source_repository: str,
    source_revision: str,
) -> None:
    config_data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    manifests = []
    for entry in config_data.get("asset_manifests", []):
        manifest_path = (project_root / entry["path"]).resolve()
        manifest = load_manifest(manifest_path)
        manifests.append(
            {
                "path": _display_path(manifest_path, project_root),
                "sha256": _digest(manifest_path),
                "producer": manifest["producer"],
            }
        )

    info = {
        "schema_version": 1,
        "assembler": {
            "name": "tool.eng-docs",
            "version": __version__,
        },
        "source": {
            "repository": source_repository,
            "revision": source_revision,
        },
        "configuration": {
            "path": _display_path(config_path, project_root),
            "sha256": _digest(config_path),
        },
        "input_manifests": manifests,
    }
    (staging / "assembly-info.yml").write_text(
        yaml.safe_dump(info, sort_keys=False),
        encoding="utf-8",
    )


def assemble_output(
    project_root: Path,
    config_path: Path,
    out_root: Path,
    *,
    source_repository: str,
    source_revision: str,
) -> dict:
    """Assemble through a sibling staging directory and replace output on success."""

    if not source_repository.strip() or not source_revision.strip():
        raise ValueError("source repository and source revision must be non-empty")

    project_root = project_root.resolve()
    config_path = config_path.resolve()
    out_root = out_root.resolve()
    out_root.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{out_root.name}.assemble-", dir=out_root.parent))
    backup = out_root.parent / f".{out_root.name}.previous"

    try:
        # assemble_tree owns/cleans staging only. Existing producer output below
        # out_root remains readable while manifests/assets are consumed.
        result = assemble_tree(project_root, config_path, staging)
        _write_assembly_info(
            project_root,
            config_path,
            staging,
            source_repository=source_repository,
            source_revision=source_revision,
        )

        if backup.exists():
            shutil.rmtree(backup)
        if out_root.exists():
            out_root.rename(backup)

        try:
            staging.rename(out_root)
        except Exception:
            if backup.exists() and not out_root.exists():
                backup.rename(out_root)
            raise

        if backup.exists():
            shutil.rmtree(backup)
        return result
    finally:
        if staging.exists():
            shutil.rmtree(staging)
