#!/usr/bin/env node
/**
 * promptfoo <-> PRML gate — lock the bar before `promptfoo eval` runs.
 *
 * promptfoo is unusually honest among eval tools: the success criteria live in
 * one YAML file, in the open — asserts, thresholds, test cases. But that file
 * is exactly as editable after the run as before it. The results JSON records
 * what passed; nothing records that the asserts it passed against are the
 * asserts that existed before the outputs were known. Loosen one `equals`, or
 * delete the one failing test, re-run, and the report looks identical.
 *
 * THE HONEST DESIGN (same split as our Inspect / hud / Mastra / Laminar bridges):
 *   lock   — BEFORE: read promptfooconfig.yaml, take a SHA-256 over the
 *            canonical JSON of its `tests` (the cases AND their asserts — the
 *            bar), bind it into a PRML manifest with the pass-rate threshold
 *            you commit to, and lock the manifest to a digest.
 *   run    — `promptfoo eval` for real. The echo provider makes this demo
 *            deterministic and offline; swap in any real provider freely.
 *   verify — AFTER: read the results file promptfoo wrote, recompute the bar's
 *            hash from the config AS IT IS NOW, check both:
 *              - the bar is untouched (config hash still matches the manifest)
 *              - pass rate clears the pre-committed threshold
 *            Exit 0 PASS / 10 FAIL / 3 TAMPERED.
 *
 * Everything here is real: a real `promptfoo eval` subprocess end to end (no
 * mocked scores, no sample output), and the real `falsify-js` reference for
 * canonical bytes, manifest hash and verdicts.
 *
 * Run:  node prml_gate.mjs
 * Needs: npm install promptfoo falsify-js
 */

import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { readFileSync, writeFileSync, copyFileSync } from "node:fs";

import * as yaml from "js-yaml"; // promptfoo's own YAML dependency
import {
  canonicalize,
  manifestHash,
  validateManifest,
  evaluatePredicate,
} from "falsify-js";

const EXIT_PASS = 0, EXIT_TAMPERED = 3, EXIT_FAIL = 10;
const CONFIG = "promptfooconfig.yaml";

// ── lock: seal the bar before anything runs ─────────────────────────────────

/** SHA-256 over canonical JSON (sorted keys, compact) of the config's `tests`
 *  — the cases and their asserts together. "Same bar" is a byte-level claim. */
function barHash(configPath) {
  const cfg = yaml.load(readFileSync(configPath, "utf8"));
  const canonJson = (x) =>
    JSON.stringify(x, (_, v) =>
      v && typeof v === "object" && !Array.isArray(v)
        ? Object.fromEntries(Object.keys(v).sort().map((k) => [k, v[k]]))
        : v
    );
  return createHash("sha256").update(canonJson(cfg.tests)).digest("hex");
}

function lock() {
  const manifest = {
    version: "prml/0.1",
    claim_id: "01991b7a-4c2e-7f6a-8b1d-3e5f7a9c0d2e",
    created_at: "2026-08-19T10:00:00Z",
    metric: "pass_rate", // successes / (successes + failures) from promptfoo stats
    comparator: ">=",
    threshold: 0.7,
    dataset: { id: "promptfooconfig-tests-v1", hash: barHash(CONFIG) },
    seed: 42,
    producer: { id: "examples/promptfoo" },
  };
  const errors = validateManifest(manifest);
  if (errors.length) throw new Error("invalid manifest: " + errors.join("; "));
  const locked = manifestHash(manifest);
  writeFileSync("manifest.locked.json", JSON.stringify({ manifest, locked }, null, 2));
  console.log(`locked bar: pass_rate >= ${manifest.threshold}, tests ${manifest.dataset.hash.slice(0, 16)}…`);
  console.log(`manifest sha256: ${locked}\n`);
  return { manifest, locked };
}

// ── run: promptfoo itself, for real ─────────────────────────────────────────

function runEval() {
  try {
    execFileSync("npx", ["promptfoo", "eval", "-c", CONFIG, "-o", "results.json", "--no-progress-bar"], {
      stdio: ["ignore", "ignore", "inherit"],
      env: { ...process.env, PROMPTFOO_DISABLE_TELEMETRY: "1", PROMPTFOO_DISABLE_UPDATE: "1" },
    });
  } catch (e) {
    // promptfoo exits 100 when any test fails — that is a result, not an error.
    // The verdict on the run belongs to the locked bar, not to the exit code.
    if (e.status !== 100) throw e;
  }
  const results = JSON.parse(readFileSync("results.json", "utf8")).results;
  const { successes, failures } = results.stats;
  return successes / (successes + failures);
}

// ── verify: the locked bar decides, and the bar must still be the bar ───────

function verify(manifest, locked, passRate) {
  const errors = validateManifest(manifest);
  if (errors.length || manifestHash(manifest) !== locked) {
    console.log("verdict: TAMPERED — manifest does not match the pre-run lock");
    return EXIT_TAMPERED;
  }
  if (barHash(CONFIG) !== manifest.dataset.hash) {
    console.log("verdict: TAMPERED — the config's tests/asserts changed after locking");
    return EXIT_TAMPERED;
  }
  const ok = evaluatePredicate(passRate, manifest.comparator, manifest.threshold);
  console.log(`observed pass_rate = ${passRate}  vs locked bar ${manifest.comparator} ${manifest.threshold}`);
  console.log(`verdict: ${ok ? "PASS" : "FAIL"}`);
  return ok ? EXIT_PASS : EXIT_FAIL;
}

// ── demo ────────────────────────────────────────────────────────────────────

const { manifest, locked } = lock();
const passRate = runEval();
const rc = verify(manifest, locked, passRate);

console.log("\n-- adversarial 1: threshold edited 0.7 -> 0.5 AFTER the run --");
const doctored = { ...manifest, threshold: 0.5 };
if (verify(doctored, locked, passRate) !== EXIT_TAMPERED) throw new Error("tamper 1 not caught");

console.log("\n-- adversarial 2: the failing test deleted from the config, eval RE-RUN --");
copyFileSync(CONFIG, CONFIG + ".bak");
try {
  const cfg = yaml.load(readFileSync(CONFIG, "utf8"));
  cfg.tests = cfg.tests.slice(0, 3); // drop the failing case
  writeFileSync(CONFIG, yaml.dump(cfg));
  const doctoredRate = runEval();     // a real re-run: now a perfect 3/3
  console.log(`   (doctored config really re-run: pass_rate = ${doctoredRate})`);
  if (verify(manifest, locked, doctoredRate) !== EXIT_TAMPERED) throw new Error("tamper 2 not caught");
} finally {
  copyFileSync(CONFIG + ".bak", CONFIG);
}

process.exit(rc);
