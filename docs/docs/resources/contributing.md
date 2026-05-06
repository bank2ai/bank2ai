---
title: Contributing
sidebar_position: 3
description: How to contribute to bank2ai — the spec, the library, and the docs.
---

# Contributing

Bank2ai is an open standard maintained at [github.com/bank2ai/bank2ai](https://github.com/bank2ai/bank2ai). Contributions are welcome.

## Working in the monorepo

The repo is a [uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/). From the root:

```bash
uv sync                                       # install library + examples + dev deps
uv run --package bank2ai-demo bank2ai-demo    # run the demo server
uv run pytest examples/demo                   # run the demo example tests
uv run python scripts/generate_spec.py        # regenerate specs/bank2ai.json
```

## Where to make changes

| If you're changing… | Edit… | Then run… |
| --- | --- | --- |
| Tool inputs/outputs | `src/bank2ai/tools.py`, `src/bank2ai/models.py` | `uv run python scripts/generate_spec.py`; the drift test in `examples/demo/tests/test_schema_sync.py` should pass. |
| Spec narrative | `specs/bank2ai.spec.md` | Nothing — the docs site renders it directly. |
| Library docs | `docs/docs/library/*.md` | `cd docs && npm run start` to preview. |
| Tool / model reference pages | _Don't_ — they're generated from `specs/bank2ai.json` by `docs/scripts/sync-spec.mjs`. |

## Pull request flow

1. Open an issue first for anything spec-affecting, so the design is discussed before code lands.
2. Fork, branch, and make your change.
3. Run the relevant tests (see the table above).
4. Open a PR and link the issue.

## Code of conduct

Be the kind of collaborator you'd want on the other side of the conversation.

## Working on the docs site

```bash
cd docs
npm install
npm run start
```

The docs build runs the spec-sync script automatically (`prestart` / `prebuild`). If you change anything under `specs/`, those changes flow into the site automatically.
