"""Safe publication of assembled document trees.

The low-level assembly builder writes a complete tree into the supplied output
root. This wrapper keeps existing producer output available while that tree is
built, then replaces the final root only after assembly succeeds.
"""

from __future__ import annotations

from pathlib import Path
import shutil
import tempfile

from .assembly import assemble as assemble_tree


def assemble_output(project_root: Path, config_path: Path, out_root: Path) -> dict:
    """Assemble through a sibling staging directory and replace output on success."""

    out_root = out_root.resolve()
    out_root.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{out_root.name}.assemble-", dir=out_root.parent))
    backup = out_root.parent / f".{out_root.name}.previous"

    try:
        # assemble_tree owns/cleans staging only. Existing producer output below
        # out_root remains readable while manifests/assets are consumed.
        result = assemble_tree(project_root, config_path, staging)

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
