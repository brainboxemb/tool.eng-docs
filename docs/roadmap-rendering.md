# Roadmap rendering

This capability renders a **presentation view** of project planning. It does not
parse or own a project's planning model.

The reusable boundary is:

```text
authoritative project planning
        |
        | consumer-owned adapter
        v
RoadmapView YAML
        |
        v
eng-docs roadmap
        |
        +--> SVG
        +--> printable PDF
```

A consuming repository remains responsible for deciding which project concepts
become roadmap items, section headings, state labels, metadata and badges.

## Source model

The roadmap source is deliberately presentation-oriented and domain-neutral.

```yaml
roadmap:
  title: Engineering roadmap
  subtitle: Optional context

  items:
    - id: phase-2
      title: Integrate service

      state:
        label: ACTIVE
        tone: active

      meta:
        - "~3d"
        - "forecast Oct"

      sections:
        - heading: RESULT
          bullets:
            - Public boundary is usable.
            - Consumer remains source of truth.

        - heading: DEMO
          bullets:
            - Connect a sample client.
            - Inspect one generated result.

      badges:
        - label: SPEC
          tone: mature
```

The renderer treats identifiers, headings and labels as opaque presentation data.
It does not assign semantics to values such as `ACTIVE`, `RESULT`, `DEMO`
or `SPEC`.

## Layout contract

The renderer must:

- wrap text predictably;
- never silently clip or ellipsize supplied content;
- expand card height and/or paginate when content grows;
- keep all supplied item sections and badges visible;
- fail only for structurally invalid RoadmapView input or an unsupported
  presentation shape, not because authoritative project prose happened to grow.

A consumer may deliberately generate concise roadmap wording. That compact view
is separate from the authoritative planning text.

## CLI

The intended command is:

```text
eng-docs roadmap --source <roadmap-view.yaml> --out <directory>
```

The same command is used locally and in CI.

## Ownership boundary

`tool.eng-docs` owns:

- RoadmapView schema/validation;
- generic layout/pagination;
- SVG/PDF rendering;
- deterministic output;
- domain-neutral examples/tests.

Consuming repositories own:

- authoritative planning;
- the adapter into RoadmapView;
- project-specific status/estimate/document semantics;
- publication/orchestration.

## Generated output

The command writes:

```text
<out>/
  roadmap.svg
  roadmap.pdf
  roadmap/
    roadmap-page-01.svg
    roadmap-page-02.svg
    ...
```

The renderer first tries three columns, then two, then one when wrapped card
content requires more width or height. Rows paginate across A4 landscape pages.
A presentation item fails only if it cannot fit on one full-width page; that
error applies to the compact RoadmapView, not to the consumer's authoritative
planning source.
