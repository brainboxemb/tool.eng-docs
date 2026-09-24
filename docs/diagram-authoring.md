# Declarative diagram authoring

This guide documents the current user-facing YAML contract for
`eng-docs diagrams`.

The diagram source model is intentionally small. A source file describes:

- the canvas;
- optional visual groups;
- nodes;
- directed edges;
- optional routing hints.

`tool.eng-docs` validates the YAML, renders an SVG for normal documentation use,
and also writes a native editable draw.io file.

The machine-readable schema is
`src/eng_docs/schemas/diagram.schema.json`. This page explains how to use that
schema without having to read the implementation.

## Quick start

Put one or more `.yaml` files in a directory and run:

```text
eng-docs diagrams --source examples --out bld/docs/diagrams
```

For each valid source file the command writes:

```text
<diagram.id>.svg
<diagram.id>.drawio
```

For example, `examples/minimal-flow.yaml` contains:

```yaml
diagram:
  id: minimal-flow
  title: Minimal service flow
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

The command produces:

```text
bld/docs/diagrams/minimal-flow.svg
bld/docs/diagrams/minimal-flow.drawio
```

The SVG is suited to embedding in Markdown or HTML. The `.drawio` file can be
opened and edited in diagrams.net/draw.io.

## File discovery

`eng-docs diagrams` reads every `*.yaml` file directly inside the directory given
to `--source`.

The current command does not recurse into subdirectories.

Files are processed in sorted filename order. Output filenames are based on
`diagram.id`, not on the source filename.

## Top-level structure

Every source file has four required top-level keys:

```yaml
diagram: {}
groups: []
nodes: []
edges: []
```

All four are required even when `groups` or `edges` is empty.

Unknown top-level fields are rejected.

---

## `diagram`

`diagram` describes the canvas and output identity.

Required fields:

```yaml
diagram:
  id: system-overview
  title: System overview
  width: 1000
  height: 620
```

Optional fields:

```yaml
  description: Longer machine/human description of the diagram.
  note: Short note rendered below the title in the SVG.
```

### `id`

`id` becomes the output basename:

```text
system-overview.svg
system-overview.drawio
```

Rules:

- lowercase letters, digits and `-` only;
- must start with a lowercase letter or digit;
- use a stable semantic name because links normally reference the generated
  output by this ID.

### `title`

Human-readable diagram title. It is rendered at the top of the SVG and becomes
the diagram page name in draw.io.

### `width` / `height`

Canvas dimensions in diagram coordinate units/pixels.

Minimum values enforced by the schema:

```text
width  >= 320
height >= 240
```

All group/node/route coordinates use the same coordinate system.

### `description`

Optional descriptive metadata. The current renderer accepts it but does not place
it on the SVG canvas.

### `note`

Optional short note rendered under the SVG title.

---

## Coordinates and `layout`

Groups and nodes use the same rectangular layout shape:

```yaml
layout:
  x: 120
  y: 150
  w: 180
  h: 60
```

or the equivalent compact YAML form:

```yaml
layout: {x: 120, y: 150, w: 180, h: 60}
```

Meaning:

```text
x   left edge from canvas origin
y   top edge from canvas origin
w   width, must be > 0
h   height, must be > 0
```

The canvas origin is the top-left corner.

The current model deliberately uses explicit layout rather than an automatic
whole-diagram layout engine. This makes diagrams deterministic and makes the
source author responsible for major placement decisions.

---

## `groups`

Groups are optional visual containers/layers.

Example:

```yaml
groups:
  - id: application
    label: Application
    kind: group-primary
    layout: {x: 60, y: 80, w: 780, h: 330}
```

Required fields:

```text
id
label
kind
layout
```

Optional field:

```text
note
```

### Group `id`

Group IDs:

- may contain letters, digits, `_`, `.`, and `-`;
- must be unique among groups;
- may not reuse a node ID.

### Group `label`

Rendered heading for the visual group.

### Group `kind`

Selects a style from the active theme. With the built-in theme the group kinds
are:

```text
group-primary
group-secondary
group-neutral
```

A custom theme may define different/additional kinds.

### Group membership

Groups do not geometrically own/move their nodes. A node can declare a `group`
reference for semantic structure, while its layout remains absolute canvas
coordinates.

That means this is valid:

```yaml
nodes:
  - id: api
    group: application
    label: API
    kind: component
    layout: {x: 120, y: 150, w: 170, h: 60}
```

The referenced group ID must exist.

---

## `nodes`

Nodes are the boxes that represent components/services/runtimes/etc.

Example:

```yaml
nodes:
  - id: worker
    group: application
    label: Worker
    kind: runtime
    layout: {x: 590, y: 140, w: 180, h: 60}
```

Required fields:

```text
id
label
kind
layout
```

Optional fields:

```text
group
subtitle
note
```

### Node `id`

Node IDs:

- may contain letters, digits, `_`, `.`, and `-`;
- must be unique among nodes;
- may not reuse a group ID;
- are referenced by edge `from` and `to` fields.

### Node `label`

Human-readable rendered text. Newlines are supported and are rendered as
multi-line text in SVG/draw.io.

### Node `subtitle`

Use `subtitle` for a short secondary explanation that should have less visual
weight than the primary node name:

```yaml
- id: timing
  label: StageTiming
  subtitle: running times + ranking
  kind: service
  layout: {x: 500, y: 300, w: 220, h: 70}
```

The SVG and draw.io renderers display the subtitle beneath the label at a smaller
font size. Keep `label` for the semantic component name and `subtitle` for a
brief clarification. Existing multi-line `label` values remain supported.

Custom themes may define `font.node_subtitle_size`. When omitted, the renderer
derives a smaller size from `font.node_size`, so existing custom themes remain
compatible.

### Node `kind`

Selects a style from the active theme.

Built-in node kinds are:

```text
component
service
runtime
integration
storage
platform
external
```

A kind is not a hard-coded semantic category. It is looked up in the active
theme. A custom theme can define project-neutral additional kinds if required.

### Node `group`

Optional reference to an existing group ID.

The validator rejects references to a missing group.

### Node `note`

Optional source metadata. The current renderer accepts this field but does not
render it inside the node.

---

## `edges`

Edges are directed connections between nodes.

Minimal form:

```yaml
edges:
  - from: client
    to: service
```

Both IDs must reference existing nodes.

Optional fields:

```text
label
kind
dashed
from_anchor
to_anchor
route
```

### `label`

Optional label drawn along the longest edge segment.

```yaml
label: request
```

### `kind`

The schema currently accepts a string and defaults it to `dependency`.

The current SVG/draw.io renderer does not yet vary edge styling by `kind`; treat
it as semantic metadata for now rather than a visual style switch.

### `dashed`

Use a dashed connection:

```yaml
dashed: true
```

The default is `false`.

---

## Automatic orthogonal routing

With only `from` and `to`, the renderer automatically chooses source and target
box sides and creates an orthogonal polyline:

```yaml
edges:
  - from: client
    to: service
```

This is the preferred starting point. Add routing hints only when automatic
routing produces crossings/overlaps or when the diagram needs deliberately stable
entry/exit points.

Automatic routing uses node geometry and relative positions. It is deterministic,
but it is intentionally a small router rather than a global graph-layout solver.

---

## Explicit anchors

Use `from_anchor` and/or `to_anchor` to select exactly where an edge leaves or
enters a node.

Example:

```yaml
from_anchor:
  side: right
  position: 0.35

to_anchor:
  side: left
  position: 0.50
```

Supported sides:

```text
top
right
bottom
left
```

`position` is optional and ranges from `0` to `1`. The default is `0.5`.

Interpretation:

- top/bottom: `0` is the left edge, `1` the right edge;
- left/right: `0` is the top edge, `1` the bottom edge.

Examples:

```text
{side: right, position: 0.0}   top-right corner
{side: right, position: 0.5}   middle of right side
{side: right, position: 1.0}   bottom-right corner
```

You may specify only one end; the other end is inferred automatically.

---

## Explicit route waypoints

Use `route` when the connection must pass through specific canvas points.

Example:

```yaml
edges:
  - from: api
    to: worker
    from_anchor: {side: right, position: 0.35}
    to_anchor: {side: left, position: 0.50}
    route:
      - {x: 360, y: 171}
      - {x: 360, y: 110}
      - {x: 540, y: 110}
      - {x: 540, y: 170}
```

Each point has required numeric `x` and `y` coordinates.

The renderer connects the source node orthogonally to the first waypoint, follows
the supplied route, then connects the last waypoint orthogonally to the target.

Consecutive duplicate/collinear points may be simplified by the SVG renderer.
The draw.io output retains the explicit route points as editable waypoints.

Use explicit routes sparingly. They are useful for:

- avoiding a central box;
- keeping parallel flows separated;
- forcing a connection above/below a group;
- stabilizing a carefully reviewed architecture view.

`examples/routed-flow.yaml` demonstrates anchors plus waypoints.

---

## Themes and `kind`

The built-in theme lives at:

```text
src/eng_docs/themes/default.yaml
```

Current built-in styles:

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

A group/node `kind` must exist in the active theme. Otherwise validation fails.

The built-in theme also defines:

```text
font family/sizes
canvas background/text/edge colors
edge-label background
fill/stroke colors per kind
```

### Custom theme

Pass a different theme file:

```text
eng-docs diagrams \
  --source docs/_diagrams \
  --out bld/docs/architecture \
  --theme docs/_diagrams/theme.yaml
```

A custom theme is a complete renderer input, not a partial overlay. It should
provide the font/canvas fields used by the renderer and every `kind` referenced by
the source diagrams.

Keep project-specific visual policy in the consuming repository when it is not
generic enough to belong in the built-in theme.

---

## Custom schema

The built-in schema is used automatically.

A different compatible JSON Schema can be supplied with:

```text
eng-docs diagrams \
  --source docs/_diagrams \
  --out bld/docs/architecture \
  --schema path/to/diagram.schema.json
```

This option is primarily intended for controlled extension/qualification. If a
consumer requires a reusable schema change, prefer contributing that change to
`tool.eng-docs` rather than maintaining a permanently divergent private schema.

Schema validation does not replace the additional semantic checks performed by
`tool.eng-docs` for IDs/references/theme kinds.

---

## Validation

The command fails with a non-zero exit code when a source is invalid.

Validation happens in two layers.

### JSON Schema validation

Examples of schema errors:

- missing required `diagram`, `groups`, `nodes` or `edges`;
- unknown fields;
- invalid `diagram.id`;
- canvas too small;
- missing node/group properties;
- non-positive layout width/height;
- unsupported anchor side;
- anchor position outside `0..1`;
- malformed route point.

The error includes the YAML field path where possible.

### Semantic validation

Additional checks include:

- duplicate group IDs;
- duplicate node IDs;
- one ID reused as both group and node;
- unknown group/node `kind` in the selected theme;
- node referencing a missing group;
- edge referencing a missing node.

Example failure shape:

```text
path/to/file.yaml: edge references missing node: api -> missing-service
```

---

## Common mistakes

### Source filename and output name differ

Output is based on `diagram.id`, not the YAML filename.

```text
source: architecture-v2.yaml
diagram.id: system-overview
output: system-overview.svg / system-overview.drawio
```

Use stable IDs deliberately.

### Forgetting empty arrays

This is invalid:

```yaml
diagram: ...
nodes: ...
```

because `groups` and `edges` are required top-level keys.

Use:

```yaml
groups: []
edges: []
```

when they are empty.

### Using a `kind` not present in the theme

Kinds are theme keys. Adding this to YAML:

```yaml
kind: database
```

does not automatically create a style. Add `database` to the selected theme or
use an existing kind such as `storage`.

### Expecting `group` to make coordinates relative

Node layout remains absolute canvas layout. Group membership is semantic/visual;
it does not create a nested coordinate system.

### Overusing manual routes

Start with automatic routing. Add anchors, then waypoints only where needed. A
large number of manual route points makes later layout changes more expensive.

---

## Recommended authoring workflow

A practical sequence is:

1. choose a stable `diagram.id` and canvas size;
2. place major groups;
3. place nodes with explicit rectangles;
4. add edges using automatic routing;
5. render SVG/draw.io;
6. add explicit anchors to fix edge entry/exit placement;
7. add waypoints only for remaining crossings/overlaps;
8. keep labels short enough to remain readable;
9. review the generated SVG visually;
10. optionally open the `.drawio` output for interactive inspection/editing.

The YAML remains the authoritative reproducible source even when draw.io is used
for inspection or one-off manual exploration.

---

## Project integration pattern

A consuming repository can keep diagram sources separate from Markdown:

```text
docs/
  architecture.md
  _diagrams/
    system-overview.yaml
    runtime-view.yaml
```

Generate them with:

```text
eng-docs diagrams --source docs/_diagrams --out bld/docs/architecture
```

The narrative document can then reference the generated SVG through the
consumer's publication convention.

The diagram YAML is producer source; the Markdown is narrative source. Keeping
those responsibilities separate is intentional.

---

## Examples in this repository

User-facing examples live under `examples/`:

```text
examples/minimal-flow.yaml
examples/routed-flow.yaml
```

They are covered by tests so they remain valid/renderable as the implementation
evolves.

The files under `tests/fixtures/` are conformance/stress fixtures and may be more
specialized than a normal starting example.
