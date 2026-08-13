#!/usr/bin/env node
// Cross-language parity target for prml-linkage/0.
//
// Reads one JSON request on stdin, writes one JSON response on stdout.
//   {"mode":"canonical","record":{...}}
//     → {"canonical":"...","hash":"..."}
//   {"mode":"finalize","start":{...},"observed":N,"digest":"...","exit_code":N,"finished_at":"..."}
//     → {"final":{...},"hash":"..."}
//   {"mode":"verify","final":{...},"start":{...}|null,"manifest":{...}|null}
//     → {"ok":bool,"tier":...,"failures":[...],"skipped":[...]}
// Used by tests/test_linkage_parity.py; not part of the public API.

'use strict';

const { canonicalize } = require('./falsify.js');
const linkage = require('./linkage.js');
const crypto = require('crypto');

let input = '';
process.stdin.on('data', (d) => { input += d; });
process.stdin.on('end', () => {
  const req = JSON.parse(input);
  let out;
  if (req.mode === 'canonical') {
    const canonical = canonicalize(req.record);
    out = {
      canonical,
      hash: crypto.createHash('sha256').update(canonical, 'utf-8').digest('hex'),
    };
  } else if (req.mode === 'finalize') {
    const final = linkage.finalize(req.start, req.observed, req.digest, req.exit_code, {
      finishedAt: req.finished_at,
    });
    out = { final, hash: linkage.linkageHash(final) };
  } else if (req.mode === 'verify') {
    out = linkage.verify(req.final, {
      startRecord: req.start || null,
      manifest: req.manifest || null,
    });
  } else {
    throw new Error(`unknown mode: ${req.mode}`);
  }
  process.stdout.write(JSON.stringify(out));
});
