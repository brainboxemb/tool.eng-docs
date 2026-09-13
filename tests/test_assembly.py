from pathlib import Path

import yaml

from eng_docs.assembly import assemble
from eng_docs.manifests import build_manifest


def _fixture(tmp_path: Path):
    root = tmp_path / "project"
    docs = root / "docs"
    docs.mkdir(parents=True)
    produced = root / "bld" / "architecture"
    produced.mkdir(parents=True)
    (produced / "system.svg").write_text("<svg>system</svg>\n", encoding="utf-8")
    manifest = produced / "assets.yml"
    build_manifest(
        produced,
        manifest,
        producer="example.diagrams",
        producer_version="1.0.0",
        source_revision="0123456789abcdef",
        lifecycle="docs",
        relationship="producer-source",
        include=["*.svg"],
    )

    source_a = docs / "a.md"
    source_a.write_text(
        "# Architecture\n\n"
        "![System](../../../raw/prod/docs/assets/architecture/system.svg)\n\n"
        "[Download](../../../raw/dev/pr-42/docs/assets/architecture/system.svg)\n\n"
        "[Local document](./b.md)\n\n"
        "`![inline code](../../../raw/prod/docs/assets/architecture/system.svg)`\n\n"
        "```text\n"
        "![fenced](../../../raw/prod/docs/assets/architecture/system.svg)\n"
        "```\n",
        encoding="utf-8",
    )
    source_b = docs / "b.md"
    source_b.write_text("# Details\n\nDetails stay ordinary Markdown.\n", encoding="utf-8")

    config = {
        "schema_version": 1,
        "asset_manifests": [
            {
                "path": "bld/architecture/assets.yml",
                "publish_prefix": "assets/architecture",
            }
        ],
        "documents": [
            {"id": "architecture", "source": "docs/a.md"},
            {"id": "details", "source": "docs/b.md"},
        ],
        "indexes": [
            {
                "output": "documents/README.md",
                "title": "Generated documents",
                "sections": [
                    {
                        "title": "Architecture",
                        "items": [
                            {"document": "architecture"},
                            {"document": "details"},
                            {"label": "Planning", "target": "../planning/README.md"},
                        ],
                    }
                ],
            }
        ],
        "books": [
            {
                "output": "documents/book.md",
                "title": "Architecture book",
                "description": "Combined review copy.",
                "documents": ["architecture", "details"],
            }
        ],
    }
    config_path = root / "assembly.yml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    return root, config_path, source_a


def test_assemble_localizes_only_manifest_assets(tmp_path):
    root, config_path, source_a = _fixture(tmp_path)
    original = source_a.read_text(encoding="utf-8")
    out = root / "bld" / "docs"

    result = assemble(root, config_path, out)

    assert result == {"documents": 2, "assets": 1, "indexes": 1, "books": 1}
    assert source_a.read_text(encoding="utf-8") == original

    generated = (out / "documents" / "a.md").read_text(encoding="utf-8")
    assert "![System](../assets/architecture/system.svg)" in generated
    assert "[Download](../assets/architecture/system.svg)" in generated
    assert "[Local document](./b.md)" in generated
    assert "`![inline code](../../../raw/prod/docs/assets/architecture/system.svg)`" in generated
    assert "![fenced](../../../raw/prod/docs/assets/architecture/system.svg)" in generated

    assert (out / "assets" / "architecture" / "system.svg").read_text(encoding="utf-8") == "<svg>system</svg>\n"
    assert (out / "_manifests" / "01-assets.yml").is_file()


def test_assemble_builds_index_and_book(tmp_path):
    root, config_path, _ = _fixture(tmp_path)
    out = root / "bld" / "docs"

    assemble(root, config_path, out)

    index = (out / "documents" / "README.md").read_text(encoding="utf-8")
    assert "[Architecture](a.md)" in index
    assert "[Details](b.md)" in index
    assert "[Planning](../planning/README.md)" in index

    book = (out / "documents" / "book.md").read_text(encoding="utf-8")
    assert "# Architecture book" in book
    assert "## Architecture" in book
    assert "## Details" in book
    assert "### Architecture" not in book
    assert "**Source document:** [a.md](a.md)" in book
    assert "![System](../assets/architecture/system.svg)" in book


def test_assemble_allows_explicit_document_output_override(tmp_path):
    root, config_path, _ = _fixture(tmp_path)
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    data["documents"][1]["output"] = "custom/details.md"
    config_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    assemble(root, config_path, root / "bld" / "docs")

    assert (root / "bld" / "docs" / "custom" / "details.md").is_file()
    index = (root / "bld" / "docs" / "documents" / "README.md").read_text(encoding="utf-8")
    assert "[Details](../custom/details.md)" in index


def test_assemble_source_renumbering_keeps_stable_document_references(tmp_path):
    root, config_path, _ = _fixture(tmp_path)
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    original = root / "docs" / "a.md"
    renumbered = root / "docs" / "20-architecture.md"
    original.rename(renumbered)
    data["documents"][0]["source"] = "docs/20-architecture.md"
    config_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    assemble(root, config_path, root / "bld" / "docs")

    assert data["indexes"][0]["sections"][0]["items"][0] == {"document": "architecture"}
    assert data["books"][0]["documents"][0] == "architecture"
    assert (root / "bld" / "docs" / "documents" / "20-architecture.md").is_file()

    index = (root / "bld" / "docs" / "documents" / "README.md").read_text(encoding="utf-8")
    assert "[Architecture](20-architecture.md)" in index

    book = (root / "bld" / "docs" / "documents" / "book.md").read_text(encoding="utf-8")
    assert "**Source document:** [20-architecture.md](20-architecture.md)" in book


def test_assemble_rejects_duplicate_document_output_path(tmp_path):
    root, config_path, _ = _fixture(tmp_path)
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    data["documents"][1]["output"] = "documents/a.md"
    config_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    try:
        assemble(root, config_path, root / "bld" / "docs")
    except ValueError as exc:
        assert "duplicate document output path: documents/a.md" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_assemble_rejects_parent_output_path(tmp_path):
    root, config_path, _ = _fixture(tmp_path)
    data = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    data["documents"][0]["output"] = "../escape.md"
    config_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    try:
        assemble(root, config_path, root / "bld" / "docs")
    except ValueError as exc:
        assert "must be a relative path without '..'" in str(exc)
    else:
        raise AssertionError("expected ValueError")
