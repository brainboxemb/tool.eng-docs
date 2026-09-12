# tool.eng-docs

Reusable, project-independent tooling for declarative engineering documentation.

The initial v0.1.0 scope is extracted from proven documentation tooling in `brainboxemb/2026-010-01.meta.event-timing-software` and focuses on generic mechanisms rather than project-specific engineering content.

## Initial scope

- declarative YAML sources;
- JSON Schema validation;
- reusable YAML visual themes;
- native editable draw.io generation;
- SVG generation;
- planning/roadmap rendering;
- printable PDF generation where applicable;
- domain-neutral conformance fixtures and tests;
- Linux and Windows verification.

The repository must not contain event-timing-specific labels, topology, requirements or other consuming-project semantics.

## Active work

The first implementation increment is tracked by [issue #1](https://github.com/brainboxemb/tool.eng-docs/issues/1) and targets the first reusable release, `v0.1.0`.

## Extraction baseline

The reusable mechanisms were proven in `brainboxemb/2026-010-01.meta.event-timing-software`, especially issue #6 and PR #9. That project remains the owner of its project-specific YAML sources; this repository owns only reusable schemas, rendering/layout mechanisms, themes, CLI behaviour and conformance tests.
