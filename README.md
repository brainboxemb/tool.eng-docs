# tool.eng-docs

Reusable, project-independent tooling for engineering documentation.

`tool.eng-docs` owns reusable documentation mechanisms and schemas, not the
engineering meaning or build semantics of consuming repositories.

## Current capabilities

`v0.2.0` provides two bounded capabilities.

### Declarative diagrams

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

### Document assembly

- `eng-docs manifest` describes already-produced assets/evidence without taking
  ownership of their build;
- `eng-docs assemble` creates self-contained Markdown review/publication trees
  from authoritative source Markdown plus producer manifests;
- generic asset/evidence metadata covers build, design-document, verification and
  docs lifecycles;
- normal Markdown/image links are localized only in the generated copy, so source
  Markdown remains directly useful on GitHub;
- stable document IDs support ordered indexes and combined books without coupling
  document identity to a filename;
- `assembly-info.yml` retains assembler version, source repository/revision,
  configuration digest and input-manifest provenance;
- output is staged safely before replacing the requested assembly tree.

The assembly boundary was qualified against both the event-timing software-doc
consumer and the current SCAD reference consumer. It consumes producer output;
it does **not** run OpenSCAD, Maven, verification or diagram producers itself.

See [docs/document-assembly.md](docs/document-assembly.md) and the executable
`examples/assembly/` example.

Planning/roadmap and printable PDF work is tracked separately in issue #3.

## Install

Pin the released version from GitHub:

```text
python -m pip install "brainboxemb-eng-docs @ git+https://github.com/brainboxemb/tool.eng-docs.git@v0.2.0"
```

The package installs the `eng-docs` command.

## Five-minute diagram quick start

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

The SVG is intended for Markdown/HTML. The `.drawio` file is a native editable
diagrams.net/draw.io document. Output filenames are based on `diagram.id`, not on
the YAML filename.

## Diagram source model

The complete authoring contract is documented in
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

The machine-readable diagram schema is:

```text
src/eng_docs/schemas/diagram.schema.json
```

The built-in theme is:

```text
src/eng_docs/themes/default.yaml
```

## User-facing examples

Diagram examples:

```text
examples/minimal-flow.yaml
examples/routed-flow.yaml
```

The first demonstrates the minimal model and automatic routing. The second shows
visual grouping, explicit edge anchors, a dashed edge and manual waypoints.

Document-assembly example:

```text
examples/assembly/
```

The examples are exercised by automated tests so documentation and behavior stay
aligned. Files under `tests/fixtures/` are conformance/stress fixtures rather than
the recommended user starting point.

## CLI reference

Diagram generation:

```text
eng-docs diagrams \
  --source <diagram-yaml-directory> \
  --out <output-directory> \
  [--schema <diagram-schema.json>] \
  [--theme <theme.yaml>]
```

Asset manifest generation and assembly are documented in
[docs/document-assembly.md](docs/document-assembly.md). The executable example
shows the normal flow:

```text
producer output -> eng-docs manifest -> eng-docs assemble -> self-contained docs tree
```

`--source` for `diagrams` must be a directory. The command reads every direct
child matching `*.yaml`; it does not currently recurse into subdirectories.

## Typical repository layout

A consuming repository can keep narrative Markdown and producer source separate:

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

Diagram validation has two layers:

1. JSON Schema validation of structure/types/ranges;
2. semantic validation of unique IDs, group references, edge node references and
   theme kinds.

Document assembly validates asset manifests and assembly configuration against
packaged JSON Schemas and also checks path safety, source immutability and
resolvable declared assets.

## Release model

This is a tooling repository, so root `VERSION`, the Python package version in
`pyproject.toml` and runtime `eng_docs.__version__` form one checked release
contract.

A release is not created merely because a version change reaches `main`.
Production order is:

```text
merge qualified implementation
  -> Test green on exact main commit
  -> guarded release request
  -> immutable vX.Y.Z tag
  -> Test again on the exact tag
  -> build wheel/sdist
  -> GitHub Release
```

Generic release/tag gating is delegated to released `tool.git-project`; Python
package construction remains owned here.

Current release target:

```text
v0.2.0
```

Consumers should pin a release rather than a feature branch.

## Generated conformance documentation

CI publishes domain-neutral review evidence so behavior can be inspected without
relying only on assertions or long Actions logs.

Generated output follows the shared lifecycle convention:

```text
pull request  -> dev/pr-<PR-number>/docs
main          -> prod/docs
release tag   -> rel/vX.Y.Z/docs
```

Published conformance output includes:

- rendered SVG fixtures and editable draw.io output;
- fixture YAML;
- the executable assembly example as a self-contained generated document tree;
- assembly input/configuration, producer manifest and `assembly-info.yml`
  provenance;
- human-readable pytest output;
- `source-sha.txt` provenance for the owner repository snapshot.

Publication and PR-preview cleanup use released `tool.git-project` lifecycle
primitives; `tool.eng-docs` only prepares the documentation tree.

## Development / ownership boundary

The first reusable mechanisms were extracted from
`brainboxemb/2026-010-01.meta.event-timing-software`, but this repository remains
project-independent.

`tool.eng-docs` owns reusable schemas, validation, rendering/layout, themes,
generic document assembly, CLI behavior, examples and conformance tests.
Consuming repositories own their actual architecture labels, topology,
requirements, diagram sources and producer-specific build/verification
semantics.

See [AGENTS.md](AGENTS.md) for repository working rules.
