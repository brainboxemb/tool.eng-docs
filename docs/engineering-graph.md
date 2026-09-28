# Engineering graph authoring and review

The engineering-graph capability turns small, project-owned metadata fragments
inside normal Markdown and declarative diagram sources into a normalized graph
and a human review view.

The tool owns extraction, validation and generated views. The consuming project
owns object IDs, object types, relation names and engineering meaning.

## Authoring model

Normal Markdown remains the readable engineering source.

A graph-exposed Markdown object uses an explicit stable anchor followed by one
hidden `eng` metadata comment:

```md
<a id="REQ-1"></a>
**REQ-1 — Service response**

<!-- eng {"type":"requirement","relations":{"derived_from":["GOAL-1"]}} -->

The system shall provide a response through the service boundary.
```

The metadata is hidden in normal rendered Markdown but stays adjacent to the
object it describes.

Relationships are authored at the object that owns them. A project can therefore
follow its normal engineering flow, for example:

```text
requirement  --derived_from--> upstream requirement/use case
design       --satisfies-----> requirement
verification --verifies------> requirement
```

The relation names above are examples. They are not hard-coded by
`tool.eng-docs`.

## Diagram engineering identity

Declarative diagram nodes may already carry an engineering `object_id`:

```yaml
nodes:
  - id: service
    object_id: Service
    label: Service
    kind: service
    layout: {x: 290, y: 150, w: 180, h: 60}
```

The graph extractor imports that object identity directly. A project should not
create a second Markdown object merely to repeat the same identity.

When design text owns relations for an existing diagram object, use an
`eng-rel` extension beside that design text:

```md
<!-- eng-rel {"id":"Service","relations":{"satisfies":["REQ-1"]}} -->

The Service design owns the implementation responsibility for REQ-1.
```

The extension adds relations to the already-defined object. It does not define a
second `Service`.

## Consumer-owned graph model

An optional YAML model can constrain object and relation types without embedding
project semantics in the reusable tool.

Example:

```yaml
schema_version: 1
diagram_object_type: design

object_types:
  - goal
  - requirement
  - design
  - verification

relations:
  derived_from:
    from: [requirement]
    to: [goal, requirement]
  satisfies:
    from: [design]
    to: [requirement]
  verifies:
    from: [verification]
    to: [requirement]
```

With a model supplied, extraction fails when:

- an object uses an undeclared type;
- a relation name is undeclared;
- a relation source type is not allowed;
- a relation target type is not allowed.

The model is optional. Duplicate IDs and unknown owners/targets are always
validated.

## CLI

Generate normalized JSON and a human review:

```text
eng-docs graph \
  --root . \
  --docs examples/graph/docs \
  --diagrams examples/graph/diagrams \
  --model examples/graph/model.yml \
  --out bld/engineering-graph.json \
  --review bld/engineering-graph-review.md \
  --source-revision <exact-source-revision>
```

`--diagrams`, `--model` and `--review` are optional. `--docs`, `--out`
and `--source-revision` are required.

Source paths stored in the graph are relative to `--root` where possible.

## Human review view

The generated review intentionally makes hidden authoring visible.

For every engineering object it shows:

1. **Authored input** — the exact `eng`, `eng-rel` or diagram
   `object_id` source;
2. **Authored outgoing** — normalized relations owned by that object;
3. **Generated incoming** — inverse context derived from other objects.

For a requirement the result can therefore read conceptually as:

```text
REQ-1

Authored outgoing
  derived_from -> GOAL-1

Generated incoming
  satisfies <- Service
  verifies  <- VC-1
```

Only the outgoing relations are authored. The incoming view is derived and must
not be maintained separately.

## Validation boundary

The first reusable boundary intentionally validates a small contract:

- stable Markdown anchors for `eng` objects;
- unique engineering IDs across Markdown and diagram nodes;
- valid JSON metadata;
- relation targets that exist;
- `eng-rel` owners that already exist;
- optional consumer-owned type compatibility;
- deterministic normalized JSON and Markdown review output.

It does not mutate source Markdown, generate a portal, depend on Sphinx-Needs or
own project-specific traceability policy.

See `examples/graph/` for the executable domain-neutral example.
