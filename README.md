# tool.eng-docs

Reusable, project-independent tooling for declarative engineering documentation.

The first release, `v0.1.0`, is extracted from proven documentation tooling in `brainboxemb/2026-010-01.meta.event-timing-software` and focuses on reusable diagram generation rather than project-specific engineering content.

## v0.1.0 scope

- declarative YAML diagram sources;
- JSON Schema validation;
- reusable YAML visual themes;
- SVG generation;
- native editable draw.io generation;
- automatic orthogonal edge routing;
- explicit edge waypoints and side/position anchors;
- domain-neutral conformance fixtures and tests;
- Linux and Windows verification;
- `eng-docs diagrams` command-line interface.

Planning/roadmap and printable PDF extraction is intentionally deferred to [issue #3](https://github.com/brainboxemb/tool.eng-docs/issues/3) so the reusable diagram renderer can be released and consumed first.

The repository must not contain consuming-project-specific labels, topology, requirements or other domain semantics.

## Installation

The intended repository-consumer form is a pinned Git dependency. After the `v0.1.0` release:

```text
brainboxemb-eng-docs @ git+https://github.com/brainboxemb/tool.eng-docs.git@v0.1.0
```

A consuming repository can then run, for example:

```text
eng-docs diagrams --source docs/_diagrams --out bld/docs/architecture
```

The built-in schema and theme are used unless `--schema` or `--theme` is supplied.

## Release model

`pyproject.toml` owns the package version. When a non-development version is merged to `main`, the release workflow creates the matching GitHub tag/release and attaches the built Python package artifacts. Consumers should pin the released tag rather than depend on a feature branch.

The first real consumer is `brainboxemb/2026-010-01.meta.event-timing-software`. After `v0.1.0` exists, that repository should install the pinned release in its documentation environment and invoke `eng-docs diagrams` instead of carrying a duplicate generic renderer implementation.

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

The active v0.1.0 PR publishes its review output to `dev/pr-2/docs` once the workflow is green.

## Active work

The first implementation increment is tracked by [issue #1](https://github.com/brainboxemb/tool.eng-docs/issues/1) and targets release `v0.1.0` followed by migration of the first real consumer.

## Extraction baseline

The reusable mechanisms were proven in `brainboxemb/2026-010-01.meta.event-timing-software`, especially issue #6 and PR #9. That project remains the owner of its project-specific YAML sources; this repository owns only reusable schemas, rendering/layout mechanisms, themes, CLI behaviour and conformance tests.
