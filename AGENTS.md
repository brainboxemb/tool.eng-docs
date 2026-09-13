# Repository agent guidance

Persistent guidance for automated agents working in `brainboxemb/tool.eng-docs`.

## Purpose

This repository provides reusable, project-independent tooling for engineering documentation: declarative diagrams and, where explicitly qualified, common document/evidence assembly mechanisms.

It must not absorb project-specific engineering semantics from consuming repositories.

## Extraction boundary

The initial diagram implementation was extracted from mechanisms proven in `brainboxemb/2026-010-01.meta.event-timing-software`.

Keep the boundary explicit:

- this repository owns generic schemas, renderer/layout mechanisms, themes, generic assembly/link mechanisms, CLI behaviour and conformance fixtures;
- consuming repositories own project-specific YAML, document sets, build/verification execution and engineering meaning;
- do not copy event-timing-, SCAD- or Java-specific labels, requirements, IDs or implementation semantics into reusable contracts;
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

Before implementing a planned step, reassess its purpose, owner boundary, assumptions and qualification cases against the current repository state and real consumers. A roadmap item is a working hypothesis, not an instruction to preserve stale design choices.

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

## Release and development scope

The latest released baseline is documented by `pyproject.toml`, `CHANGELOG.md` and the matching GitHub release/tag. Consumers should pin released versions.

Feature branches may use a development version such as `X.Y.Z.dev0`. Do not present unreleased CLI/configuration contracts as part of the last stable release.

For new capabilities, derive scope from the owning issue plus any cross-project architecture/qualification plan. Keep the first slice small and prove it against real consumers before widening ownership or adding orchestration.

In particular, common document assembly must remain separate from producer execution: diagram rendering, SCAD builds, Java builds and verification keep their own execution/cache/failure semantics unless a later explicit architecture decision changes that boundary.

## Dependencies

Use normal Python project metadata. Dependencies are intentionally small: currently `PyYAML`, `jsonschema` and `pytest` for tests, with additional libraries only where an accepted capability requires them. Prefer the Python standard library for XML/SVG/draw.io and Markdown assembly mechanics where practical.

Do not add a separate repository-initialisation layer or consume `tool.git-project` merely because this is a tool repository.

## Verification

Diagram renderer changes should verify source validation, parseable SVG and draw.io XML, native/editable draw.io structure, expected semantic content, deterministic repeated rendering and useful non-zero CLI failures for invalid input.

Document-assembly changes should verify schema validation, source immutability, safe output paths, deterministic asset localisation, preservation of unknown links/code blocks, provenance/manifests and qualification against the intended real consumers.

User-facing examples should be exercised by CI as part of the normal test suite.

Run the suite on Linux and Windows before a reusable release is considered complete.
