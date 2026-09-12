from pathlib import Path

from eng_docs.cli import main


FIXTURES = Path(__file__).parent / "fixtures"


def test_cli_renders_diagrams(tmp_path):
    out = tmp_path / "out"
    result = main(["diagrams", "--source", str(FIXTURES), "--out", str(out)])

    assert result == 0
    assert (out / "simple-flow.svg").is_file()
    assert (out / "simple-flow.drawio").is_file()


def test_cli_reports_invalid_source(tmp_path, capsys):
    source = tmp_path / "source"
    source.mkdir()
    (source / "invalid.yaml").write_text("diagram: {}\n", encoding="utf-8")

    result = main(["diagrams", "--source", str(source), "--out", str(tmp_path / "out")])

    assert result == 2
    assert "invalid diagram source" in capsys.readouterr().err


def test_cli_reports_missing_source_directory(tmp_path, capsys):
    result = main([
        "diagrams",
        "--source",
        str(tmp_path / "missing"),
        "--out",
        str(tmp_path / "out"),
    ])

    assert result == 2
    assert "diagram source directory does not exist" in capsys.readouterr().err
