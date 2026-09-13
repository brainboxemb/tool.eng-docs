# tool.eng-docs generated conformance documentation

Generated from source commit `a15d2d259be7a88921e6c1afd7572b5acfd0fdd3`.

This branch is review evidence for both reusable capabilities: declarative diagram generation and document assembly around already-produced assets. The generated files are intentionally inspectable without opening an Actions log.

## Owner test evidence

- [pytest output](evidence/pytest.txt)
- [source revision](source-sha.txt)

## Document assembly example

The example keeps ordinary source Markdown readable, inventories an already-produced SVG through a manifest, and assembles a self-contained publication copy.

- [assembled document index](assembly/documents/README.md)
- [assembled document](assembly/documents/overview.md)
- [assembly provenance](assembly/assembly-info.yml)
- [localized asset](assembly/assets/architecture/system.svg)
- [assembly configuration](assembly/_input/assembly.yml)
- [source Markdown before assembly](assembly/_input/overview.md)
- [producer asset manifest](assembly/_input/assets.yml)

## Diagram conformance

The SVG output is the quickest visual review; the draw.io files verify that the same diagrams remain natively editable.

### Simple flow

[Source YAML](fixtures/simple-flow.yaml) · [Editable draw.io](diagrams/simple-flow.drawio)

![Simple flow](diagrams/simple-flow.svg)

### Layered architecture

[Source YAML](fixtures/layered-architecture.yaml) · [Editable draw.io](diagrams/layered-architecture.drawio)

![Layered architecture](diagrams/layered-architecture.svg)

### Routing stress

[Source YAML](fixtures/routing-stress.yaml) · [Editable draw.io](diagrams/routing-stress.drawio)

![Routing stress](diagrams/routing-stress.svg)
