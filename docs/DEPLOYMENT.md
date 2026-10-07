# Deploying bank2ai.com

The site is built with Docusaurus and deployed to **Firebase Hosting**
(site `bank2ai-com`).

## How it works

- [`.github/workflows/firebase-hosting.yml`](../.github/workflows/firebase-hosting.yml)
  runs on every push to `main` touching `docs/`, `specs/`, or the workflow/config.
- The workflow installs `docs/` deps, runs `npm run build` (which calls the
  `prebuild` `sync-spec` script first), and deploys `docs/build/` with
  `firebase-tools`.
- Auth is **keyless**: GitHub OIDC → Workload Identity Federation →
  `deploy-sites@bancony-shared` (Firebase-Hosting-admin only). There are no
  deployment tokens or secrets in this repo.
- [`firebase.json`](../firebase.json) carries the hosting behaviour:
  `trailingSlash: false` (canonical URLs without trailing slash, matching the
  sitemap) and `.md` served as `text/markdown`. Docusaurus's `404.html` is
  served automatically for unknown paths.

## One-time setup (already done)

1. Firebase Hosting site `bank2ai-com` created.
2. This repo admitted to the Workload Identity Federation pool the deploy
   service account trusts (maintainers: see the internal infra repo).
3. Custom domain `bank2ai.com` wired to the site.

## Analytics

Google Analytics 4 via Docusaurus's built-in `gtag` preset option in
[`docusaurus.config.ts`](docusaurus.config.ts): property `bank2ai.com`,
measurement ID `G-06F97KDXF7` (public by design, so it lives in the config,
not in a secret store). Page views and traffic sources only; no advertising
features. The sitemap at `/sitemap.xml` is submitted in Google Search Console.

## Local preview

```bash
cd docs
npm install
npm run build
npm run serve
```

This runs `prebuild` → `sync-spec` → `docusaurus build` → static server on `http://localhost:3000`.

## Spec → docs sync

`docs/scripts/sync-spec.mjs` runs automatically before `npm start` and `npm run build`. It reads `../specs/bank2ai.spec.md` and `../specs/bank2ai.json` and regenerates `docs/docs/specification/`. The generated directory is gitignored, `specs/` is the source of truth.
