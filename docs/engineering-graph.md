# Engineering graph normalization and review

The engineering-graph capability consumes an existing Sphinx-Needs
`needs.json` export and turns the selected outgoing relation fields into a
small deterministic BrainboxEmb graph plus a human review view.

`tool.eng-docs` does **not** own the engineering authoring syntax. Native
MyST/Sphinx-Needs owns graph-exposed engineering objects, IDs, relation
authoring and typed relation validation.

## Source boundary

A consuming project authors graph-exposed objects as normal MyST/Sphinx-Needs
directives, for example:

```md
```{req} Service response
:id: REQ-1
:derived_from: GOAL-1

The system shall provide a response through the service boundary.
```
```

The relation is authored at the object that owns it.

A typical engineering flow can therefore be:

```text
requirement  --derived_from--> upstream requirement/use case
design       --satisfies-----> requirement
verification --verifies------> requirement
```

The relation names above are examples. They are consumer-owned and configured in
Sphinx-Needs; `tool.eng-docs` does not hard-code them.

Sphinx-Needs then provides:

- stable object IDs;
- typed objects;
- typed outgoing relation validation;
- generated inverse/backlinks;
- reader-facing object anchors;
- machine-readable `needs.json`.

The `needs.json` export is the input boundary for `eng-docs graph`.

## Diagram engineering identity

Declarative diagram nodes may carry an engineering `object_id`:

```yaml
nodes:
  - id: service
    object_id: Service
    label: Service
    kind: service
    layout: {x: 290, y: 150, w: 180, h: 60}
```

The diagram does **not** define a second engineering object.

The design/Need with ID `Service` owns the engineering object. The diagram
`object_id` references that existing object for navigation and cross-view
identity.

When `--diagrams` is supplied, `eng-docs graph` validates every diagram
`object_id` against the Needs graph and records the diagram reference on the
normalized object. An unresolved diagram ID fails the command.

## CLI

Generate normalized JSON and an optional human review:

```text
eng-docs graph \
  --needs bld/needs/needs.json \
  --relation derived_from \
  --relation satisfies \
  --relation verifies \
  --diagrams docs/_diagrams \
  --out bld/engineering-graph.json \
  --review bld/engineering-graph-review.md \
  --source-revision <exact-source-revision>
```

`--relation` may be repeated. Only those outgoing relation fields are
normalized into the BrainboxEmb graph.

`--diagrams` and `--review` are optional.

`--needs`, `--out` and `--source-revision` are required.

## Normalized graph

The normalized graph retains:

- exact source revision supplied by the consuming build;
- Sphinx-Needs project/version provenance;
- object ID;
- Need type and human type name;
- title;
- source document/line from the Needs export;
- content;
- zero or more diagram references;
- explicitly selected outgoing relations.

Incoming/backlink context is derived from the normalized outgoing relations and
is not stored as a second authored relation set.

The output is validated against:

```text
src/eng_docs/schemas/engineering-graph.schema.json
```

## Human review

The generated Markdown review shows, for every object:

1. source identity from Sphinx-Needs;
2. **Authored outgoing** relations;
3. **Generated incoming** relations;
4. diagram references.

For a requirement the review can therefore read conceptually as:

```text
REQ-1

Authored outgoing
  derived_from -> GOAL-1

Generated incoming
  satisfies <- Service
  verifies  <- VC-1

Diagram references
  none
```

The review is derived from `needs.json`. It does not parse or reproduce a
second custom Markdown metadata language.

## Validation ownership

Sphinx-Needs remains responsible for authoring-level rules such as:

- valid Need IDs;
- project-specific Need types;
- allowed relation names;
- allowed source/target type combinations;
- ordinary backlink generation.

`tool.eng-docs` adds only the reusable post-export checks needed by its
derived views:

- valid Sphinx-Needs export structure;
- embedded Need ID consistency;
- selected relation fields must contain lists of IDs;
- selected relation targets must exist;
- diagram `object_id` values must resolve to existing Needs;
- deterministic normalized graph/review output.

This keeps project semantics in the consuming repository while avoiding a
second authoring parser.

## Runtime dependency boundary

`eng-docs graph` consumes JSON and therefore does not need Sphinx-Needs as a
runtime dependency.

The consuming documentation build runs Sphinx-Needs first and passes its export
to `tool.eng-docs` only when a normalized BrainboxEmb graph, diagram
cross-validation or another derived view is required.

See `examples/graph/` for the domain-neutral source, Needs export and diagram
reference example.
