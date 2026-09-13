# Repository agent guidance

Persistent guidance for automated agents working in `brainboxemb/tool.eng-docs`.

## Purpose

This repository provides reusable, project-independent tooling for declarative engineering documentation: architecture diagrams, planning/roadmap views, schema validation, theming and generated SVG/draw.io/PDF output.

It must not absorb project-specific engineering semantics from consuming repositories.

## Extraction boundary

The initial v0.1.0 implementation is extracted from mechanisms proven in `brainboxemb/2026-010-01.meta.event-timing-software`, especially issue #6 and PR #9.

Keep the boundary explicit:

- this repository owns generic schemas, renderer/layout mechanisms, themes, CLI behaviour and conformance fixtures;
- consuming repositories own project-specific YAML and engineering meaning;
- do not copy event-timing-specific labels, requirements, IDs or topology into reusable fixtures;
- clean/refactor generic mechanisms during extraction instead of preserving project-local structure blindly.

## Working method

Use issue → feature branch → early draft PR.

1. start from an issue/work item;
2. create `feature/pr-<work-number>-<short-slug>`;
3. open a draft PR as soon as the first reviewable commit exists;
4. use the PR as the implementation/discussion/evidence record;
5. mark ready only after scoped tests and evidence are complete.

The `pr-<N>` portion is the issue/work number and need not equal the eventual GitHub PR number.

Do not perform normal feature work directly on `main`.

## User-facing documentation

A reusable capability is not complete merely because the schema/CLI/tests exist.

For every new or materially changed public capability:

- document the user workflow in the README or a linked page under `docs/`;
- document the current source/configuration contract rather than making users reverse-engineer schemas/tests;
- provide at least one small domain-neutral example under `examples/`;
- keep user-facing examples executable/renderable in automated tests so they cannot silently drift from the implementation;
- distinguish user examples from conformance/stress fixtures under `tests/fixtures/`;
- update user documentation in the same PR when public CLI/source behavior changes.

Machine-readable schemas remain authoritative for validation, but they are not a substitute for usable human documentation.

## v0.1.0 scope

Issue #1 owns the first-release scope. Keep it small and proven:

- YAML parsing;
- JSON Schema validation;
- reusable themes;
- native editable draw.io generation;
- SVG generation;
- planning/roadmap rendering and PDF where applicable;
- generic CLI entry points;
- domain-neutral conformance fixtures;
- deterministic output checks;
- Linux and Windows verification.

Do not add speculative diagram families or abstractions before the extracted baseline is stable.

## Dependencies

Use normal Python project metadata. Initial dependencies are intentionally small: `PyYAML`, `jsonschema`, `reportlab` where PDF is required, and `pytest` for tests. Prefer the Python standard library for XML/SVG/draw.io generation where practical.

Do not add a separate repository-initialisation layer or consume `tool.git-project` merely because this is a tool repository.

## Verification

Renderer changes should verify source validation, parseable SVG and draw.io XML, native/editable draw.io structure, expected semantic content, deterministic repeated rendering, PDF generation where applicable, and useful non-zero CLI failures for invalid input.

User-facing examples should also be rendered by CI as part of the normal test suite.

Run the suite on Linux and Windows before a reusable release is considered complete.
