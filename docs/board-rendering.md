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
    - orig ~3d · rem ~2d
    - forecast end 18 Oct

  summary:
    heading: PURPOSE
    text: Explain the board in normal readable body text, separately from compact metadata.

  section_columns: 2
  sections:
    - heading: RESULT
      bullets:
        - Produce one observable result.
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
          header_meta:
            - ~1d
            - after D02

  trailing_sections:
    - heading: PLANNING CHANGES
      bullets:
        - 2026-09-30 — narrowed the first slice.
```

Card `header_meta` is optional compact metadata rendered inline after the bold card ID. Multiple values are joined with ` | `; the status chip remains right-aligned. Longer descriptive `meta` remains a separate block below the title.

The optional `marker` is a prominent compact identifier placed at the leading left edge of the title row, before the title. Board-level `meta` values are joined with ` | ` and wrap as one continuous status line beneath the title row.
The optional `summary` gives descriptive prose its own heading and normal body
typography rather than forcing it into the small metadata line.

`section_columns` defaults to 1 and may be set to 2 when two related sections
should share one row. Each section still wraps independently; the taller section
sets the row height. This is presentation-only and assigns no meaning to the
section headings.

All identifiers, headings, state labels, tones and metadata are presentation data. Group tones are retained as compatible source metadata but do not color group headings.
The renderer does not assign semantics to concepts such as an activity, lane,
document or planning change.

## Print-friendly style

BoardView and RoadmapView share the same presentation palette and neutral visual
primitives:

- white page and white cards;
- thin neutral borders and section rules;
- large colored background areas are avoided;
- all section/group headings use the same uppercase, neutral typography, font size and rule styling;
- color is reserved mainly for compact state chips, document badges and small accents;
- section rules start after the rendered heading text rather than crossing it;
- card IDs remain bold while compact header metadata uses normal small text on the same row;
- cards grow with wrapped title/metadata instead of clipping content;
- three cards are used per row on A4 portrait;
- compact outer margins and block spacing preserve readable typography while
  using the portrait page efficiently.

BoardView preserves the A4 portrait page model without imposing a one-page limit.
When the complete board is taller than one page, the renderer paginates at
top-level block boundaries (summary, section rows, badge section, groups and
trailing sections):

- `board.pdf` contains real A4 pages;
- `board.svg` remains one continuous vertical review view with visible page
  boundaries;
- typography, card size and source content are not reduced merely to force a
  board onto one page;
- an individual top-level block remains indivisible in this slice. Rendering
  fails only when that one block itself cannot fit on a single A4 page.

Existing boards that fit on one page keep the same one-page presentation.

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
