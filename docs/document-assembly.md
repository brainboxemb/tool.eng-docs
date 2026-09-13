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

By default a document is published as `documents/<source filename>`. In this example `docs/architecture.md` therefore becomes `documents/architecture.md`.

Use an explicit `output` only when the published location really differs from that default:

```yaml
documents:
  - id: architecture
    source: docs/architecture.md
    output: reference/architecture.md
```

The stable document `id` is what indexes and books reference. The numbered source filename may therefore change during a repository renumbering without forcing matching changes through every index and book declaration; normally only the document's `source` path changes. The assembler never renames or mutates authoritative source files itself.

Then assemble:

```bash
eng-docs assemble \
  --root . \
  --config assembly.yml \
  --out bld/docs \
  --source-repository "$GITHUB_REPOSITORY" \
  --source-revision "$GITHUB_SHA"
```

The source Markdown remains authoritative and is not modified.

Every CLI assembly writes `assembly-info.yml` at the assembled output root. It records:

- `tool.eng-docs` as assembler plus its exact package version;
- the source repository and exact source revision supplied by the caller;
- the assembly configuration path plus SHA-256 digest;
- every input asset manifest, its SHA-256 digest and its producer provenance.

The final publication namespace (`dev/pr-N/docs`, `prod/docs`, a release namespace, or another destination) is deliberately **not** stored as assembler policy. The repository/CI publication step owns that side effect and can record its own destination context. This keeps assembly cacheable and separate from publication.

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

## Qualification result

The Step-2.5 qualification has now exercised the same core contract against the two required real consumers plus the cross-domain Java guard.

### Consumer A — software engineering documents

`brainboxemb/2026-010-01.meta.event-timing-software` PR #36 uses the exact development tool revision from this PR through the repository's normal `project.yml` / gitlink dependency mechanism.

The latest qualification run on consumer head `9101da1ff77a6d97bfe42bf19f0ee7c58945d2d7` passed as workflow run `34760915037` and proved:

- existing diagram and planning producers remain independently owned;
- `eng-docs manifest` + `eng-docs assemble` replace generic project-local copy/link/index/book glue;
- authoritative source Markdown remains directly readable;
- generated output remains self-contained and publication-compatible;
- redundant per-document output filenames are unnecessary when the published filename follows the source filename;
- stable document IDs keep indexes/books independent of source-document numbering changes.

### Consumer B — current SCAD reference consumer

`brainboxemb/template.scad-project` PR #17 qualifies the same contract without replacing `scad-render`, OpenSCAD or `tool.scad-project` ownership.

The corrected qualification head `49d7807f5195e49c16612527bba3dc9b9fc7a196` passed Build #184, Verify #169 and Qualify document assembly #8. The qualification deliberately uses the normal repository dependency boundary: `tool.eng-docs` is declared in `project.yml`, pinned as `tools/tool.eng-docs`, and materialized by `bootstrap.sh` / `tool.git-project`. The workflow activates the already-managed local checkout rather than fetching the tool through a direct `git+https` pip URL.

The proof shows:

- document-local SCAD render authoring remains unchanged;
- already-generated design images and normal build PNGs are described through manifests and consumed without duplicate rendering;
- source-local Markdown can participate without moving;
- the assembler has no SCAD implementation dependency.

### Cross-domain Java manifest guard

The owner test suite also mirrors the actual generated publication layout from `template.java-project` / `tool.java-project`:

```text
README.md
source-sha.txt
artifacts/<runnable jar>
evidence/toolchain-build-provenance.txt
evidence/tests/README.md
evidence/tests/.../TEST-*.xml
```

The same generic manifest fields describe that tree. No Java, Maven or Surefire-specific schema fields are required.

## Configuration conclusion

The first two consumers do not justify a mandatory repository-wide `project.docs.yml`.

The smallest proven assembly configuration is the existing assembly input itself:

```text
asset manifest inputs + publish prefixes
documents: stable ID + source + optional exceptional output
optional ordered indexes
optional ordered books
```

The assembly output root plus source repository/revision are invocation/orchestration concerns (`--out`, `--source-repository`, `--source-revision`). Publication namespace selection such as `dev/pr-N/docs` versus `prod/docs` remains outside the assembler and belongs to the repository/CI orchestration layer.

This is intentionally smaller than the original provisional configuration list: the real consumers did not require a separate generic publication-context field in the assembly schema. Ordinary source links plus manifest publication paths were sufficient for localisation, while `assembly-info.yml` supplies generic materialization provenance.

## Ownership conclusion

The qualification supports keeping common assembly in `tool.eng-docs` rather than creating another repository:

- the implementation remains domain-neutral;
- dependencies stay small (`PyYAML`, `jsonschema` and the standard library for assembly mechanics);
- both full consumers use the same schemas/CLI contract;
- no SCAD, Java, Maven or verification implementation is imported;
- the capability fits the existing `eng-docs` subcommand/package structure.

A separate assembly repository should only be reconsidered if a materially independent dependency/release lifecycle or broader non-engineering scope appears later.

## Deferred work

Qualification does **not** authorize broadening the first slice. Keep deferred:

- mandatory `project.docs.yml` or other repository-global docs profile;
- native producer manifests where a project-local manifest adapter is already sufficient;
- verification evidence-bundle semantics beyond the current manifest relationship vocabulary;
- broader Markdown syntax such as reference-style link rewriting unless a real consumer requires it;
- producer scheduling inside `eng-docs assemble`;
- replacement of current SCAD `scad-render` authoring;
- moving source documents into one common folder layout.
