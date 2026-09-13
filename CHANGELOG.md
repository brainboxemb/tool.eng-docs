# Changelog

All notable changes to `tool.eng-docs` are recorded here.

## 0.1.1 — 2026-09-13

### Added

- README installation and five-minute diagram quick start;
- complete `docs/diagram-authoring.md` user guide for the existing YAML model;
- user-facing `examples/minimal-flow.yaml` and `examples/routed-flow.yaml`;
- automated rendering tests for the user-facing examples on Linux and Windows;
- repository guidance requiring public capabilities/source-model changes to ship with usable human documentation and tested examples.

### Clarified

- canvas coordinates, groups, nodes, edges, theme `kind` lookup and validation behavior;
- automatic orthogonal routing, explicit edge anchors and manual waypoint routing;
- generated SVG/draw.io naming and recommended repository integration;
- machine-readable schemas remain authoritative validation contracts but are not a substitute for human-facing documentation.

### Compatibility

- no diagram YAML schema or renderer behavior changes from v0.1.0;
- `eng-docs diagrams` remains the released public capability;
- common document assembly remains separate work under issue #4 and is not part of v0.1.1.

## 0.1.0 — 2026-09-12

### Added

- reusable Python package and `eng-docs` CLI;
- declarative YAML diagram source model;
- JSON Schema validation and reference validation;
- reusable built-in visual theme;
- deterministic SVG generation;
- native editable draw.io generation;
- automatic orthogonal routing;
- explicit route waypoints, dashed edges and labels;
- explicit edge anchors using side plus relative position;
- domain-neutral simple-flow, layered-architecture and routing-stress fixtures;
- CLI success/failure tests;
- Linux and Windows test matrix;
- generated conformance documentation on `dev/pr-<N>/docs` and `prod/docs`;
- automatic GitHub tag/release creation from the package version on `main`;
- issue-first, early-draft-PR working method.

### Deferred

- reusable planning/roadmap and printable PDF generation is tracked separately in issue #3 rather than delaying the first reusable diagram release.

### Consumer direction

- the first intended real consumer is `brainboxemb/2026-010-01.meta.event-timing-software`, pinned to release `v0.1.0` before its duplicate local generic diagram renderer is removed.
