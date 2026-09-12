# tool.eng-docs

Reusable, project-independent tooling for declarative engineering documentation.

The initial v0.1.0 scope is extracted from proven documentation tooling in `brainboxemb/2026-010-01.meta.event-timing-software` and focuses on generic mechanisms rather than project-specific engineering content.

## Initial scope

- declarative YAML sources;
- JSON Schema validation;
- reusable YAML visual themes;
- native editable draw.io generation;
- SVG generation;
- planning/roadmap rendering;
- printable PDF generation where applicable;
- domain-neutral conformance fixtures and tests;
- Linux and Windows verification.

The repository must not contain event-timing-specific labels, topology, requirements or other consuming-project semantics.

## Generated conformance documentation

CI renders the domain-neutral conformance fixtures so diagram quality can be reviewed directly in GitHub instead of only through test assertions or downloaded artifacts.

Generated output is published using the same convention as consuming documentation projects:

```text
pull request  -> dev/pr-<PR-number>/docs
main          -> prod/docs
```

Each generated documentation branch contains:

- a README with the rendered SVG fixtures embedded for visual inspection;
- the fixture YAML sources;
- SVG output;
- native editable draw.io output;
- `source-sha.txt` tying the generated result to its source commit.

The active v0.1.0 draft PR therefore publishes its review output to `dev/pr-2/docs` once the workflow is green.

## Active work

The first implementation increment is tracked by [issue #1](https://github.com/brainboxemb/tool.eng-docs/issues/1) and targets the first reusable release, `v0.1.0`.

## Extraction baseline

The reusable mechanisms were proven in `brainboxemb/2026-010-01.meta.event-timing-software`, especially issue #6 and PR #9. That project remains the owner of its project-specific YAML sources; this repository owns only reusable schemas, rendering/layout mechanisms, themes, CLI behaviour and conformance tests.
