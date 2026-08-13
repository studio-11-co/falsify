#!/usr/bin/env node
// prml-linkage/0 — JavaScript reference implementation (draft).
//
// Spec: spec/linkage/prml-linkage-0.md. Byte-parity with the Python
// reference (falsify_linkage.py) is asserted by tests/test_linkage_parity.py.
// Canonicalization is delegated to falsify.js, which renders linkage
// records under the same rules as PRML manifests (incl. the observed
// float rule).

'use strict';

const crypto = require('crypto');
const { canonicalize } = require('./falsify.js');

const LINKAGE_VERSION = 'prml-linkage/0';

const START_FIELDS = ['linkage_version', 'manifest_hash', 'receipt', 'run'];
const FINAL_FIELDS = START_FIELDS.concat(['start_hash', 'result']);
const RUN_FIELDS = ['id', 'started_at', 'environment', 'model_version', 'dataset_hash'];
const RESULT_FIELDS = ['observed', 'digest', 'exit_code', 'finished_at'];
const VALID_EXIT_CODES = new Set([0, 3, 10, 11]);

const SHA256_RE = /^[0-9a-f]{64}$/;
const COMPARATORS = {
  '>=': (a, b) => a >= b,
  '>': (a, b) => a > b,
  '<=': (a, b) => a <= b,
  '<': (a, b) => a < b,
  '==': (a, b) => a === b,
};

function linkageHash(record) {
  return crypto.createHash('sha256').update(canonicalize(record), 'utf-8').digest('hex');
}

function parseRfc3339(value) {
  if (typeof value !== 'string' || !/([zZ]|[+-]\d{2}:\d{2})$/.test(value)) {
    throw new Error(`timestamp lacks timezone: ${value}`);
  }
  const ms = Date.parse(value);
  if (Number.isNaN(ms)) throw new Error(`not RFC 3339: ${value}`);
  return ms;
}

function nowUtc() {
  // Millisecond precision: sub-second runs must still satisfy the spec's
  // strict started_at < finished_at chronology.
  return new Date().toISOString();
}

function buildStart(manifestHashHex, runId, environment, datasetHash, opts = {}) {
  if (!SHA256_RE.test(manifestHashHex)) throw new Error('manifest_hash must be 64 lowercase hex chars');
  if (!SHA256_RE.test(datasetHash)) throw new Error('dataset_hash must be 64 lowercase hex chars');
  const startedAt = opts.startedAt || nowUtc();
  parseRfc3339(startedAt);
  return {
    linkage_version: LINKAGE_VERSION,
    manifest_hash: manifestHashHex,
    receipt: opts.receipt !== undefined ? opts.receipt : null,
    run: {
      id: runId,
      started_at: startedAt,
      environment,
      model_version: opts.modelVersion !== undefined ? opts.modelVersion : null,
      dataset_hash: datasetHash,
    },
  };
}

function finalize(startRecord, observed, resultDigest, exitCode, opts = {}) {
  const problems = validateShape(startRecord, false);
  if (problems.length) throw new Error(`invalid start record: ${problems.join('; ')}`);
  if (!VALID_EXIT_CODES.has(exitCode)) throw new Error(`exit_code must be one of ${[...VALID_EXIT_CODES].join(',')}`);
  if (!SHA256_RE.test(resultDigest)) throw new Error('result digest must be 64 lowercase hex chars');
  const finishedAt = opts.finishedAt || nowUtc();
  parseRfc3339(finishedAt);
  return {
    linkage_version: startRecord.linkage_version,
    manifest_hash: startRecord.manifest_hash,
    receipt: startRecord.receipt,
    run: { ...startRecord.run },
    start_hash: linkageHash(startRecord),
    result: {
      // Spec float rule: observed is float64; canonicalization renders
      // integer values as "x.0" via the linkage float-field hint.
      observed: Number(observed),
      digest: resultDigest,
      exit_code: exitCode,
      finished_at: finishedAt,
    },
  };
}

function isPlainObject(v) {
  return v !== null && typeof v === 'object' && !Array.isArray(v);
}

function sameSet(actual, expected) {
  const a = [...actual].sort().join(',');
  const b = [...expected].sort().join(',');
  return a === b;
}

function validateShape(record, isFinal) {
  const problems = [];
  const expected = isFinal ? FINAL_FIELDS : START_FIELDS;
  if (!isPlainObject(record)) return ['record is not a mapping'];
  if (record.linkage_version !== LINKAGE_VERSION) {
    problems.push(`linkage_version must be '${LINKAGE_VERSION}'`);
  }
  const keys = Object.keys(record);
  const missing = expected.filter((k) => !keys.includes(k));
  const extra = keys.filter((k) => !expected.includes(k));
  if (missing.length) problems.push(`missing fields: ${missing.sort().join(',')}`);
  if (extra.length) problems.push(`unknown fields: ${extra.sort().join(',')}`);
  const run = record.run;
  if (!isPlainObject(run)) {
    problems.push('run is not a mapping');
  } else {
    if (!sameSet(Object.keys(run), RUN_FIELDS)) {
      problems.push(`run fields must be exactly ${RUN_FIELDS.slice().sort().join(',')}`);
    }
    if (!(typeof run.dataset_hash === 'string' && SHA256_RE.test(run.dataset_hash))) {
      problems.push('run.dataset_hash must be 64 lowercase hex chars');
    }
    try { parseRfc3339(String(run.started_at)); } catch { problems.push('run.started_at is not RFC 3339'); }
  }
  if (!(typeof record.manifest_hash === 'string' && SHA256_RE.test(record.manifest_hash))) {
    problems.push('manifest_hash must be 64 lowercase hex chars');
  }
  if (isFinal) {
    if (!(typeof record.start_hash === 'string' && SHA256_RE.test(record.start_hash))) {
      problems.push('start_hash must be 64 lowercase hex chars');
    }
    const result = record.result;
    if (!isPlainObject(result)) {
      problems.push('result is not a mapping');
    } else {
      if (!sameSet(Object.keys(result), RESULT_FIELDS)) {
        problems.push(`result fields must be exactly ${RESULT_FIELDS.slice().sort().join(',')}`);
      }
      if (!VALID_EXIT_CODES.has(result.exit_code)) {
        problems.push('result.exit_code must be one of 0,3,10,11');
      }
      if (!(typeof result.digest === 'string' && SHA256_RE.test(result.digest))) {
        problems.push('result.digest must be 64 lowercase hex chars');
      }
      try { parseRfc3339(String(result.finished_at)); } catch { problems.push('result.finished_at is not RFC 3339'); }
    }
  }
  return problems;
}

function verify(finalRecord, opts = {}) {
  const { startRecord = null, manifest = null } = opts;
  let manifestHashHex = opts.manifestHash || null;
  const failures = [];
  const skipped = [];

  const problems = validateShape(finalRecord, true);
  if (problems.length) {
    return {
      ok: false,
      tier: null,
      failures: problems.map((p) => ({ check: 'malformed', detail: p })),
      skipped: [],
    };
  }

  let tier = 'L1';
  if (startRecord !== null) {
    tier = 'L2';
    if (linkageHash(startRecord) !== finalRecord.start_hash) {
      failures.push({ check: 'chain-broken', detail: 'hash(start) != start_hash' });
    } else {
      for (const key of START_FIELDS) {
        if (canonicalize({ v: startRecord[key] }) !== canonicalize({ v: finalRecord[key] })) {
          failures.push({ check: 'chain-broken', detail: `field '${key}' differs between start and final` });
        }
      }
    }
  } else {
    skipped.push('chain (no start record supplied)');
  }

  const started = parseRfc3339(finalRecord.run.started_at);
  const finished = parseRfc3339(finalRecord.result.finished_at);
  if (!(started < finished)) {
    failures.push({ check: 'chronology', detail: 'started_at is not before finished_at' });
  }

  if (manifest !== null && manifestHashHex === null) {
    manifestHashHex = crypto.createHash('sha256').update(canonicalize(manifest), 'utf-8').digest('hex');
  }

  if (manifestHashHex !== null) {
    if (finalRecord.manifest_hash !== manifestHashHex) {
      failures.push({ check: 'manifest-mismatch', detail: 'manifest_hash differs' });
    }
  } else {
    skipped.push('manifest hash (no manifest supplied)');
  }

  if (manifest !== null) {
    const mDataset = (manifest.dataset || {}).hash;
    if (finalRecord.run.dataset_hash !== mDataset) {
      failures.push({ check: 'dataset-mismatch', detail: 'run.dataset_hash != manifest dataset.hash' });
    }
    const comparator = manifest.comparator;
    const threshold = manifest.threshold;
    const exitCode = finalRecord.result.exit_code;
    if (COMPARATORS[comparator] && typeof threshold === 'number' && (exitCode === 0 || exitCode === 10)) {
      const passed = COMPARATORS[comparator](finalRecord.result.observed, threshold);
      const expected = passed ? 0 : 10;
      if (exitCode !== expected) {
        failures.push({
          check: 'verdict-mismatch',
          detail: `observed vs threshold implies exit ${expected}, record says ${exitCode}`,
        });
      }
    } else if (exitCode === 3 || exitCode === 11) {
      skipped.push('verdict recompute (error exit code)');
    }
  } else {
    skipped.push('dataset + verdict (no manifest supplied)');
  }

  return { ok: failures.length === 0, tier, failures, skipped };
}

module.exports = {
  LINKAGE_VERSION,
  linkageHash,
  buildStart,
  finalize,
  verify,
  validateShape,
};
