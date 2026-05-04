#!/usr/bin/env node
/**
 * Sync the language-neutral spec from ../specs into docs/specification/.
 *
 * The source of truth is ../specs/bank2ai.spec.md (narrative) and
 * ../specs/bank2ai.json (JSON Schema). This script regenerates:
 *
 *   docs/specification/overview.md
 *   docs/specification/tools/index.md
 *   docs/specification/tools/<tool-name>.md   (one per tool)
 *   docs/specification/models/index.md
 *   docs/specification/models/<ModelName>.md  (one per model)
 *
 * Generated files carry a "do not edit" banner and are gitignored. Edit
 * the spec under ../specs/ instead.
 */

import {mkdir, readFile, rm, writeFile} from 'node:fs/promises';
import {dirname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(HERE, '..', '..');
const SPECS_DIR = resolve(REPO_ROOT, 'specs');
const OUT_DIR = resolve(HERE, '..', 'docs', 'specification');

const BANNER = (sourcePath) =>
  `{/* This file is generated from ${sourcePath} by docs/scripts/sync-spec.mjs. Do not edit by hand. */}\n\n`;

async function main() {
  const spec = JSON.parse(await readFile(resolve(SPECS_DIR, 'bank2ai.json'), 'utf8'));
  const overviewMd = await readFile(resolve(SPECS_DIR, 'bank2ai.spec.md'), 'utf8');

  await rm(OUT_DIR, {recursive: true, force: true});
  await mkdir(resolve(OUT_DIR, 'tools'), {recursive: true});
  await mkdir(resolve(OUT_DIR, 'models'), {recursive: true});

  await writeOverview(overviewMd);
  await writeToolsIndex(spec.tools);
  for (const tool of spec.tools) {
    await writeToolPage(tool);
  }
  await writeModelsIndex(spec.models);
  for (const [name, schema] of Object.entries(spec.models)) {
    await writeModelPage(name, schema);
  }

  console.log(
    `[sync-spec] wrote ${spec.tools.length} tools and ${
      Object.keys(spec.models).length
    } models to ${OUT_DIR}`,
  );
}

async function writeOverview(spec) {
  const frontmatter = [
    '---',
    'title: Specification overview',
    'sidebar_position: 1',
    'description: The Bank2AI MCP specification — narrative source of truth.',
    '---',
    '',
  ].join('\n');
  // Strip the H1 (frontmatter title becomes the page heading) and rewrite repo-relative links.
  const body = rewriteSpecLinks(spec.replace(/^#\s+.*\n+/, ''));
  const intro =
    ':::info Source of truth\n' +
    'This page is generated from [`specs/bank2ai.spec.md`](https://github.com/bank2ai/bank2ai/blob/main/specs/bank2ai.spec.md). Edit there.\n' +
    ':::\n\n';
  await writeFile(
    resolve(OUT_DIR, 'overview.md'),
    frontmatter + BANNER('specs/bank2ai.spec.md') + intro + body,
  );
}

const REPO_BLOB = 'https://github.com/bank2ai/bank2ai/blob/main';
const REPO_TREE = 'https://github.com/bank2ai/bank2ai/tree/main';

function rewriteSpecLinks(md) {
  return md
    // (./bank2ai.json) -> raw spec on GitHub
    .replace(/\(\.\/bank2ai\.json\)/g, `(${REPO_BLOB}/specs/bank2ai.json)`)
    // (./README.md) inside specs/ -> specs README on GitHub
    .replace(/\(\.\/README\.md\)/g, `(${REPO_BLOB}/specs/README.md)`)
    // (../README.md#marketplace) -> on-site marketplace page
    .replace(/\(\.\.\/README\.md#marketplace\)/g, '(/docs/marketplace/overview)')
    // (../README.md) -> repo README on GitHub
    .replace(/\(\.\.\/README\.md\)/g, `(${REPO_BLOB}/README.md)`)
    // (../examples/<name>) -> example on GitHub
    .replace(/\(\.\.\/examples\/([^)]+)\)/g, `(${REPO_TREE}/examples/$1)`);
}

async function writeToolsIndex(tools) {
  const lines = [
    '---',
    'title: Tool surface',
    'sidebar_position: 1',
    'description: The eight MCP tools every Bank2AI server registers.',
    '---',
    '',
    BANNER('specs/bank2ai.json').trim(),
    '',
    '# Tool surface',
    '',
    'Every compliant Bank2AI server registers the following MCP tools. Names, input schemas, and output schemas are fixed by the spec; servers MAY add vendor-specific tools but MUST NOT alter these.',
    '',
    '| Tool | Purpose |',
    '| --- | --- |',
  ];
  for (const tool of tools) {
    const desc = (tool.description || '').replace(/\n+/g, ' ').replace(/\|/g, '\\|');
    lines.push(`| [\`${tool.name}\`](./${tool.name}) | ${desc} |`);
  }
  lines.push('');
  await writeFile(resolve(OUT_DIR, 'tools', 'index.md'), lines.join('\n'));
}

async function writeToolPage(tool) {
  const lines = [
    '---',
    `title: ${tool.name}`,
    `description: ${escapeYaml(oneLine(tool.description))}`,
    '---',
    '',
    BANNER('specs/bank2ai.json').trim(),
    '',
    `# \`${tool.name}\``,
    '',
    tool.description,
    '',
    '## Input',
    '',
    ...renderSchemaSection(tool.inputSchema),
    '',
    '## Output',
    '',
    ...renderSchemaSection(tool.outputSchema),
    '',
  ];
  await writeFile(resolve(OUT_DIR, 'tools', `${tool.name}.md`), lines.join('\n'));
}

async function writeModelsIndex(models) {
  const lines = [
    '---',
    'title: Data models',
    'sidebar_position: 1',
    'description: Shared Bank2AI data models — Account, Transaction, Category, Recipient.',
    '---',
    '',
    BANNER('specs/bank2ai.json').trim(),
    '',
    '# Data models',
    '',
    'These shared shapes are referenced from tool inputs and outputs. Servers MAY return additional fields; clients MUST tolerate unknown fields.',
    '',
    '| Model | Description |',
    '| --- | --- |',
  ];
  for (const [name, schema] of Object.entries(models)) {
    const desc = (schema.description || '').replace(/\n+/g, ' ').replace(/\|/g, '\\|');
    lines.push(`| [\`${name}\`](./${name}) | ${desc} |`);
  }
  lines.push('');
  await writeFile(resolve(OUT_DIR, 'models', 'index.md'), lines.join('\n'));
}

async function writeModelPage(name, schema) {
  const lines = [
    '---',
    `title: ${name}`,
    `description: ${escapeYaml(oneLine(schema.description) || `${name} data model.`)}`,
    '---',
    '',
    BANNER('specs/bank2ai.json').trim(),
    '',
    `# \`${name}\``,
    '',
    schema.description || '',
    '',
    '## Properties',
    '',
    ...renderSchemaSection(schema),
    '',
  ];
  await writeFile(resolve(OUT_DIR, 'models', `${name}.md`), lines.join('\n'));
}

function renderSchemaSection(schema) {
  if (!schema || Object.keys(schema).length === 0) {
    return ['_(none)_'];
  }
  // FastMCP wraps non-object outputs into `{result: ...}` for MCP transport.
  // Unwrap that for friendlier rendering; keep the raw schema in the details block.
  const display = unwrapResultEnvelope(schema);
  const out = [];

  if (display.kind === 'array') {
    out.push(`Returns an array of ${describeType(display.items ?? {})}.`);
    out.push('');
    if (display.items?.properties) {
      out.push(...renderPropertiesTable(display.items));
    }
  } else if (display.kind === 'object') {
    out.push(...renderPropertiesTable(display.schema));
  } else if (display.kind === 'scalar') {
    out.push(`Returns ${describeType(display.schema)}.`);
    out.push('');
  }

  out.push('<details>');
  out.push('<summary>Raw JSON Schema</summary>');
  out.push('');
  out.push('```json');
  out.push(JSON.stringify(schema, null, 2));
  out.push('```');
  out.push('');
  out.push('</details>');
  return out;
}

function renderPropertiesTable(schema) {
  const properties = schema?.properties;
  if (!properties || Object.keys(properties).length === 0) return [];
  const required = new Set(schema.required ?? []);
  const lines = [
    '| Field | Type | Required | Description |',
    '| --- | --- | --- | --- |',
  ];
  for (const [name, prop] of Object.entries(properties)) {
    const type = describeType(prop);
    const isRequired = required.has(name) ? '✓' : '';
    const desc = formatDescription(prop);
    lines.push(`| \`${name}\` | ${type} | ${isRequired} | ${desc} |`);
  }
  lines.push('');
  return lines;
}

function unwrapResultEnvelope(schema) {
  // Detect FastMCP's `{type: object, properties: {result: <S>}, required: [result]}` wrapper.
  if (
    schema?.type === 'object' &&
    schema.properties &&
    Object.keys(schema.properties).length === 1 &&
    schema.properties.result
  ) {
    const inner = schema.properties.result;
    if (inner.type === 'array') {
      return {kind: 'array', items: inner.items, schema: inner};
    }
    if (inner.type === 'object' || inner.properties) {
      return {kind: 'object', schema: inner};
    }
    return {kind: 'scalar', schema: inner};
  }
  if (schema?.type === 'array') {
    return {kind: 'array', items: schema.items, schema};
  }
  if (schema?.type === 'object' || schema?.properties) {
    return {kind: 'object', schema};
  }
  return {kind: 'scalar', schema};
}

function describeType(prop) {
  if (!prop) return '`unknown`';
  if (prop.$ref) return refName(prop.$ref);
  if (prop.anyOf) {
    const parts = prop.anyOf.map(describeType).filter(Boolean);
    const unique = [...new Set(parts)];
    return unique.join(' \\| ');
  }
  if (prop.enum) {
    return prop.enum.map((v) => `\`${JSON.stringify(v)}\``).join(' \\| ');
  }
  if (prop.type === 'array') {
    return `array&lt;${describeType(prop.items ?? {})}&gt;`;
  }
  if (prop.type === 'null') return '`null`';
  if (typeof prop.type === 'string') return `\`${prop.type}\``;
  if (Array.isArray(prop.type)) return prop.type.map((t) => `\`${t}\``).join(' \\| ');
  return '`object`';
}

function refName(ref) {
  const parts = ref.split('/');
  return `\`${parts[parts.length - 1]}\``;
}

function formatDescription(prop) {
  const bits = [];
  if (prop.description) bits.push(escapeCell(prop.description));
  if (prop.default !== undefined) {
    bits.push(`Default: \`${JSON.stringify(prop.default)}\`.`);
  }
  if (prop.examples?.length) {
    bits.push(`Examples: ${prop.examples.map((e) => `\`${JSON.stringify(e)}\``).join(', ')}.`);
  }
  if (prop.pattern) {
    bits.push(`Pattern: \`${prop.pattern}\`.`);
  }
  return bits.join(' ');
}

function escapeCell(value) {
  return String(value).replace(/\|/g, '\\|').replace(/\n+/g, ' ');
}

function oneLine(value) {
  return String(value || '').replace(/\s+/g, ' ').trim();
}

function escapeYaml(value) {
  return JSON.stringify(value);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
