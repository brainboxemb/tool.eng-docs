from pathlib import Path

from eng_docs.cli import main


EXAMPLES = Path(__file__).parents[1] / "examples"


def test_user_examples_render(tmp_path):
    out = tmp_path / "out"

    result = main(["diagrams", "--source", str(EXAMPLES), "--out", str(out)])

    assert result == 0
    for name in ("minimal-flow", "routed-flow"):
        assert (out / f"{name}.svg").is_file()
        assert (out / f"{name}.drawio").is_file()
