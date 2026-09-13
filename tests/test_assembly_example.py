from pathlib import Path
import shutil

from eng_docs.cli import main


EXAMPLE = Path(__file__).parents[1] / "examples" / "assembly"


def test_user_facing_assembly_example(tmp_path):
    project = tmp_path / "assembly-example"
    shutil.copytree(EXAMPLE, project)

    result = main([
        "manifest",
        "--source", str(project / "produced"),
        "--out", str(project / "produced" / "assets.yml"),
        "--producer", "example.diagrams",
        "--producer-version", "1.0.0",
        "--source-revision", "0123456789abcdef",
        "--lifecycle", "docs",
        "--relationship", "producer-source",
        "--include", "*.svg",
    ])
    assert result == 0

    result = main([
        "assemble",
        "--root", str(project),
        "--config", "assembly.yml",
        "--out", str(project / "bld" / "docs"),
    ])
    assert result == 0

    source = (project / "docs" / "overview.md").read_text(encoding="utf-8")
    generated = (project / "bld" / "docs" / "documents" / "overview.md").read_text(encoding="utf-8")

    assert "../../../raw/prod/docs/assets/architecture/system.svg" in source
    assert "../assets/architecture/system.svg" in generated
    assert (project / "bld" / "docs" / "assets" / "architecture" / "system.svg").is_file()
    assert (project / "bld" / "docs" / "documents" / "README.md").is_file()
