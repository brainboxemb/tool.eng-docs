# Declarative diagram authoring

This guide documents the current user-facing YAML contract for
`eng-docs diagrams`.

The diagram source model is intentionally small and supports two diagram types:

- **structure** diagrams — groups, nodes, directed edges and optional routing hints;
- **sequence** diagrams — ordered participants and ordered messages.

Both use the same canvas metadata, theme, validation command and output pipeline.

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

Every source has a required `diagram` block.

A structural diagram uses the existing form:

```yaml
diagram: {}
groups: []
nodes: []
edges: []
```

When `diagram.type` is omitted it defaults semantically to `structure`, so all
existing sources remain valid.

A sequence diagram uses:

```yaml
diagram:
  type: sequence
participants: []
messages: []
```

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
  type: structure   # or sequence; omitted means structure
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

## Sequence diagrams

Use `type: sequence` when interaction order over time is the primary concern.
Sequence diagrams use automatic horizontal participant placement and automatic
vertical message placement; authors specify semantic order rather than canvas
coordinates for every message.

Example:

```yaml
diagram:
  id: request-flow
  type: sequence
  title: Request flow
  width: 1000
  height: 620

participants:
  - id: client
    label: Client
    kind: external
  - id: queue
    label: Queue
    kind: integration
  - id: worker
    label: Worker
    kind: service

messages:
  - from: client
    to: queue
    label: submit
    kind: async
  - from: queue
    to: worker
    label: next item
    kind: async
  - from: worker
    to: client
    label: result
    kind: return
```

The renderer creates UML lifelines, activation bars and messages in source order
from top to bottom. The draw.io output uses native `umlLifeline` participant
shapes plus editable activation-bar child cells; SVG uses the same
lifeline/activation geometry. The same source therefore remains deterministic
while opening as an editable UML sequence diagram in draw.io.

### `participants`

A sequence diagram requires at least two participants.

Each participant has:

```yaml
- id: worker
  label: Worker
  kind: service
```

`id` is local diagram identity and must be unique. `kind` selects a normal
theme style, so sequence diagrams use the same visual vocabulary as structural
diagrams.

### `messages`

A sequence diagram requires at least one message.

```yaml
- from: client
  to: worker
  label: request
  kind: call
```

Supported first-slice message kinds are:

```text
call    synchronous/normal call; solid line + filled arrow
async   asynchronous hand-off; solid line + open arrow
return  return/result; dashed line + open arrow
```

`kind` defaults semantically to `call` when omitted.

Synchronous `call` messages start an activation on the target. A matching
`return` from that target to the caller closes the most recent matching
activation. When a high-level diagram omits a routine return, the activation
extends through that participant's remaining interaction.

A message may also target the same participant:

```yaml
- from: worker
  to: worker
  label: process queued work
  kind: call
```

That is rendered as a UML self-call and is useful for showing internal processing
without inventing another architectural participant. Asynchronous messages use
an open arrow and do not by themselves create an activation bar.

Sequence message labels use a compact 13 px text size. Long labels are wrapped
automatically to the horizontal space available between their participants; only
that message row grows when an extra line is needed. Explicit line breaks in the
source label are also preserved. This keeps short interaction diagrams compact
without forcing authors to abbreviate useful transition text.

Both `from` and `to` must reference existing participants. UML interaction
fragments such as `alt`, `loop` and `par`, plus destruction markers, remain
deferred until a real consumer requires them.

Sequence diagrams are intended for interaction/process views. Use the structural
source model for component/layer topology and routing-heavy architecture views.

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

Optional fields:

```text
note
properties
properties_width
object_id
notation
outline
label_offset
```

### Group `id`

Group IDs:

- may contain letters, digits, `_`, `.`, and `-`;
- must be unique among groups;
- may not reuse a node ID.

### Group `label`

Rendered heading for the visual group.

### Group `note`

Optional compact secondary text rendered directly below the group heading. Use it
for a small amount of identity/state context that belongs to the semantic
container itself, not for a second nested component model.

Newlines are supported.

### Group `properties`

Use `properties` for compact identity/state concepts owned by a semantic
component group when those concepts should read as part of the component rather
than as commentary:

```yaml
properties:
  - aggregateId
  - locationId
  - state
```

SVG renders these values in a small neutral inner box beneath the group heading,
using a simple left-aligned dash list with no stereotype, component glyph or
secondary title. Editable draw.io output preserves the same light inner box. The values are architecture-view properties; they do not
declare exact implementation fields or turn the group into a UML class.

Use `note` for explanatory secondary text. Use `properties` when the text is
part of the semantic identity/state of the enclosing component.

The property block normally sizes itself from its content. Use
`properties_width` only when the block should align to a deliberate diagram
column:

```yaml
properties_width: 240
```

The value is an explicit positive width in diagram units/pixels. Omitting it
keeps the automatic sizing behaviour.

### Group `object_id`

A group may carry the same project-owned engineering `object_id` as a node when
the enclosing component/container is itself the stable engineering object.

When present, SVG wraps the complete rendered group with
`data-engineering-id="<object_id>"`, editable draw.io stores the same metadata on
the group cell, and engineering-graph normalization records the group as a
diagram reference. Plain visual layers should omit `object_id`.

By default the heading keeps the established inset from the layout box's
upper-left corner. Shaped groups may move that heading further right/down
without changing the group's bounding box:

```yaml
label_offset: {x: 0, y: 45}
```

Both values are non-negative diagram units/pixels and are added to the default
heading inset. SVG and editable draw.io output apply the same offset semantics.
This is especially useful when a polygon's bounding-box upper-left lies outside
the visible filled area.

### Group `outline`

By default a group is rendered as the existing rounded rectangle described by
`layout`. A group may instead define one closed polygon outline while keeping
that same rectangular layout as its bounding box:

```yaml
groups:
  - id: upper-area
    label: Upper responsibility
    kind: group-primary
    layout: {x: 70, y: 85, w: 760, h: 190}
    outline:
      corner_radius: 10
      points:
        - {x: 0.0, y: 0.0}
        - {x: 1.0, y: 0.0}
        - {x: 1.0, y: 1.0}
        - {x: 0.62, y: 1.0}
        - {x: 0.62, y: 0.76}
        - {x: 0.0, y: 0.76}
```

Outline coordinates are normalized relative to the layout box: `0,0` is its
upper-left and `1,1` its lower-right. At least three distinct points are
required and all coordinates must remain in the inclusive `0..1` range. Do
not repeat the first point at the end; the renderer closes the polygon.

Use optional `corner_radius` to round custom-outline vertices in diagram units:

```yaml
outline:
  corner_radius: 10
  points:
    # ...
```

Omitting `corner_radius`, or setting it to `0`, preserves the existing sharp
polygon vertices. Positive values round each vertex while retaining the authored
polygon geometry and sloped/stepped boundary.

SVG and draw.io use the same polygon. The draw.io representation remains a
native editable polygon (`mxgraph.basic.polygon`), not an embedded image.
Group titles and edge routing still use the rectangular `layout` bounding box.
Keep the title area inside the polygon and use explicit edge anchors when a
non-rectangular boundary makes the default bounding-box anchor visually
ambiguous.

Polygon outlines currently apply to groups only and cannot be combined with
`notation`; component/class notation remains rectangular.

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

Groups may also be used directly as edge `from` or `to` endpoints. Anchors
then attach to the group boundary just as they do to a node boundary. This is
preferable to inventing a component-level dependency in a high-level view when
only the layer relationship is established.

### Group `notation`

A group is normally a plain visual layer/container and has no semantic glyph.
Use `notation: packaging-component` only when the enclosing box is itself a
software packaging component, not merely because it is an architecture layer.

```yaml
notation: packaging-component
```

The SVG uses a compact integrated packaging-component glyph: the package/folder
tab sits at the upper-left, while the UML component tabs cross the left edge of
the same body. It does not draw a second complete component rectangle inside the
package.
This matches the semantics of a component that behaves as a package/container.
draw.io keeps the element editable as a container/component.
Ordinary layers such as Presentation, Domain or I/O should normally remain plain
groups with no notation.

For backwards compatibility, `notation: component` on groups is still accepted.

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
object_id
group
subtitle
items
notation
note
```

### Node `id`

Node IDs:

- may contain letters, digits, `_`, `.`, and `-`;
- must be unique among nodes;
- may not reuse a group ID;
- are referenced by edge `from` and `to` fields.

### Engineering `object_id`

Use `object_id` when a diagram group, node or selected structured item represents
an engineering object that also exists outside the diagram.

```yaml
- id: service-card
  object_id: example.service
  label: Service
  kind: service
  layout: {x: 500, y: 150, w: 180, h: 60}
```

`id` and `object_id` have deliberately different responsibilities:

- group/node `id` is local diagram identity used by routing, grouping and edges;
- `object_id` is optional project-owned semantic identity used to connect
  generated output to other engineering-documentation views.

`object_id` is treated as an opaque non-empty string. The renderer does not
look it up in a requirements database or engineering graph.

When present on a node:

- SVG wraps the rendered node in an element carrying
  `data-engineering-id="<object_id>"`;
- editable draw.io output preserves the same
  `data-engineering-id` metadata on the node cell.

Object-form structured items may carry the same optional field:

```yaml
items:
  - label: Worker
    object_id: example.worker
  - label: Workers
    items:
      - label: Primary
        object_id: example.worker.primary
```

For an identified item, SVG wraps that rendered row with the same
`data-engineering-id` attribute. Draw.io preserves the identity on the row's
embedded HTML inside the editable parent node. Strings remain display-only
items and cannot carry identity.

`object_id` values must be unique across groups, nodes and nested items in one
diagram because duplicate semantic identity would make interactive selection
ambiguous. Do not use a second label-to-object lookup table when the diagram
source itself can declare the identity.

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

### Node `items`

Use `items` when a node represents a small structured list or tree rather than
a single explanatory subtitle. Items are rendered left-aligned beneath the node
label (and optional subtitle).

Leaf items may be strings:

```yaml
items:
  - Reader
  - Display
  - Keypad
```

Nested items use an object with `label`, optional `object_id`, and optional child `items`:

```yaml
items:
  - Browser
  - label: Terminals
    items:
      - Local
      - Remote
```

The renderer shows top-level entries as bullets and nested entries as indented
tree rows. Keep this structure small; a large hierarchy normally deserves its
own detail diagram.

### Node `notation`

Use the optional `notation` field when a node needs standard semantic notation
independent of its theme/color `kind`.

For a concrete modular software component:

```yaml
notation: component
```

This adds the UML component glyph in SVG and uses the native component shape in
draw.io.

For a class/type whose identity or state is relevant to the architecture view:

```yaml
notation: class
items:
  - id
  - state
```

The class uses a compact UML class-style box: a small `«class»` stereotype,
the class name, a separator, and a short property list. Keep the box compact in
high-level architecture views; it does not need to span the width of the
containing component.

A packaging component can be either a group that geometrically contains child
nodes or a node that summarizes a contained hierarchy:

```yaml
notation: packaging-component
```

Use it for the actual packaging component, not for the surrounding architecture
layer.

`kind` continues to select theme styling. `notation` is deliberately
orthogonal to that styling choice.

### UI wireframe notation

Use wireframe notation when a structural diagram is describing the intended
layout and interaction surface of a UI rather than software topology. The same
YAML still produces both reader-facing SVG and native editable draw.io output.

Supported first-slice node notations are:

```text
wireframe-panel
wireframe-tabs
wireframe-input
wireframe-button
wireframe-table
wireframe-status
```

Example:

```yaml
nodes:
  - id: location
    label: Location
    subtitle: "24"
    kind: external
    notation: wireframe-input
    layout: {x: 90, y: 205, w: 220, h: 72}

  - id: apply
    label: Apply
    kind: component
    notation: wireframe-button
    layout: {x: 330, y: 230, w: 110, h: 38}
```

The notation controls the UI-control shape and text placement. `kind` still
selects theme fill/stroke, which lets a consuming repository use its theme to
show selected, disabled or warning states without putting application-specific
state names into this reusable schema.

Conventions:

- `wireframe-panel`: a top-aligned section/container; optional `subtitle` and
  `items` describe compact secondary content;
- `wireframe-tabs`: use `|`-separated labels in `label`; optional
  `subtitle` selects the matching tab, otherwise the first tab is selected;
- `wireframe-input`: `label` is the field name and optional `subtitle` is
  the shown value/placeholder;
- `wireframe-button`: centered action label;
- `wireframe-table`: `label` is the table title and `items` are plain row
  strings; keep columns compact because this is a wireframe, not a data-grid
  renderer;
- `wireframe-status`: compact pill/badge for connection or UI state.

Wireframe nodes are deliberately mid-fidelity. They document layout, control
availability and state presentation without hard-coding a frontend toolkit or
production visual design into engineering documentation.

See `examples/ui-wireframe.yaml` for a complete domain-neutral example.

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

Edges are directed connections between diagram endpoints. An endpoint may be a
node or a visual group/layer.

Minimal form:

```yaml
edges:
  - from: client
    to: service
```

Both IDs must reference an existing node or group. Referencing a group is useful
for high-level architecture where the relationship is known to cross a layer
boundary but the concrete component dependency has intentionally not been fixed.

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

Automatic routing uses endpoint geometry and relative positions. For
node-to-node edges, the renderer also detects when the normal orthogonal path
would cross another node and deterministically detours around that intermediate
component with a small clearance. The same generated detour is emitted as native
editable draw.io waypoints, so SVG and draw.io preserve the same reviewed route.

When two node endpoints belong to distinct, non-overlapping groups and their
resolved anchors face the gap between those groups, the router prefers the
whitespace corridor between the group boundaries. For vertically stacked groups
the horizontal middle segment is placed halfway through the vertical gap; for
side-by-side groups the vertical middle segment is placed halfway through the
horizontal gap. This keeps cross-layer relationships in the visual separation
already authored into the diagram instead of running long middle segments inside
one of the layers.

A preferred corridor is used only when its complete orthogonal path remains clear
of other nodes and unrelated groups (including routing clearance). If that
corridor is blocked, the normal deterministic obstacle-aware router remains the
fallback. An explicit `route:` always wins over automatic corridor selection.

Group endpoints themselves still use the existing rectangular boundary model
without global obstacle solving. Routing is intentionally a small deterministic
orthogonal router rather than a force-directed or full graph-layout engine:
component placement remains authoritative and is never moved automatically.
Prefer fewer high-level edges and group endpoints over forcing speculative
component-to-component arrows; use explicit anchors/routes only where the
relationship is concrete and the visual path still needs stabilising.

`examples/obstacle-routing.yaml` demonstrates automatic obstacle avoidance;
`examples/corridor-routing.yaml` demonstrates cross-layer corridor preference.
Neither example requires absolute route coordinates.

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

You may specify only one end; the other end is inferred automatically. The
opposite end uses the facing side (bottom -> top, right -> left, and vice versa)
and projects its position onto the authored anchor coordinate. This keeps
naturally aligned connections straight without requiring a second hand-tuned
fractional position.

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
- empty group/node/item `object_id`;
- non-positive layout width/height;
- unsupported anchor side;
- anchor position outside `0..1`;
- malformed route point;
- unsupported node `notation`.

The error includes the YAML field path where possible.

### Semantic validation

Additional checks include:

- duplicate group IDs;
- duplicate node IDs;
- duplicate diagram `object_id` values across groups, nodes and items;
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
