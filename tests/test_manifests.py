from pathlib import Path

import yaml

from eng_docs.manifests import build_manifest, load_manifest


def test_build_manifest_describes_existing_outputs(tmp_path):
    source = tmp_path / "produced"
    source.mkdir()
    (source / "overview.svg").write_text("<svg/>\n", encoding="utf-8")
    (source / "overview.drawio").write_text("<mxfile/>\n", encoding="utf-8")
    out = source / "assets.yml"

    data = build_manifest(
        source,
        out,
        producer="example.diagrams",
        producer_version="1.2.3",
        source_revision="0123456789abcdef",
        lifecycle="docs",
        relationship="producer-source",
    )

    assert out.is_file()
    assert data["producer"] == {
        "name": "example.diagrams",
        "version": "1.2.3",
        "source_revision": "0123456789abcdef",
    }
    assert [item["path"] for item in data["assets"]] == [
        "overview.drawio",
        "overview.svg",
    ]
    assert all(item["lifecycle"] == "docs" for item in data["assets"])
    assert all(item["relationship"] == "producer-source" for item in data["assets"])
    assert load_manifest(out) == yaml.safe_load(out.read_text(encoding="utf-8"))


def test_manifest_include_filters_outputs(tmp_path):
    source = tmp_path / "produced"
    source.mkdir()
    (source / "overview.svg").write_text("<svg/>\n", encoding="utf-8")
    (source / "overview.drawio").write_text("<mxfile/>\n", encoding="utf-8")

    data = build_manifest(
        source,
        source / "assets.yml",
        producer="example.diagrams",
        source_revision="deadbeef",
        lifecycle="docs",
        relationship="producer-source",
        include=["*.svg"],
    )

    assert [item["path"] for item in data["assets"]] == ["overview.svg"]


def test_manifest_remains_domain_neutral_for_java_build_evidence(tmp_path):
    source = tmp_path / "bld"
    evidence = source / "evidence" / "tests"
    evidence.mkdir(parents=True)
    (source / "event-timing.jar").write_bytes(b"jar-placeholder")
    (source / "provenance.txt").write_text("source=0123456789abcdef\n", encoding="utf-8")
    (evidence / "README.md").write_text("# Test evidence\n", encoding="utf-8")
    (evidence / "TEST-example.xml").write_text("<testsuite tests='1'/>\n", encoding="utf-8")

    data = build_manifest(
        source,
        source / "assets.yml",
        producer="tool.java-project",
        producer_version="test-sha",
        source_revision="0123456789abcdef",
        lifecycle="build",
        relationship="reference-existing",
    )

    assert {item["path"] for item in data["assets"]} == {
        "event-timing.jar",
        "provenance.txt",
        "evidence/tests/README.md",
        "evidence/tests/TEST-example.xml",
    }
    assert all(
        set(item) == {"id", "kind", "lifecycle", "relationship", "path"}
        for item in data["assets"]
    )
    assert all(item["lifecycle"] == "build" for item in data["assets"])
    assert all(item["relationship"] == "reference-existing" for item in data["assets"])


def test_manifest_rejects_unknown_lifecycle(tmp_path):
    source = tmp_path / "produced"
    source.mkdir()

    try:
        build_manifest(
            source,
            source / "assets.yml",
            producer="example",
            source_revision="deadbeef",
            lifecycle="unknown",
            relationship="producer-source",
        )
    except ValueError as exc:
        assert "unknown asset lifecycle" in str(exc)
    else:
        raise AssertionError("expected ValueError")
