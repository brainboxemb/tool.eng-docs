# Changelog

## 0.3.10 — 2026-09-28

### Added

- optional non-negative `label_offset` for visual groups, allowing shaped polygon groups to keep their heading inside the visible area while retaining the same layout/routing bounding box;
- matching SVG and editable draw.io label-offset rendering plus schema validation and executable example coverage.

### Compatibility

- groups without `label_offset` keep the existing title placement exactly.

## 0.3.9 — 2026-09-28

### Added

- optional normalized polygon outlines for visual groups while retaining the existing rectangular layout box for labels, routing and geometry;
- matching native SVG and editable draw.io polygon rendering using the same source points;
- a domain-neutral polygon-group example and validation for invalid outline/notation combinations, degenerate outlines and out-of-range coordinates.

### Compatibility

- groups without `outline` render exactly through the existing rounded-rectangle path;
- polygon outlines are deliberately limited to plain visual groups in this first slice; component/package/class notation remains rectangular.

## 0.3.8 — 2026-09-27

### Fixed

- packaging-component SVG notation now places the package/folder tab at the upper-left while keeping the UML component tabs on the left edge, matching the intended combined package + component icon.

## 0.3.7 — 2026-09-27

### Changed

- packaging-component SVG notation now uses one integrated package/component outline: the package body is the component body and the UML component tabs cross its left edge, removing the misleading nested component rectangle from v0.3.6.

## 0.3.6 — 2026-09-27

### Changed

- packaging-component notation now renders as a visible combination of a package/folder outline and the UML component symbol, matching the intended package-like component semantics more closely.

## 0.3.5 — 2026-09-27

### Changed

- enlarged the SVG UML component glyph so component notation remains legible in normal architecture cards while staying visually subordinate to the component name.

## 0.3.4 — 2026-09-27

### Changed

- architecture layers can remain plain groups while actual packaging components carry their own semantic notation;
- `packaging-component` is supported on both grouping containers and normal nodes;
- packaging components use a compact EA-inspired component/package glyph rather than a folder-style symbol;
- class notation uses a compact UML class box with `«class»`, class name and a short property compartment, suitable for mixed component/class architecture views.

## 0.3.3 — 2026-09-27

### Added

- distinct `packaging-component` notation for component containers, separate from ordinary component glyphs and plain visual groups/layers;
- explicit `class` notation for architecture diagrams, including a compact attribute compartment in SVG and editable draw.io output.

### Clarified

- component, packaging-component, class and visual-group semantics are now documented separately so consuming diagrams do not overload one glyph for multiple meanings.

## 0.3.2 — 2026-09-27

### Added

- `notation: component` is also supported on grouping boxes, allowing packaging-component style diagrams where a component visually owns child components while remaining distinct from a plain layer/package.

### Changed

- structured nodes with `items` place their heading at the top and flow the item hierarchy downward; simple and subtitle-only nodes retain balanced vertical alignment.

## 0.3.1 — 2026-09-27

### Added

- optional `notation: component` for nodes, rendered with UML-style component notation in SVG and native draw.io output;
- documented distinction between visual groups/containers and concrete component nodes without coupling theme `kind` to semantic notation.


All notable changes to `tool.eng-docs` are recorded here.

## 0.3.0 — 2026-09-27

### Added

- structured node `items` for compact left-aligned lists and nested tree rows in SVG and native draw.io output;
- edges may reference visual groups/layers as endpoints in addition to concrete nodes, including explicit anchors and orthogonal routing;
- domain-neutral `structured-layer.yaml` user example covering both capabilities.

### Clarified

- high-level architecture may terminate an edge on a layer boundary when the layer relationship is established but a concrete component dependency would be premature;
- automatic routing remains intentionally small and deterministic; fewer meaningful edges and layer endpoints are preferred over speculative component-to-component routing.

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
