from pathlib import Path

from eng_docs.assembly import Asset, rewrite_markdown


def _asset(asset_id: str, published: str) -> Asset:
    return Asset(
        id=asset_id,
        source=Path("/tmp/source.svg"),
        published_path=Path(published),
        manifest=Path("/tmp/manifest.yml"),
        producer={"name": "example", "version": "1", "source_revision": "abc"},
        metadata={},
    )


def test_more_specific_publication_path_wins_suffix_match(tmp_path):
    out = tmp_path / "docs"
    document = out / "documents" / "architecture.md"
    assets = [
        _asset("raw", "architecture/system.svg"),
        _asset("publication", "assets/architecture/system.svg"),
    ]

    generated = rewrite_markdown(
        "![System](../../../raw/prod/docs/assets/architecture/system.svg)\n",
        document_output=document,
        out_root=out,
        assets=assets,
    )

    assert generated == "![System](../assets/architecture/system.svg)\n"
