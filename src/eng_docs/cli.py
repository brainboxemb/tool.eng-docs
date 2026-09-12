"""Command-line entry point for engineering-document tooling."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path
import argparse
import sys

from .diagrams import generate


def main(argv=None):
    parser = argparse.ArgumentParser(prog="eng-docs")
    sub = parser.add_subparsers(dest="command", required=True)

    diagrams = sub.add_parser("diagrams", help="render declarative diagrams")
    diagrams.add_argument("--source", required=True, help="directory containing diagram YAML files")
    diagrams.add_argument("--out", required=True, help="output directory")
    diagrams.add_argument("--schema", help="diagram JSON Schema; built-in default is used when omitted")
    diagrams.add_argument("--theme", help="theme YAML; built-in default is used when omitted")

    args = parser.parse_args(argv)
    if args.command == "diagrams":
        package_root = files("eng_docs")
        schema = Path(args.schema) if args.schema else Path(str(package_root.joinpath("schemas/diagram.schema.json")))
        theme = Path(args.theme) if args.theme else Path(str(package_root.joinpath("themes/default.yaml")))
        source = Path(args.source)
        if not source.is_dir():
            print(f"diagram source directory does not exist: {source}", file=sys.stderr)
            return 2
        try:
            generate(source, schema, theme, Path(args.out))
        except (ValueError, OSError) as exc:
            print(str(exc), file=sys.stderr)
            return 2
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
