"""Command-line entry point for engineering-document tooling."""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path
import argparse
import sys

import yaml

from .assembly_output import assemble_output
from .diagrams import generate
from .engineering_graph import write_graph
from .manifests import build_manifest
from .roadmap import generate as generate_roadmap
from .board import generate as generate_board


def main(argv=None):
    parser = argparse.ArgumentParser(prog="eng-docs")
    sub = parser.add_subparsers(dest="command", required=True)

    diagrams = sub.add_parser("diagrams", help="render declarative diagrams")
    diagrams.add_argument("--source", required=True, help="directory containing diagram YAML files")
    diagrams.add_argument("--out", required=True, help="output directory")
    diagrams.add_argument("--schema", help="diagram JSON Schema; built-in default is used when omitted")
    diagrams.add_argument("--theme", help="theme YAML; built-in default is used when omitted")

    roadmap = sub.add_parser("roadmap", help="render a generic RoadmapView")
    roadmap.add_argument("--source", required=True, help="RoadmapView YAML file")
    roadmap.add_argument("--out", required=True, help="output directory")
    roadmap.add_argument(
        "--schema",
        help="roadmap JSON Schema; built-in default is used when omitted",
    )

    board = sub.add_parser("board", help="render a generic BoardView")
    board.add_argument("--source", required=True, help="BoardView YAML file")
    board.add_argument("--out", required=True, help="output directory")
    board.add_argument(
        "--schema",
        help="board JSON Schema; built-in default is used when omitted",
    )

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

    graph = sub.add_parser("graph", help="normalize a Sphinx-Needs engineering graph")
    graph.add_argument("--needs", required=True, help="Sphinx-Needs needs.json export")
    graph.add_argument(
        "--relation",
        action="append",
        default=[],
        help="outgoing relation field to normalize; may be repeated",
    )
    graph.add_argument("--diagrams", help="optional declarative diagram YAML directory")
    graph.add_argument("--out", required=True, help="normalized graph JSON path")
    graph.add_argument("--review", help="optional human Markdown review path")
    graph.add_argument("--source-revision", required=True, help="exact source revision/provenance")

    assembly = sub.add_parser("assemble", help="assemble Markdown and produced assets")
    assembly.add_argument("--root", default=".", help="project root for source/config paths")
    assembly.add_argument("--config", required=True, help="assembly YAML configuration")
    assembly.add_argument("--out", required=True, help="assembled output root")
    assembly.add_argument("--source-repository", required=True, help="source repository identity for assembly provenance")
    assembly.add_argument("--source-revision", required=True, help="exact source revision materialized by this assembly run")

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

        if args.command == "roadmap":
            package_root = files("eng_docs")
            schema = (
                Path(args.schema)
                if args.schema
                else Path(str(package_root.joinpath("schemas/roadmap.schema.json")))
            )
            generate_roadmap(Path(args.source), schema, Path(args.out))
            return 0

        if args.command == "board":
            package_root = files("eng_docs")
            schema = (
                Path(args.schema)
                if args.schema
                else Path(str(package_root.joinpath("schemas/board.schema.json")))
            )
            generate_board(Path(args.source), schema, Path(args.out))
            return 0

        if args.command == "graph":
            write_graph(
                Path(args.needs),
                Path(args.out),
                relation_types=args.relation,
                diagrams_root=Path(args.diagrams) if args.diagrams else None,
                review_path=Path(args.review) if args.review else None,
                source_revision=args.source_revision,
            )
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
            assemble_output(
                root,
                config,
                Path(args.out),
                source_repository=args.source_repository,
                source_revision=args.source_revision,
            )
            return 0
    except (ValueError, OSError, yaml.YAMLError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
