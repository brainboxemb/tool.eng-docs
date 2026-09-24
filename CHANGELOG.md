# Changelog

All notable changes to `tool.eng-docs` are recorded here.

## 0.2.1 — 2026-09-24

### Added

- optional diagram node `subtitle` text rendered beneath the primary label at a smaller size in SVG and draw.io output;
- backwards-compatible `node_subtitle_size` theme support, with a derived fallback for existing custom themes.

## 0.2.0 — 2026-09-13

### Added

- `eng-docs manifest` for domain-neutral descriptions of already-produced build, design-document, verification and documentation assets;
- `eng-docs assemble` for self-contained Markdown review/publication trees assembled from authoritative source Markdown plus producer manifests;
- JSON Schemas for asset manifests and assembly configuration;
- stable document IDs, optional derived document output paths, ordered indexes and combined books;
- generated `assembly-info.yml` provenance with assembler version, source repository/revision, configuration digest and input-manifest provenance;
- safe staged assembly that replaces an existing output tree only after successful generation;
- executable user-facing assembly example and generated review evidence on `dev/pr-N/docs` / `prod/docs`;
- published pytest output alongside generated conformance documentation.

### Qualified

- software-document consumer `2026-010-01.meta.event-timing-software` using its normal managed `tool.eng-docs` git dependency;
- current SCAD reference consumer `template.scad-project` without replacing `scad-render`, OpenSCAD or `tool.scad-project` ownership;
- cross-domain manifest genericity against the actual Java reference publication-tree shape without Java/Maven/Surefire-specific schema fields;
- document renumbering through stable IDs so source filename changes do not require matching index/book identifier changes.

### Architecture

- assembly consumes already-produced outputs and does not schedule SCAD, Java, verification or diagram producers;
- publication destination/branch selection remains an external repository/CI orchestration responsibility;
- generated conformance publication and PR-preview cleanup use released `tool.git-project` lifecycle primitives;
- the two-consumer qualification did not justify a mandatory repository-wide `project.docs.yml`;
- verification evidence-bundle semantics, broader Markdown syntax and producer orchestration remain deferred until a real consumer requires them.

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
