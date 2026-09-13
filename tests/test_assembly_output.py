from pathlib import Path

import pytest
import yaml

from eng_docs.assembly_output import assemble_output
from eng_docs.manifests import build_manifest


SOURCE_REPOSITORY = "brainboxemb/example-project"
SOURCE_REVISION = "fedcba9876543210"


def _config(root: Path, *, source: str = "docs/overview.md") -> Path:
    config = {
        "schema_version": 1,
        "asset_manifests": [
            {
                "path": "bld/docs/architecture/assets.yml",
                "publish_prefix": "assets/architecture",
            }
        ],
        "documents": [
            {
                "id": "overview",
                "source": source,
                "output": "documents/overview.md",
            }
        ],
    }
    path = root / "assembly.yml"
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    return path


def _producer_output(root: Path) -> None:
    architecture = root / "bld" / "docs" / "architecture"
    architecture.mkdir(parents=True)
    (architecture / "system.svg").write_text("<svg>existing producer output</svg>\n", encoding="utf-8")
    build_manifest(
        architecture,
        architecture / "assets.yml",
        producer="example.architecture",
        producer_version="1.0.0",
        source_revision="0123456789abcdef",
        lifecycle="docs",
        relationship="producer-source",
        include=["*.svg"],
    )


def test_assembly_can_consume_assets_below_final_output_root(tmp_path):
    root = tmp_path / "project"
    docs = root / "docs"
    docs.mkdir(parents=True)
    (docs / "overview.md").write_text(
        "# Overview\n\n![System](../../../raw/prod/docs/assets/architecture/system.svg)\n",
        encoding="utf-8",
    )
    _producer_output(root)
    config = _config(root)
    out = root / "bld" / "docs"

    result = assemble_output(
        root,
        config,
        out,
        source_repository=SOURCE_REPOSITORY,
        source_revision=SOURCE_REVISION,
    )

    assert result["assets"] == 1
    assert (out / "assets" / "architecture" / "system.svg").read_text(encoding="utf-8") == "<svg>existing producer output</svg>\n"
    generated = (out / "documents" / "overview.md").read_text(encoding="utf-8")
    assert "../assets/architecture/system.svg" in generated
    assert not (out / "architecture").exists()

    info = yaml.safe_load((out / "assembly-info.yml").read_text(encoding="utf-8"))
    assert info["assembler"]["name"] == "tool.eng-docs"
    assert info["source"] == {
        "repository": SOURCE_REPOSITORY,
        "revision": SOURCE_REVISION,
    }
    assert info["configuration"]["path"] == "assembly.yml"
    assert len(info["configuration"]["sha256"]) == 64
    assert info["input_manifests"][0]["path"] == "bld/docs/architecture/assets.yml"
    assert info["input_manifests"][0]["producer"]["name"] == "example.architecture"


def test_failed_assembly_preserves_existing_output(tmp_path):
    root = tmp_path / "project"
    docs = root / "docs"
    docs.mkdir(parents=True)
    _producer_output(root)
    out = root / "bld" / "docs"
    sentinel = out / "keep-me.txt"
    sentinel.write_text("old output survives\n", encoding="utf-8")
    config = _config(root, source="docs/missing.md")

    with pytest.raises(ValueError, match="document source does not exist"):
        assemble_output(
            root,
            config,
            out,
            source_repository=SOURCE_REPOSITORY,
            source_revision=SOURCE_REVISION,
        )

    assert sentinel.read_text(encoding="utf-8") == "old output survives\n"
    assert (out / "architecture" / "system.svg").is_file()
