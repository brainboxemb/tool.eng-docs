"""Command-line entry point for engineering-document tooling."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path
import argparse
import sys

import yaml

from .assembly import assemble
from .diagrams import generate
from .manifests import build_manifest


def main(argv=None):
    parser = argparse.ArgumentParser(prog="eng-docs")
    sub = parser.add_subparsers(dest="command", required=True)

    diagrams = sub.add_parser("diagrams", help="render declarative diagrams")
    diagrams.add_argument("--source", required=True, help="directory containing diagram YAML files")
    diagrams.add_argument("--out", required=True, help="output directory")
    diagrams.add_argument("--schema", help="diagram JSON Schema; built-in default is used when omitted")
    diagrams.add_argument("--theme", help="theme YAML; built-in default is used when omitted")

    manifest = sub.add_parser("manifest", help="describe already-produced assets")
    manifest.add_argument("--source", required=True, help="directory containing produced assets")
    manifest.add_argument("--out", required=True, help="manifest YAML path")
    manifest.add_argument("--producer", required=True, help="producer identity")
    manifest.add_argument("--producer-version", help="producer version; defaults to tool.eng-docs version")
    manifest.add_argument("--source-revision", required=True, help="exact source revision/provenance")
    manifest.add_argument(
        "--lifecycle",
        required=True,
        choices=["build", "design-doc", "verification", "docs"],
        help="owning asset lifecycle",
    )
    manifest.add_argument(
        "--relationship",
        required=True,
        choices=["generate-inline", "producer-source", "reference-existing", "reference-evidence"],
        help="document-to-asset relationship",
    )
    manifest.add_argument(
        "--include",
        action="append",
        default=[],
        help="optional relative glob to include; may be repeated",
    )

    assembly = sub.add_parser("assemble", help="assemble Markdown and produced assets")
    assembly.add_argument("--root", default=".", help="project root for source/config paths")
    assembly.add_argument("--config", required=True, help="assembly YAML configuration")
    assembly.add_argument("--out", required=True, help="assembled output root")

    args = parser.parse_args(argv)
    try:
        if args.command == "diagrams":
            package_root = files("eng_docs")
            schema = Path(args.schema) if args.schema else Path(str(package_root.joinpath("schemas/diagram.schema.json")))
            theme = Path(args.theme) if args.theme else Path(str(package_root.joinpath("themes/default.yaml")))
            source = Path(args.source)
            if not source.is_dir():
                print(f"diagram source directory does not exist: {source}", file=sys.stderr)
                return 2
            generate(source, schema, theme, Path(args.out))
            return 0

        if args.command == "manifest":
            build_manifest(
                Path(args.source),
                Path(args.out),
                producer=args.producer,
                producer_version=args.producer_version,
                source_revision=args.source_revision,
                lifecycle=args.lifecycle,
                relationship=args.relationship,
                include=args.include,
            )
            return 0

        if args.command == "assemble":
            root = Path(args.root)
            config = Path(args.config)
            if not config.is_absolute():
                config = root / config
            assemble(root, config, Path(args.out))
            return 0
    except (ValueError, OSError, yaml.YAMLError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
