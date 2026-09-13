# tool.eng-docs

Reusable, project-independent tooling for engineering documentation.

The released `v0.1.1` capability is the declarative diagram renderer: author a
small YAML model and generate both an SVG for documentation and a native editable
draw.io file.

The repository intentionally owns reusable tooling and schema/layout behavior,
not consuming-project engineering semantics.

## Current capabilities

`v0.1.1` provides:

- declarative YAML diagram sources;
- JSON Schema validation plus semantic reference validation;
- reusable YAML themes;
- SVG generation;
- native editable draw.io generation;
- automatic orthogonal edge routing;
- explicit edge anchors and waypoint routes;
- domain-neutral conformance examples/tests;
- Linux and Windows verification;
- the `eng-docs diagrams` CLI;
- human-facing diagram authoring documentation and tested examples.

Planning/roadmap and printable PDF work is tracked separately in issue #3.
Common document assembly is being designed separately in issue #4 and must not
replace the existing producer-specific diagram model.

## Install

The current released version is `v0.1.1`.

A repository can pin it directly from GitHub:

```text
python -m pip install "brainboxemb-eng-docs @ git+https://github.com/brainboxemb/tool.eng-docs.git@v0.1.1"
```

The package installs the `eng-docs` command.

## Five-minute quick start

Create a directory for diagram sources, for example:

```text
docs/_diagrams/
```

Add `docs/_diagrams/service-flow.yaml`:

```yaml
diagram:
  id: service-flow
  title: Service flow
  width: 760
  height: 360

groups: []

nodes:
  - id: client
    label: Client
    kind: component
    layout: {x: 80, y: 150, w: 180, h: 60}
  - id: service
    label: Service
    kind: service
    layout: {x: 500, y: 150, w: 180, h: 60}

edges:
  - from: client
    to: service
    label: request
```

Render all `.yaml` files in that directory:

```text
eng-docs diagrams --source docs/_diagrams --out bld/docs/architecture
```

Generated files:

```text
bld/docs/architecture/service-flow.svg
bld/docs/architecture/service-flow.drawio
```

The SVG is intended for embedding in Markdown/HTML. The `.drawio` file is a
native editable diagrams.net/draw.io document.

Output filenames are based on `diagram.id`, not on the YAML filename.

## Diagram source model

The complete current authoring contract is documented in
[docs/diagram-authoring.md](docs/diagram-authoring.md).

That guide covers:

- canvas and coordinate system;
- groups and nodes;
- built-in theme `kind` values;
- directed edges and labels;
- automatic orthogonal routing;
- explicit `from_anchor` / `to_anchor` placement;
- explicit route waypoints;
- custom themes and schemas;
- validation/error behavior;
- common authoring mistakes;
- recommended project integration.

The machine-readable schema remains:

```text
src/eng_docs/schemas/diagram.schema.json
```

The built-in theme remains:

```text
src/eng_docs/themes/default.yaml
```

## User-facing examples

Start with:

```text
examples/minimal-flow.yaml
examples/routed-flow.yaml
```

The first demonstrates the minimal model and automatic routing. The second shows
visual grouping, explicit edge anchors, a dashed edge and manual waypoints.

The examples are rendered by automated tests so documentation examples remain in
sync with the released implementation.

Files under `tests/fixtures/` are conformance/stress fixtures and are not the
recommended user starting point.

## CLI reference

Current command:

```text
eng-docs diagrams \
  --source <diagram-yaml-directory> \
  --out <output-directory> \
  [--schema <diagram-schema.json>] \
  [--theme <theme.yaml>]
```

`--source` must be a directory. The command reads every direct child matching
`*.yaml`; it does not currently recurse into subdirectories.

The built-in schema and theme are used when `--schema` / `--theme` are omitted.
Invalid source returns a non-zero exit code with schema/reference validation
errors on stderr.

## Typical repository layout

A consuming repository can keep narrative Markdown and diagram producer source
separate:

```text
docs/
  architecture.md
  _diagrams/
    system-context.yaml
    runtime-view.yaml
bld/
  docs/
    architecture/
      system-context.svg
      system-context.drawio
      runtime-view.svg
      runtime-view.drawio
```

This separation is intentional:

```text
Markdown             narrative/document structure
diagram YAML          reproducible diagram semantics + layout
SVG                   generated reader-facing image
draw.io               generated editable representation
```

## Themes

The default theme contains reusable kinds including:

```text
group-primary
group-secondary
group-neutral
component
service
runtime
integration
storage
platform
external
```

A group/node `kind` must exist in the active theme. See the authoring guide for
the full behavior and custom-theme expectations.

## Validation

Validation has two layers:

1. JSON Schema validation of structure/types/ranges;
2. semantic validation of unique IDs, group references, edge node references and
   theme kinds.

This catches errors such as missing required arrays, duplicate IDs, unknown
kinds, missing groups/nodes, bad anchors and malformed waypoints before output is
published.

## Release model

`pyproject.toml` owns the package version. A non-development version merged to
`main` is released through the release workflow with the matching GitHub tag and
Python package artifacts.

Current release:

```text
v0.1.1
```

Consumers should pin a release rather than a feature branch.

## Generated conformance documentation

CI renders domain-neutral conformance fixtures so diagram quality can be reviewed
visually rather than only through assertions.

Generated output follows the documentation publication convention:

```text
pull request  -> dev/pr-<PR-number>/docs
main          -> prod/docs
```

Published conformance output includes rendered SVG fixtures, fixture YAML,
editable draw.io output and `source-sha.txt` provenance.

## Development / ownership boundary

The first reusable mechanisms were extracted from
`brainboxemb/2026-010-01.meta.event-timing-software`, but this repository must
remain project-independent.

`tool.eng-docs` owns reusable schemas, validation, rendering/layout, themes, CLI
behavior, examples and conformance tests. Consuming repositories own their actual
architecture labels, topology, requirements and diagram sources.

See [AGENTS.md](AGENTS.md) for repository working rules.