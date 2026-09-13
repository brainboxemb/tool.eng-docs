# Document assembly prototype

Status: development capability for `0.2.0.dev0`; the current released version remains `v0.1.1` and only guarantees the diagram capability.

`eng-docs assemble` builds a self-contained review/publication tree from ordinary Markdown plus assets that have already been produced by their owning tools. It deliberately does **not** run OpenSCAD, Maven, verification, diagram generation or any other producer.

The intended boundary is:

```text
producer/tool -> files + asset manifest ----\
producer/tool -> files + asset manifest -----+-> eng-docs assemble -> self-contained docs tree
source Markdown ----------------------------/
```

## Why manifests exist

Different producers already own different execution semantics. A SCAD build, a diagram renderer and a Java verification job should not be forced into one build engine merely so documentation can link to their outputs.

A manifest therefore describes an already-produced output tree using domain-neutral metadata:

- stable asset ID;
- MIME-like asset kind;
- lifecycle: `build`, `design-doc`, `verification` or `docs`;
- document relationship: `generate-inline`, `producer-source`, `reference-existing` or `reference-evidence`;
- relative artifact path;
- producer identity/version;
- exact source revision/provenance.

The schemas are:

```text
src/eng_docs/schemas/asset-manifest.schema.json
src/eng_docs/schemas/assembly.schema.json
```

They are machine-readable validation contracts. This guide remains the human-facing explanation.

## Step 1 — describe existing producer output

Suppose another tool has already generated:

```text
bld/architecture/
  system.svg
```

Create a manifest without rebuilding the asset:

```bash
eng-docs manifest \
  --source bld/architecture \
  --out bld/architecture/assets.yml \
  --producer project.architecture-diagrams \
  --producer-version 1.0.0 \
  --source-revision "$GITHUB_SHA" \
  --lifecycle docs \
  --relationship producer-source \
  --include '*.svg'
```

`manifest` recursively inventories matching files. It does not modify or execute the producer.

For an already-built product render use `--lifecycle build --relationship reference-existing`. For verification evidence use `--lifecycle verification --relationship reference-evidence`.

## Step 2 — declare document assembly

Example `assembly.yml`:

```yaml
schema_version: 1

asset_manifests:
  - path: bld/architecture/assets.yml
    publish_prefix: assets/architecture

documents:
  - id: architecture
    source: docs/architecture.md
    output: documents/architecture.md

indexes:
  - output: documents/README.md
    title: Generated documents
    sections:
      - title: Architecture
        items:
          - document: architecture

books:
  - output: documents/architecture-book.md
    title: Architecture book
    description: Combined review copy.
    documents:
      - architecture
```

Then assemble:

```bash
eng-docs assemble --root . --config assembly.yml --out bld/docs
```

The source Markdown remains authoritative and is not modified.

## Link localisation

Source documents should remain readable directly on GitHub. They do not need an `asset://`-only syntax.

If a normal inline Markdown link resolves to an asset from one of the input manifests, only the generated copy is rewritten to the local assembled path. For example a source link such as:

```markdown
![System](../../../raw/prod/docs/assets/architecture/system.svg)
```

can become in `bld/docs/documents/architecture.md`:

```markdown
![System](../assets/architecture/system.svg)
```

Unknown links remain unchanged. Inline code and fenced code blocks are not rewritten.

The current prototype handles ordinary inline Markdown links/images. Reference-style links and more advanced Markdown constructs should be added only when a real qualification consumer demonstrates the need.

## Indexes and books

`indexes` provide ordered navigation without hardcoding project document names in `tool.eng-docs`.

`books` concatenate selected documents into one review copy. The original generated document remains separately available, and headings are shifted only in the combined book.

These are assembly operations, not document-authoring semantics. The consuming repository still decides which documents belong in which index/book and in what order.

## Qualification boundary

This capability is not considered release-ready merely because the generic tests pass. Before a feature release it must prove the same core contract against:

1. the software engineering document set in `2026-010-01.meta.event-timing-software`;
2. a current SCAD reference consumer without replacing its existing SCAD render authoring;
3. a cross-domain manifest check using the Java reference consumer evidence tree, without adding Java/Maven/Surefire fields to the generic schema.

Only after those checks should `project.docs.yml`, native producer manifests, verification evidence bundles or broader Markdown syntax be considered.
