# Deploying bank2ai.com

The site is built with Docusaurus and deployed via **Azure Static Web Apps** (the same hosting Bancony uses for `bancony.com`).

## How it works

- [`.github/workflows/azure-static-web-apps.yml`](../.github/workflows/azure-static-web-apps.yml) runs on every push to `main` and on every PR touching `docs/`, `specs/`, or the workflow itself.
- The workflow installs `docs/` deps, runs `npm run build` (which calls the `prebuild` `sync-spec` script first), and uploads `docs/build/` to Azure Static Web Apps.
- Pull requests get preview deployments from Azure SWA automatically; the PR-close job tears them down.
- [`docs/static/staticwebapp.config.json`](./static/staticwebapp.config.json) configures the SPA fallback (404 → `/404.html` for routes that aren't static assets).

## One-time setup

1. **Create a Static Web App in Azure** for `bank2ai.com`. Choose the "Custom" build option (not GitHub-managed Oryx) since we build the site ourselves in CI.
2. **Add the deployment token to GitHub** as a repository secret named `AZURE_STATIC_WEB_APPS_API_TOKEN_BANK2AI`.
3. **Wire the custom domain** in the Azure portal: add `bank2ai.com` (and optionally `www.bank2ai.com`) to the Static Web App and create the `CNAME` / `ALIAS` records in DNS as instructed.
4. **Enable HTTPS** — Azure SWA provisions a managed cert automatically once the DNS records are in place.

## Local preview

```bash
cd docs
npm install
npm run build
npm run serve
```

This runs `prebuild` → `sync-spec` → `docusaurus build` → static server on `http://localhost:3000`.

## Spec → docs sync

`docs/scripts/sync-spec.mjs` runs automatically before `npm start` and `npm run build`. It reads `../specs/bank2ai.spec.md` and `../specs/bank2ai.json` and regenerates `docs/docs/specification/`. The generated directory is gitignored — `specs/` is the source of truth.
