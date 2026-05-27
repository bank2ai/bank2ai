#!/usr/bin/env node
/**
 * Sync the canonical CHANGELOG.md at the repo root into the docs site.
 *
 * The source of truth is /CHANGELOG.md. This script regenerates:
 *
 *   docs/docs/resources/changelog.md
 *
 * The generated file carries a "do not edit" banner and is gitignored. Edit
 * /CHANGELOG.md at the repo root instead.
 */

import {readFile, writeFile} from 'node:fs/promises';
import {dirname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(HERE, '..', '..');
const SOURCE = resolve(REPO_ROOT, 'CHANGELOG.md');
const OUT = resolve(HERE, '..', 'docs', 'resources', 'changelog.md');

const FRONTMATTER = [
  '---',
  'title: Changelog',
  'sidebar_position: 2',
  'description: Notable changes to the bank2ai specification and library.',
  '---',
  '',
].join('\n');

const BANNER =
  '{/* This file is generated from /CHANGELOG.md by docs/scripts/sync-changelog.mjs. Do not edit by hand. */}\n\n';

async function main() {
  const source = await readFile(SOURCE, 'utf8');
  // Strip the leading H1; the frontmatter title becomes the page heading.
  const body = source.replace(/^#\s+.*\n+/, '');
  await writeFile(OUT, FRONTMATTER + BANNER + body);
  console.log(`[sync-changelog] wrote ${OUT}`);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
