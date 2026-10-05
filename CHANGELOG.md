# Changelog

## Unreleased

### Changed

- resolve explicit edge anchors on custom polygon groups against the authored outline boundary in SVG and draw.io instead of the rectangular layout bounding box.


## 0.9.3 — 2026-10-04

### Changed

- prefer the whitespace corridor between distinct non-overlapping endpoint groups
  for cross-layer node-to-node relationships when the resolved anchors face that
  gap;
- preserve deterministic midpoint placement in horizontal and vertical group
  corridors while keeping component/group placement authoritative;
- reject a preferred corridor when another node or unrelated group blocks it,
  then fall back to the existing obstacle-aware orthogonal router;
- emit the chosen corridor as equivalent SVG geometry and editable draw.io
  waypoints.

### Compatibility

- diagram YAML syntax is unchanged;
- explicit `route:` waypoints remain authoritative and bypass corridor
  selection;
- same-group edges and edges without a useful group corridor retain the existing
  routing behavior;
- group endpoints remain outside this node-to-node corridor preference.


## 0.9.2 — 2026-10-04

### Changed

- automatically detour structural node-to-node edges around intermediate
  component rectangles when the normal orthogonal path would cross them;
- keep routing deterministic with a small clearance and preserve deliberate
  component placement;
- emit the same generated detour as editable draw.io waypoints as well as SVG
  geometry;
- when only one edge anchor is authored, infer the opposite anchor position from
  that exact coordinate so naturally aligned connections remain straight without
  a second fractional anchor adjustment.

### Compatibility

- diagram YAML syntax is unchanged;
- explicit `route:` waypoints remain the authoritative escape hatch;
- existing routes that do not cross another node keep their previous geometry;
- group-endpoint routing is unchanged in this slice.


## 0.9.1 — 2026-10-01

### Changed

- allow BoardView detail boards to span multiple portrait A4 pages instead of
  forcing consumers to shorten authoritative planning content;
- paginate at top-level board-block boundaries while preserving existing
  typography/card sizing;
- generate real multi-page PDF output and a continuous SVG review view with
  visible page-break markers.

### Compatibility

- existing one-page BoardView sources remain valid and keep a one-page layout;
- BoardView YAML schema is unchanged;
- an individual top-level block is still indivisible and produces a clear error
  only when that block itself cannot fit on one A4 page.


## 0.9.0 — 2026-10-01

### Added

- declarative UI wireframe node notations for panels, tabs, inputs, buttons,
  tables and status pills in the existing structural YAML model;
- matching deterministic SVG rendering and native editable draw.io cells;
- domain-neutral wireframe example, authoring documentation and regression tests.

### Compatibility

- existing structure/sequence YAML remains valid and renders unchanged;
- wireframe semantics remain presentation-only; consuming repositories retain
  application/UI state meaning through labels, layout and theme kinds;
- the README install example now pins the prepared v0.9.0 release.

## 0.8.1 — 2026-10-01

### Changed

- reduce default vertical spacing between sequence messages so short interaction
  diagrams use substantially less canvas height;
- increase sequence message-label text from 12 px to 13 px;
- wrap long message labels automatically to the horizontal space available
  between participants;
- balance two-line labels around word boundaries instead of leaving very short
  trailing lines;
- preserve explicit source line breaks and grow only the affected message row;
- keep SVG and native editable draw.io label layout consistent.

### Compatibility

- sequence source syntax and call/async/return semantics are unchanged;
- structural diagram rendering is unchanged;
- existing sequence sources may render more compactly without source changes.

## 0.8.0 — 2026-10-01

### Added

- native draw.io `umlLifeline` participant shapes for declarative sequence diagrams;
- inferred UML activation bars for synchronous calls and matching returns;
- self messages, including synchronous and asynchronous loopback interactions;
- activation-aware SVG/message geometry matching the editable draw.io output.

### Changed

- sequence diagrams now render as conventional UML interaction views instead of
  generic participant cards with separately drawn lifelines;
- activation bars remain simple editable child cells so the draw.io output does
  not depend on a separate stencil library;
- the domain-neutral sequence example and conformance tests cover async hand-off,
  self processing, persistence and return behaviour.

### Compatibility

- existing sequence sources using `call`, `async` and `return` remain valid;
- existing structural diagram sources and rendering are unchanged;
- UML interaction fragments such as `alt`, `loop` and `par` remain deferred.


## 0.7.0 — 2026-09-30

### Added

- declarative `diagram.type: sequence` sources with ordered participants and messages;
- first-slice message semantics for `call`, `async` and `return`;
- deterministic participant/lifeline/message layout in SVG;
- native editable draw.io sequence output from the same YAML source;
- domain-neutral sequence example, schema/semantic validation and Linux/Windows regression coverage;
- generated conformance preview for the user-facing sequence example.

### Architecture

- sequence diagrams extend the existing `eng-docs diagrams` YAML → SVG + draw.io pipeline instead of introducing Mermaid, PlantUML, Node or Java rendering dependencies;
- structural diagram sources remain valid without adding a `type` field; omitted `diagram.type` continues to mean the existing structural form;
- the first slice deliberately defers full UML interaction fragments, activation bars, destruction markers and self messages until a real consumer requires them.

### Compatibility

- existing structural diagram rendering and source semantics are unchanged;
- engineering-graph normalization safely ignores sequence diagrams for object-reference extraction in this first slice.

## 0.6.6 — 2026-09-30

### Changed

- remove the obsolete `baseline` term from the BoardView planning example and
  documentation so the example matches the current `orig / act / rem / total est`
  terminology used by consumers.

### Compatibility

- renderer behavior and BoardView schema are unchanged.

## 0.6.5 — 2026-09-30

### Changed

- move the optional BoardView marker to the leading left edge of the title row and
  render it larger/bolder for faster left-to-right scanning;
- join board-level metadata values with ` | ` into one continuous status line
  beneath the title row, wrapping only when necessary.

### Compatibility

- the BoardView source schema is unchanged; existing marker and meta data render
  with the refined hierarchy.

## 0.6.4 — 2026-09-30

### Added

- BoardView cards support optional `header_meta` values rendered inline after
  the bold card ID;
- multiple header metadata values are presented compactly with ` | ` separators;
- header metadata wraps within the space left by the ID and optional status chip.

### Changed

- render all BoardView section and group headings with the same neutral uppercase
  typography and rule style so color remains reserved for semantic badges/status.

### Compatibility

- existing card `meta` remains available for longer descriptive text below the title;
- existing BoardView sources remain valid.

## 0.6.3 — 2026-09-30

### Changed

- reduce BoardView outer margin and generic vertical block spacing slightly;
- reduce inter-group separation while retaining existing typography, card
  padding and wrapping;
- keep one-page overflow detection explicit rather than clipping dense content.

### Compatibility

- BoardView source schema and consumer semantics are unchanged.

## 0.6.2 — 2026-09-30

### Added

- BoardView supports optional one- or two-column section rows;
- two-column sections wrap independently and share the taller row height;
- compact side-by-side summaries reduce vertical page usage without shrinking
  typography or clipping content.

### Compatibility

- `section_columns` defaults to 1;
- section headings and content remain opaque presentation data.

## 0.6.1 — 2026-09-30

### Changed

- BoardView supports an optional compact board-level `marker` in the upper
  right so consumers do not need to repeat identity in the title;
- BoardView supports an optional headed `summary` using normal body typography,
  keeping descriptive prose separate from compact planning metadata;
- section rules now begin after the rendered heading width and no longer cross
  longer headings.

### Compatibility

- existing BoardView sources without `marker` or `summary` remain valid;
- no domain-specific Step, Goal or Demo semantics are added to the renderer.

## 0.6.0 — 2026-09-30

### Added

- generic print-friendly `BoardView` schema and `eng-docs board` CLI;
- deterministic A4 portrait SVG/PDF rendering for sections, badge groups,
  named card groups and trailing notes;
- adaptive three-column detail cards whose height grows with wrapped content;
- shared presentation-style primitives used by RoadmapView and BoardView;
- domain-neutral BoardView example, documentation and Linux/Windows tests.

### Boundary

- consumers own lane/group/activity/document/planning semantics and adapt them
  into BoardView presentation data;
- large colored background panels are deliberately avoided; color is used mainly
  for compact status/accent information;
- BoardView never parses SIP or event-timing planning sources.

## 0.5.2 — 2026-09-30

### Changed

- reduce the default roadmap outer margin, inter-column gap and card padding so
  A4 landscape width is used more efficiently;
- keep three-column layout viable for denser real-consumer cards before falling
  back to two or one column;
- retain current typography, adaptive card height, wrapping and pagination.

### Compatibility

- RoadmapView source data and semantics are unchanged;
- no content clipping, fixed-height cards or source-text limits are introduced.

## 0.5.1 — 2026-09-30

### Changed

- roadmap cards regain a calmer fixed visual hierarchy while retaining adaptive
  height, wrapping and pagination;
- optional compact item `marker` supports number-style step identity without
  overloading the opaque item id;
- the first ordered meta value occupies the stable upper metadata area, with
  remaining values shown as secondary context;
- optional `badge_heading` groups generic badges under a named section;
- neutral card frames and section rules reduce visual noise while state tone
  remains visible in the state chip.

### Compatibility

- existing RoadmapView inputs without `marker` or `badge_heading` remain valid;
- no fixed-height boxes or source-text line limits are reintroduced.

## 0.5.0 — 2026-09-30

### Added

- generic `RoadmapView` YAML schema and `eng-docs roadmap` CLI;
- adaptive 3/2/1-column roadmap layout with row pagination rather than fixed
  source-text line limits;
- deterministic per-page SVG, panorama SVG and printable PDF output;
- domain-neutral roadmap example and regression coverage for long text,
  pagination, duplicate IDs, unknown tones and deterministic output.

### Boundary

- consumers own authoritative planning and the adapter into compact RoadmapView
  presentation data;
- roadmap section/state/badge labels are opaque to the renderer;
- project planning prose is not parsed or constrained by roadmap card geometry.

## 0.4.5 — 2026-09-29

### Added

- optional non-negative `outline.corner_radius` for custom group outlines;
- rounded SVG path rendering that preserves authored polygon geometry;
- editable draw.io rounded-polygon styling;
- regression coverage for both rounded and unchanged sharp custom outlines.

### Compatibility

- custom outlines without `corner_radius`, or with radius `0`, retain the existing sharp polygon rendering.

## 0.4.4 — 2026-09-29

### Added

- optional `properties_width` layout control for semantic-group property blocks;
- SVG/draw.io regression coverage for explicit property-column alignment.

### Compatibility

- automatic property-block sizing remains the default when `properties_width` is omitted.

## 0.4.3 — 2026-09-29

### Added

- optional semantic-group `properties` list;
- neutral inner SVG property block with a simple dash list and no stereotype/title;
- equivalent editable draw.io inner property block;
- schema validation, domain-neutral example and Linux/Windows regression coverage.

### Clarified

- group `note` remains explanatory secondary text;
- group `properties` are compact architecture-view identity/state concepts and do not imply exact implementation fields or a UML class contract.

## 0.4.2 — 2026-09-29

### Added

- optional `object_id` on semantic diagram groups;
- SVG and editable draw.io `data-engineering-id` preservation for identified groups;
- engineering-graph normalization of group diagram references;
- rendering of the existing optional group `note` directly below the group heading;
- duplicate identity validation across groups, nodes and nested items;
- domain-neutral examples and Linux/Windows regression coverage.

### Compatibility

- visual groups that omit `object_id` and `note` keep the existing rendering path;
- consumers decide whether a group is merely layout or a stable engineering object.

## 0.4.1 — 2026-09-29

### Added

- optional `object_id` on object-form structured diagram items;
- SVG `data-engineering-id` preservation for identified nested item rows;
- matching item identity retained in editable draw.io node HTML;
- duplicate identity validation across top-level nodes and nested items;
- engineering-graph normalization of nested item diagram references;
- domain-neutral examples and Linux/Windows regression coverage.

### Compatibility

- string items remain display-only and existing diagrams render through the same path;
- consumers choose which structured items are engineering objects; the tool does not infer identity from labels.

## 0.4.0 — 2026-09-28

### Added

- reusable `eng-docs graph` normalization from an existing Sphinx-Needs
  `needs.json` export;
- explicit selection of outgoing relation fields without hard-coding project
  relation names;
- deterministic normalized graph JSON retaining Need identity, type, title,
  content, source location and diagram references;
- human Markdown review with authored outgoing and generated incoming relations;
- diagram `object_id` cross-validation against existing engineering objects;
- domain-neutral executable Needs-export example and Linux/Windows test coverage.

### Boundary

- native MyST/Sphinx-Needs owns engineering-object authoring, stable IDs, typed
  relation rules and backlink generation;
- `tool.eng-docs` does not maintain a second Markdown/hidden-JSON authoring
  parser;
- diagram `object_id` values reference existing engineering objects rather
  than define duplicates;
- relation names and project semantics remain consumer-owned;
- consuming a Needs JSON export does not add a Sphinx-Needs runtime dependency
  to `tool.eng-docs`;
- portal generation remains outside this release.

## 0.3.11 — 2026-09-28

### Added

- optional node `object_id` as opaque project-owned engineering identity, separate from diagram-local routing/layout `id`;
- SVG preservation through `data-engineering-id` on the rendered node group;
- matching `data-engineering-id` metadata on editable draw.io node cells;
- duplicate engineering-object identity validation and domain-neutral example/test coverage.

### Compatibility

- nodes without `object_id` render exactly through the existing visual path;
- the renderer does not depend on Sphinx-Needs or validate object IDs against an external engineering graph;
- groups do not gain engineering identity in this first slice.

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
