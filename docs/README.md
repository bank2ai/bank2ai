# bank2ai docs

This directory will host the [Docusaurus](https://docusaurus.io/) site for [bank2ai.com](https://bank2ai.com).

## Bootstrap (planned)

```bash
# from the repo root
npx create-docusaurus@latest docs classic --typescript
```

The classic preset gives us a docs section, a blog (optional), and a landing page out of the box. After bootstrapping:

* point `presets.docs.path` at the docs source directory and add the existing `bank2ai` library + example servers as documented surfaces;
* configure deployment to bank2ai.com (GitHub Pages, Cloudflare Pages, or Vercel — TBD);
* link to the per-package READMEs (`bank2ai/README.md`, `examples/demo/README.md`, `examples/meniga/README.md`) until the docs site is fleshed out.

## Local development (once bootstrapped)

```bash
cd docs
npm install
npm run start
```

## Sourcing content from `specs/`

The canonical spec lives in [`../specs`](../specs). The Docusaurus site SHOULD render — not duplicate — that content:

* Surface [`../specs/bank2ai.spec.md`](../specs/bank2ai.spec.md) directly as a documentation page (e.g. via a Docusaurus `MDX` import or a small pre-build script that copies it into `docs/`).
* Generate per-tool reference pages from [`../specs/bank2ai.json`](../specs/bank2ai.json) (e.g. with a custom plugin / pre-build script that turns each `tools[]` entry into an MDX page with the input/output schemas rendered as tables).

Whatever pipeline we settle on, the rule of thumb is: `specs/` is the source of truth, `docs/` is presentation.

## Layout (intended)

```
docs/
├── docusaurus.config.ts
├── sidebars.ts
├── docs/                # markdown sources (some auto-generated from ../specs)
│   ├── intro.md
│   ├── library/
│   ├── tools/           # generated from ../specs/bank2ai.json
│   └── examples/
├── src/                 # custom React components, theme overrides
└── static/              # images, favicons
```
