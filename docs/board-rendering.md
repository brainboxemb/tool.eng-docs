# Detail-board rendering

`BoardView` is a presentation-only model for compact A4 portrait detail boards.
It complements `RoadmapView`: the consumer keeps its planning/domain model and
maps only the information needed for a printable board.

```text
consumer-owned planning/domain model
        |
        | consumer-owned adapter
        v
BoardView YAML
        |
        v
eng-docs board
        |
        +--> SVG
        +--> printable PDF
```

## Source model

```yaml
board:
  marker: "4"
  title: Engineering detail board

  meta:
    - ACTIVE
    - forecast 18 Oct
    - orig ~3d · rem ~2d

  summary:
    heading: PURPOSE
    text: Explain the board in normal readable body text, separately from compact metadata.

  sections:
    - heading: END DEMO
      bullets:
        - Connect a sample client.
        - Inspect one generated result.

  badge_section:
    heading: DOCUMENTATION
    badges:
      - {label: SPEC R-70, tone: warning}
      - {label: TEST W-60, tone: active}

  groups:
    - heading: Application / product
      tone: success
      cards:
        - id: A01
          title: Implement one deterministic path
          state: {label: ACTIVE, tone: active}
          meta:
            - ~1d · after D02

  trailing_sections:
    - heading: PLANNING CHANGES
      bullets:
        - 2026-09-30 — narrowed the first slice.
```

The optional `marker` is a compact visible identifier placed at the upper right.
The optional `summary` gives descriptive prose its own heading and normal body
typography rather than forcing it into the small metadata line.

All identifiers, headings, state labels, tones and metadata are presentation data.
The renderer does not assign semantics to concepts such as an activity, lane,
document or planning change.

## Print-friendly style

BoardView and RoadmapView share the same presentation palette and neutral visual
primitives:

- white page and white cards;
- thin neutral borders and section rules;
- large colored background areas are avoided;
- color is reserved mainly for compact state chips and small accents;
- section rules start after the rendered heading text rather than crossing it;
- cards grow with wrapped title/metadata instead of clipping content;
- three cards are used per row on A4 portrait.

The first implementation keeps one BoardView on one portrait A4 page. If the
consumer-produced view cannot fit even after card growth, rendering fails with an
explicit presentation-size error instead of clipping or ellipsizing content.

## CLI

```text
eng-docs board --source <board-view.yaml> --out <directory>
```

Generated output:

```text
<out>/
  board.svg
  board.pdf
```

## Ownership boundary

`tool.eng-docs` owns:

- BoardView schema/validation;
- generic A4 portrait layout;
- shared print-friendly presentation style;
- SVG/PDF rendering;
- deterministic output;
- domain-neutral examples/tests.

Consumers own:

- authoritative planning/domain data;
- the adapter into BoardView;
- group/lane meaning;
- card/activity meaning;
- state and document workflow semantics;
- publication/orchestration.
