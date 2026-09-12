# Changelog

All notable changes to `tool.eng-docs` are recorded here.

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
