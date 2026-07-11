#!/usr/bin/env node
// falsify-js — second reference implementation of PRML v0.1
//
// Single file, ~400 LOC, zero runtime dependencies beyond Node.js stdlib.
// Reproduces all 13 PRML v0.1 conformance vectors byte-for-byte.
//
// Spec:    https://spec.falsify.dev/v0.1
// Vectors: https://github.com/studio-11-co/falsify/tree/main/spec/test-vectors
// Python:  https://github.com/studio-11-co/falsify (reference implementation)
//
// Usage:
//   falsify-js init <name>                    create skeleton manifest
//   falsify-js lock <path>                    canonicalize + hash + write sidecar
//   falsify-js verify <path> --observed <v>   verify hash + evaluate verdict
//   falsify-js test-vectors <vectors.json>    run against conformance suite
//
// License: MIT.

'use strict';

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

// ─────────────────────────────────────────────────────────────────────────
// Canonicalization
// ─────────────────────────────────────────────────────────────────────────

const YAML_INDICATORS = ['?', ':', ',', '[', ']', '{', '}', '#', '&', '*',
                         '!', '|', '>', "'", '"', '%', '@', '`'];

const PLAIN_BOOL_NULL = new Set([
  'y','Y','yes','Yes','YES','n','N','no','No','NO',
  'true','True','TRUE','false','False','FALSE',
  'on','On','ON','off','Off','OFF',
  'null','Null','NULL','~','',
]);

// Fields whose value MUST round-trip as a float even when integer-valued.
// PyYAML preserves float-ness via its number type; JSON parsers in many
// languages do not. The spec field type is the source of truth, and it is
// version-aware: v0.1 fixed threshold as float64 (integer-valued thresholds
// render with explicit ".0" suffix), v0.2 RFC P-XX relaxes threshold to
// int|float (integer-valued thresholds render as plain integers).
const FLOAT_FIELDS_V01 = new Set(['threshold']);
const FLOAT_FIELDS_V02 = new Set();

function floatFieldsFor(version) {
  return version === 'prml/0.1' ? FLOAT_FIELDS_V01 : FLOAT_FIELDS_V02;
}

function looksLikeNumber(s) {
  if (/^[-+]?(\.[0-9]+|[0-9]+(\.[0-9]*)?)([eE][-+]?[0-9]+)?$/.test(s)) return true;
  if (/^[-+]?[0-9]+$/.test(s)) return true;
  if (/^[-+]?0[xX][0-9a-fA-F]+$/.test(s)) return true;
  if (/^[-+]?0[oO]?[0-7]+$/.test(s)) return true;
  if (/^[-+]?\.(inf|Inf|INF)$/.test(s)) return true;
  if (/^\.(nan|NaN|NAN)$/.test(s)) return true;
  return false;
}

function looksLikeTimestamp(s) {
  return /^\d{4}-\d{2}-\d{2}([Tt ]\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:?\d{2})?)?$/.test(s);
}

function needsQuoting(s) {
  if (typeof s !== 'string') return false;
  if (s.length === 0) return true;
  if (PLAIN_BOOL_NULL.has(s)) return true;
  if (looksLikeNumber(s)) return true;
  if (looksLikeTimestamp(s)) return true;
  const first = s[0];
  if (YAML_INDICATORS.includes(first)) return true;
  if (first === '-' && s.length > 1 && s[1] === ' ') return true;
  if (first === ' ' || first === '\t') return true;
  const last = s[s.length - 1];
  if (last === ' ' || last === '\t') return true;
  if (s.includes(': ')) return true;
  if (s.includes(' #')) return true;
  if (s.endsWith(':')) return true;
  if (/[\x00-\x08\x0b-\x1f\x7f]/.test(s)) return true;
  return false;
}

function quoteSingle(s) {
  return "'" + s.replace(/'/g, "''") + "'";
}

// Match PyYAML's safe_dump float rendering. PyYAML inherits Python's
// repr(float): magnitudes < 1e-4 or >= 1e16 use scientific notation; the
// mantissa always carries a `.0` if otherwise integer-valued; the exponent
// is zero-padded to at least two digits with explicit sign. JS's
// Number.prototype.toString switches to scientific only at magnitudes
// below ~1e-7 and uses no `.0` mantissa decoration, so for the small-float
// regime we need an explicit formatter to reproduce PyYAML's bytes.
//
// Examples (PyYAML / desired output):
//   0.85           -> "0.85"
//   1.0            -> handled by the hint=='float' branch above (toFixed(1))
//   0.000001       -> "1.0e-06"
//   1.5e-7         -> "1.5e-07"
//   1.234e-15      -> "1.234e-15"
function pythonRepr(v) {
  if (v === 0) return '0.0';
  const abs = Math.abs(v);
  if (abs < 1e-4 || abs >= 1e16) {
    const s = v.toExponential();
    const m = s.match(/^(-?)(\d+)(\.\d+)?e([+-])(\d+)$/);
    if (m) {
      const sign = m[1];
      const intPart = m[2];
      const fracPart = m[3] || '.0';
      const expSign = m[4];
      const expDigits = m[5].padStart(2, '0');
      return `${sign}${intPart}${fracPart}e${expSign}${expDigits}`;
    }
    return s;
  }
  return v.toString();
}

function renderScalar(v, hint) {
  if (v === null || v === undefined) return 'null';
  if (typeof v === 'boolean') return v ? 'true' : 'false';
  if (typeof v === 'bigint') return v.toString();
  if (typeof v === 'number') {
    if (!Number.isFinite(v)) {
      if (Number.isNaN(v)) return '.nan';
      return v > 0 ? '.inf' : '-.inf';
    }
    if (hint === 'float' && Number.isInteger(v)) {
      // Large integer-valued floats (|v| >= 1e16) must render in Python's
      // exponential form ("1.0e+20"), not toFixed ("100000000000000000000.0").
      // pythonRepr already produces the exponential form for that magnitude.
      if (Math.abs(v) >= 1e16) return pythonRepr(v);
      return v.toFixed(1);
    }
    if (Number.isInteger(v)) return v.toString();
    return pythonRepr(v);
  }
  if (typeof v === 'string') {
    return needsQuoting(v) ? quoteSingle(v) : v;
  }
  throw new Error('renderScalar: unsupported value type ' + typeof v);
}

function renderMapping(obj, indent, floatFields) {
  const keys = Object.keys(obj).sort();
  const lines = [];
  const pad = ' '.repeat(indent);
  for (const k of keys) {
    const v = obj[k];
    if (v !== null && typeof v === 'object' && !Array.isArray(v) && typeof v !== 'bigint') {
      lines.push(`${pad}${k}:`);
      lines.push(renderMapping(v, indent + 2, floatFields));
    } else if (Array.isArray(v)) {
      lines.push(`${pad}${k}:`);
      for (const item of v) {
        const hint = floatFields.has(k) ? 'float' : null;
        if (item !== null && typeof item === 'object' && !Array.isArray(item)) {
          const sub = renderMapping(item, indent + 2, floatFields);
          // Prefix first nested line with "- " instead of indent
          const padNested = ' '.repeat(indent + 2);
          const subLines = sub.split('\n');
          subLines[0] = `${pad}- ${subLines[0].slice(padNested.length)}`;
          for (let i = 1; i < subLines.length; i++) {
            subLines[i] = subLines[i];
          }
          lines.push(subLines.join('\n'));
        } else {
          lines.push(`${pad}- ${renderScalar(item, hint)}`);
        }
      }
    } else {
      const hint = floatFields.has(k) ? 'float' : null;
      lines.push(`${pad}${k}: ${renderScalar(v, hint)}`);
    }
  }
  return lines.join('\n');
}

function canonicalize(obj) {
  const floatFields = floatFieldsFor(obj && obj.version);
  return renderMapping(obj, 0, floatFields) + '\n';
}

function manifestHash(obj) {
  const bytes = canonicalize(obj);
  return crypto.createHash('sha256').update(bytes, 'utf-8').digest('hex');
}

// ─────────────────────────────────────────────────────────────────────────
// Required-field validation (subset of v0.1)
// ─────────────────────────────────────────────────────────────────────────

const REQUIRED_FIELDS = [
  'version', 'claim_id', 'created_at', 'metric',
  'comparator', 'threshold', 'dataset', 'seed', 'producer',
];
const REQUIRED_DATASET = ['id', 'hash'];
const REQUIRED_PRODUCER = ['id'];
const VALID_COMPARATORS = new Set(['>=', '<=', '>', '<', '==']);

// Control / non-portable chars forbidden in any PRML string field (key or value):
// C0 (U+0000–U+001F), DEL + C1 (U+007F–U+009F), line/paragraph separators
// (U+2028/U+2029), and BOM (U+FEFF). They canonicalize inconsistently across YAML
// engines, so a manifest carrying them is non-portable. Mirrors the Python
// reference (_FORBIDDEN_CHARS in falsify_prml.py). Additive — no conformance
// vector contains them, so no valid manifest's hash changes.
const FORBIDDEN_CHARS = /[\u0000-\u001f\u007f-\u009f\u2028\u2029\ufeff]/;

function badCharFields(obj, path = '') {
  const out = [];
  if (typeof obj === 'string') {
    if (FORBIDDEN_CHARS.test(obj)) out.push(path || '(value)');
  } else if (Array.isArray(obj)) {
    obj.forEach((v, i) => out.push(...badCharFields(v, `${path}[${i}]`)));
  } else if (obj && typeof obj === 'object') {
    for (const [k, v] of Object.entries(obj)) {
      const child = path ? `${path}.${k}` : k;
      // A forbidden char in a KEY canonicalizes non-portably just as in a value.
      if (FORBIDDEN_CHARS.test(k)) out.push(`${child} (key)`);
      out.push(...badCharFields(v, child));
    }
  }
  return out;
}

function validateManifest(m) {
  const errors = [];
  for (const f of REQUIRED_FIELDS) {
    if (!(f in m)) errors.push(`missing required field: ${f}`);
  }
  if (m.version !== 'prml/0.1' && m.version !== 'prml/0.2') {
    errors.push(`version must be "prml/0.1" or "prml/0.2", got "${m.version}"`);
  }
  if (typeof m.threshold !== 'number' || !Number.isFinite(m.threshold)) {
    errors.push(`threshold must be a finite number`);
  }
  if (m.comparator && !VALID_COMPARATORS.has(m.comparator)) {
    errors.push(`comparator must be one of ${[...VALID_COMPARATORS].join(', ')}`);
  }
  if (m.dataset && typeof m.dataset === 'object') {
    for (const f of REQUIRED_DATASET) {
      if (!(f in m.dataset)) errors.push(`missing required field: dataset.${f}`);
    }
    if (m.dataset.hash && !/^[0-9a-f]{64}$/.test(m.dataset.hash)) {
      errors.push(`dataset.hash must be 64 lowercase hex chars`);
    }
  }
  if (m.producer && typeof m.producer === 'object') {
    for (const f of REQUIRED_PRODUCER) {
      if (!(f in m.producer)) errors.push(`missing required field: producer.${f}`);
    }
  }
  for (const fld of badCharFields(m)) {
    errors.push(`${fld}: contains a control / non-portable character `
      + `(C0/C1, U+007F, U+2028/U+2029, or U+FEFF) — not allowed in a PRML string field`);
  }
  return errors;
}

// ─────────────────────────────────────────────────────────────────────────
// Verifier
// ─────────────────────────────────────────────────────────────────────────

const EXIT_PASS = 0;
const EXIT_BAD = 2;       // bad input / spec: unreadable, unparseable, invalid manifest, bad --observed
const EXIT_TAMPERED = 3;
const EXIT_FAIL = 10;
const EXIT_GUARD = 11;    // environmental guard: missing sidecar / missing lib

function evaluatePredicate(observed, comparator, threshold) {
  switch (comparator) {
    case '>=': return observed >= threshold;
    case '<=': return observed <= threshold;
    case '>':  return observed >  threshold;
    case '<':  return observed <  threshold;
    case '==': return observed === threshold;
    default: throw new Error('invalid comparator: ' + comparator);
  }
}

// ─────────────────────────────────────────────────────────────────────────
// CLI
// ─────────────────────────────────────────────────────────────────────────

function cmdInit(name) {
  const dir = path.join('.falsify', name);
  fs.mkdirSync(dir, { recursive: true });
  const skeleton = {
    version: 'prml/0.1',
    claim_id: '01900000-0000-0000-0000-000000000000',
    created_at: new Date().toISOString().replace(/\.\d+/, ''),
    metric: 'accuracy',
    comparator: '>=',
    threshold: 0.0,
    dataset: { id: 'PLACEHOLDER', hash: '0'.repeat(64) },
    seed: 0,
    producer: { id: 'PLACEHOLDER' },
  };
  const yamlText = canonicalize(skeleton);
  fs.writeFileSync(path.join(dir, 'spec.yaml'), yamlText);
  console.log(`init: wrote ${dir}/spec.yaml`);
  console.log('Edit the placeholder values, then run: falsify-js lock ' + dir + '/spec.yaml');
  return EXIT_PASS;
}

// Reject prototype-polluting keys anywhere in a parsed manifest. Returns the
// object unchanged if clean; throws otherwise. Bounded depth as a DoS guard.
function assertNoProtoKeys(o, depth) {
  depth = depth || 0;
  if (depth > 100) throw new Error('manifest nesting too deep');
  if (o && typeof o === 'object') {
    for (const k of Object.keys(o)) {
      if (k === '__proto__' || k === 'constructor' || k === 'prototype') {
        throw new Error('manifest contains a disallowed key: ' + k);
      }
      assertNoProtoKeys(o[k], depth + 1);
    }
  }
  return o;
}

function loadManifest(filePath) {
  // Minimal YAML loader for our canonical format only.
  // We intentionally do NOT use a generic YAML parser: round-tripping
  // through one risks breaking determinism. For load-and-canonicalize
  // workflows, prefer the Python reference impl which uses PyYAML.
  // For now we require JSON input to this tool; YAML support requires js-yaml.
  if (filePath.endsWith('.json')) {
    const raw = fs.readFileSync(filePath, 'utf-8');
    return assertNoProtoKeys(JSON.parse(raw));
  }
  // Otherwise use js-yaml if available (optional dependency).
  let yaml;
  try {
    yaml = require('js-yaml');
  } catch (e) {
    throw new Error('YAML loading requires js-yaml: npm install js-yaml. Or pass a .json file.');
  }
  // CORE_SCHEMA: no custom/JS type tags (e.g. !!js/function) can be
  // instantiated from untrusted manifest content.
  const parsed = yaml.load(fs.readFileSync(filePath, 'utf-8'), { schema: yaml.CORE_SCHEMA });
  return assertNoProtoKeys(parsed);
}

function cmdLock(filePath) {
  const m = loadManifest(filePath);
  const errors = validateManifest(m);
  if (errors.length) {
    console.error('lock: invalid manifest:');
    errors.forEach(e => console.error('  - ' + e));
    return EXIT_BAD;
  }
  const canonical = canonicalize(m);
  const hash = crypto.createHash('sha256').update(canonical, 'utf-8').digest('hex');
  const sidecar = filePath.replace(/\.[^.]+$/, '') + '.prml.sha256';
  fs.writeFileSync(sidecar, hash + '\n');
  console.log(`locked: ${filePath}`);
  console.log(`  canonical bytes: ${canonical.length}`);
  console.log(`  sha256:          ${hash}`);
  console.log(`  sidecar:         ${sidecar}`);
  return EXIT_PASS;
}

function cmdVerify(filePath, observedStr) {
  const m = loadManifest(filePath);
  const errors = validateManifest(m);
  if (errors.length) {
    console.error('verify: invalid manifest:');
    errors.forEach(e => console.error('  - ' + e));
    return EXIT_BAD;
  }
  const canonical = canonicalize(m);
  const computed = crypto.createHash('sha256').update(canonical, 'utf-8').digest('hex');
  const sidecar = filePath.replace(/\.[^.]+$/, '') + '.prml.sha256';
  if (!fs.existsSync(sidecar)) {
    console.error(`verify: sidecar not found: ${sidecar}`);
    return EXIT_GUARD;
  }
  const claimedHash = fs.readFileSync(sidecar, 'utf-8').trim();
  if (computed !== claimedHash) {
    console.error('TAMPERED');
    console.error(`  recorded:    ${claimedHash}`);
    console.error(`  recomputed:  ${computed}`);
    return EXIT_TAMPERED;
  }
  if (observedStr === undefined) {
    console.log(`hash OK: ${computed}`);
    console.log('(no --observed value given; predicate not evaluated)');
    return EXIT_PASS;
  }
  const observed = parseFloat(observedStr);
  if (!Number.isFinite(observed)) {
    console.error('verify: --observed must be a finite number');
    return EXIT_BAD;
  }
  const ok = evaluatePredicate(observed, m.comparator, m.threshold);
  if (ok) {
    console.log(`PASS  metric=${m.metric}  observed=${observed}  ${m.comparator}  threshold=${m.threshold}`);
    return EXIT_PASS;
  } else {
    console.log(`FAIL  metric=${m.metric}  observed=${observed}  NOT ${m.comparator}  threshold=${m.threshold}`);
    return EXIT_FAIL;
  }
}

function cmdTestVectors(vectorsPath) {
  const raw = fs.readFileSync(vectorsPath, 'utf-8');
  // Substitute large integers with sentinel-wrapped strings before JSON.parse
  // so we can preserve precision (JS Number loses precision above 2^53).
  const wrapped = raw.replace(/(?<=[\s:,\[])(\-?\d{16,})(?=[\s,\]\}])/g, '"__BIGINT__$1"');
  const vectors = JSON.parse(wrapped);
  function unwrap(o) {
    if (typeof o === 'string' && o.startsWith('__BIGINT__')) return BigInt(o.slice(10));
    if (Array.isArray(o)) return o.map(unwrap);
    if (o !== null && typeof o === 'object') {
      const out = {};
      for (const k of Object.keys(o)) out[k] = unwrap(o[k]);
      return out;
    }
    return o;
  }
  for (const v of vectors) v.input = unwrap(v.input);

  let pass = 0, fail = 0;
  for (const v of vectors) {
    const produced = canonicalize(v.input);
    const producedHash = crypto.createHash('sha256').update(produced, 'utf-8').digest('hex');
    const ok = produced === v.canonical && producedHash === v.hash;
    if (ok) {
      pass++;
      console.log(`PASS  ${v.id}  ${v.title}`);
    } else {
      fail++;
      console.log(`FAIL  ${v.id}  ${v.title}`);
      const a = v.canonical, b = produced;
      let i = 0;
      while (i < a.length && i < b.length && a[i] === b[i]) i++;
      console.log(`        first diff @ char ${i}`);
      console.log(`        expected: ${JSON.stringify(a.slice(Math.max(0,i-10), i+30))}`);
      console.log(`        produced: ${JSON.stringify(b.slice(Math.max(0,i-10), i+30))}`);
    }
  }
  console.log(`\nResult: ${pass}/${vectors.length} vectors passed.`);
  return fail === 0 ? EXIT_PASS : EXIT_FAIL;
}

function usage() {
  process.stderr.write(`falsify-js — PRML v0.1 reference implementation (Node.js)

Commands:
  init <name>                            create skeleton in .falsify/<name>/
  lock <spec.json|spec.yaml>             canonicalize, hash, write sidecar
  verify <spec.json> [--observed <v>]    verify hash; if --observed, evaluate
  test-vectors <vectors.json>            run conformance suite
  hash <spec.json>                       print canonical SHA-256 only

Exit codes: 0=PASS, 2=BAD (bad input/spec), 3=TAMPERED, 10=FAIL, 11=GUARD (missing sidecar/lib)
Spec:    https://spec.falsify.dev/v0.1
`);
  return EXIT_GUARD;
}

function cmdHash(filePath) {
  const m = loadManifest(filePath);
  // Validate before hashing: an invalid or non-portable manifest would
  // otherwise emit a hash the other reference impls reject — a silent,
  // non-portable commitment. Matches lock/verify here and the Go/Rust impls.
  const errors = validateManifest(m);
  if (errors.length) {
    console.error('hash: invalid manifest:');
    errors.forEach(e => console.error('  - ' + e));
    return EXIT_BAD;
  }
  console.log(manifestHash(m));
  return EXIT_PASS;
}

function main(argv) {
  const args = argv.slice(2);
  if (args.length === 0) return usage();
  const cmd = args[0];
  try {
    switch (cmd) {
      case 'init':         return cmdInit(args[1] || 'default');
      case 'lock':         return cmdLock(args[1]);
      case 'verify': {
        const idx = args.indexOf('--observed');
        const observed = idx >= 0 ? args[idx + 1] : undefined;
        return cmdVerify(args[1], observed);
      }
      case 'test-vectors': return cmdTestVectors(args[1]);
      case 'hash':         return cmdHash(args[1]);
      case '-h':
      case '--help':       return usage() === EXIT_GUARD ? EXIT_PASS : EXIT_PASS;
      default:             return usage();
    }
  } catch (e) {
    // Unreadable file, malformed JSON/YAML — bad input (EXIT_BAD=2), matching
    // the Python reference, not an environmental guard.
    console.error(`${cmd}: ${e.message}`);
    return EXIT_BAD;
  }
}

if (require.main === module) {
  process.exit(main(process.argv));
}

// Programmatic API for embedders
module.exports = {
  canonicalize,
  manifestHash,
  validateManifest,
  evaluatePredicate,
  needsQuoting,
  EXIT_PASS, EXIT_BAD, EXIT_TAMPERED, EXIT_FAIL, EXIT_GUARD,
};
