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
    'description: The bank2ai MCP specification, narrative source of truth.',
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
    'description: The MCP tools every bank2ai server registers.',
    '---',
    '',
    BANNER('specs/bank2ai.json').trim(),
    '',
    '# Tool surface',
    '',
    'Every compliant bank2ai server registers the following MCP tools. Names, input schemas, and output schemas are fixed by the spec; servers MAY add vendor-specific tools but MUST NOT alter these.',
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
    'description: Shared bank2ai data models, Account, Transaction, Category, Recipient.',
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
      out.push(...renderObjectTree(display.items, 3, 3, new Set(), schema));
    }
  } else if (display.kind === 'object') {
    out.push(...renderObjectTree(display.schema, 3, 3, new Set(), schema));
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

// Render a property table for `schema`, then recurse into any property
// whose value is a nested object (or array of objects, or anyOf of
// objects) so each item shape is documented inline. `depth` caps how
// deep recursion goes to keep the page bounded. `rootSchema` carries
// the top-level schema so `$ref` pointers can be resolved against its
// `$defs`.
function renderObjectTree(schema, depth, headingLevel = 3, seen = new Set(), rootSchema = schema) {
  const out = renderPropertiesTable(schema);
  if (depth <= 0) return out;

  const properties = schema?.properties ?? {};
  for (const [name, prop] of Object.entries(properties)) {
    const nested = extractNestedSchemas(prop, rootSchema);
    for (const sub of nested) {
      // Dedupe within a single recursion path so a model that recursively
      // references itself doesn't blow up.
      const fingerprint = sub.schema && JSON.stringify(sub.schema).slice(0, 200);
      if (seen.has(fingerprint)) continue;
      const nextSeen = new Set(seen);
      nextSeen.add(fingerprint);

      const heading = '#'.repeat(headingLevel);
      const suffix = sub.kind === 'array' ? '[]' : '';
      const variantLabel = sub.label ? ` — ${sub.label}` : '';
      out.push(`${heading} \`${name}${suffix}\`${variantLabel}`);
      out.push('');
      const desc = oneLine(sub.schema.description);
      if (desc) {
        out.push(desc);
        out.push('');
      }
      out.push(...renderObjectTree(sub.schema, depth - 1, headingLevel + 1, nextSeen, rootSchema));
    }
  }
  return out;
}

// Return the list of object-shaped sub-schemas reachable from a single
// property declaration. Handles direct objects, arrays of objects,
// `$ref` pointers (resolved against `rootSchema.$defs`), and `anyOf` /
// `oneOf` unions (Optional[X], discriminated unions, etc.) — each
// object variant is returned as its own entry so each can be
// documented.
function extractNestedSchemas(prop, rootSchema) {
  if (!prop) return [];
  if (prop.$ref) {
    const resolved = resolveRef(rootSchema, prop.$ref);
    if (resolved) return extractNestedSchemas(resolved, rootSchema);
    return [];
  }
  if (prop.type === 'object' && prop.properties) {
    return [{kind: 'object', schema: prop}];
  }
  if (!prop.type && prop.properties) {
    return [{kind: 'object', schema: prop}];
  }
  if (prop.type === 'array' && prop.items) {
    const inner = extractNestedSchemas(prop.items, rootSchema);
    return inner.map((s) => ({...s, kind: 'array'}));
  }
  const unionMembers = prop.anyOf || prop.oneOf;
  if (unionMembers) {
    const out = [];
    for (const member of unionMembers) {
      out.push(...extractNestedSchemas(member, rootSchema));
    }
    if (out.length > 1) {
      for (const entry of out) {
        if (!entry.label) entry.label = variantLabel(entry.schema);
      }
    }
    return out;
  }
  return [];
}

function resolveRef(rootSchema, ref) {
  if (!ref || !ref.startsWith('#/')) return null;
  const parts = ref.slice(2).split('/');
  let cursor = rootSchema;
  for (const part of parts) {
    if (cursor == null) return null;
    cursor = cursor[part];
  }
  return cursor ?? null;
}

// Best-effort name for an anyOf variant: prefer a literal `type`
// discriminator value when present (e.g. `iban`, `bban`), otherwise
// fall back to nothing.
function variantLabel(schema) {
  const typeProp = schema?.properties?.type;
  if (typeProp?.const) return `\`type: "${typeProp.const}"\``;
  if (typeProp?.enum?.length === 1) return `\`type: "${typeProp.enum[0]}"\``;
  return null;
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
