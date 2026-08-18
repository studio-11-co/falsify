#!/usr/bin/env node
/**
 * mastra <-> PRML bridge — lock the scoring bar before the eval runs.
 *
 * Mastra's scorer results record WHAT was scored and what came back. Nothing
 * in that record says what the bar WAS before the run: the pass threshold,
 * the scorer's identity, the test set the claim is about. All are chosen by
 * the party publishing the number, and can be adjusted after the scores are
 * known — which no reader of the results can detect.
 *
 * THE HONEST DESIGN (same split as our Inspect and hud bridges):
 *   lock   — BEFORE the run: build a PRML manifest binding the scorer id,
 *            the pass threshold, and the test set (content-hashed) to a
 *            SHA-256 via falsify-js. The bar is sealed before any score exists.
 *   verify — AFTER the run: check the mean score against the pre-locked
 *            manifest. PASS / FAIL / TAMPERED (manifest edited after locking).
 *
 * What is real vs modelled:
 *   - The scorer and its execution: REAL @mastra/core/evals — createScorer()
 *     with a code-based generateScore step, executed via scorer.run(). No LLM,
 *     no API key: judge-free scorers run entirely locally by Mastra's design.
 *   - PRML canonicalisation + hashing + verdicts: REAL falsify-js reference
 *     (byte-equivalent with the Python/Go/Rust implementations).
 *
 * Run:  node prml_gate.mjs          (needs: npm i @mastra/core falsify-js)
 */

import { createScorer } from "@mastra/core/evals";
import { createHash, randomBytes } from "node:crypto";
import falsify from "falsify-js";
const { canonicalize, manifestHash, validateManifest, evaluatePredicate } = falsify;

// ── the eval: a tiny exact-match test set and a code-based scorer ──────────
const TESTSET = [
  { input: "capital of France", expected: "Paris" },
  { input: "2 + 2", expected: "4" },
  { input: "capital of Estonia", expected: "Tallinn" },
  { input: "square root of 81", expected: "9" },
];

// stand-in for a model under test (one deliberate miss -> mean 0.75)
const model = (q) =>
  ({ "capital of France": "Paris", "2 + 2": "4",
     "capital of Estonia": "Tartu", "square root of 81": "9" }[q]);

const exactMatch = createScorer({
  id: "exact-match",
  description: "1.0 when the output equals the expected answer, else 0.0",
}).generateScore(({ run }) => (run.output === run.expected ? 1.0 : 0.0));

// ── PRML side ──────────────────────────────────────────────────────────────
const uuid7 = (ms) => {
  const b = Buffer.concat([Buffer.from(ms.toString(16).padStart(12, "0"), "hex"), randomBytes(10)]);
  b[6] = (b[6] & 0x0f) | 0x70; b[8] = (b[8] & 0x3f) | 0x80;
  const h = b.toString("hex");
  return `${h.slice(0,8)}-${h.slice(8,12)}-${h.slice(12,16)}-${h.slice(16,20)}-${h.slice(20)}`;
};

const sha256 = (s) => createHash("sha256").update(s).digest("hex");

function buildManifest(scorer, testset, threshold, seed) {
  const now = Date.now();
  return {
    version: "prml/0.1",
    claim_id: uuid7(now),
    created_at: new Date(now).toISOString().replace(/\.\d{3}Z$/, "Z"),
    metric: "mean_score",
    // the mastra scorer this bar applies to, by its real id
    metric_args: { mastra_scorer: scorer.id ?? "exact-match" },
    comparator: ">=",
    threshold,
    dataset: {
      id: "mastra/exact-match-demo",
      // content hash over the exact test set the claim is about
      hash: sha256(JSON.stringify(testset)),
    },
    seed,
    producer: { id: "your-lab.dev" },
  };
}

async function verify(lock, scores) {
  const m = lock.manifest;
  if (manifestHash(m) !== lock.locked_sha256) {
    console.log("  verdict : TAMPERED (exit 3) — manifest changed after lock");
    return 3;
  }
  const mean = scores.reduce((a, b) => a + b, 0) / scores.length;
  const ok = evaluatePredicate(mean, m.comparator, m.threshold);
  console.log(`  observed: mean_score = ${mean}`);
  console.log(`  bar     : ${m.comparator} ${m.threshold}  on scorer '${m.metric_args.mastra_scorer}'`);
  console.log(`  verdict : ${ok ? "PASS (exit 0)" : "FAIL (exit 10)"}`);
  return ok ? 0 : 10;
}

// ── run ────────────────────────────────────────────────────────────────────
const line = () => console.log("=".repeat(70));
line();
console.log("  mastra  ->  PRML   (lock the scoring bar before the run)");
line();

console.log("\n[LOCK] before the run — seal scorer id + threshold + test set");
const manifest = buildManifest(exactMatch, TESTSET, 0.7, 42);
const errs = validateManifest(manifest);
if (errs.length) { console.error("invalid manifest:", errs); process.exit(2); }
const lock = { manifest, locked_sha256: manifestHash(manifest) };
console.log(`  dataset : ${manifest.dataset.id}  sha256:${manifest.dataset.hash.slice(0, 16)}…`);
console.log(`  bar     : mean_score >= ${manifest.threshold}`);
console.log(`  locked  : sha256:${lock.locked_sha256.slice(0, 20)}…`);

console.log("\n[RUN]  the REAL mastra scorer runs over the test set");
const scores = [];
for (const t of TESTSET) {
  const r = await exactMatch.run({ input: t.input, output: model(t.input), expected: t.expected });
  scores.push(r.score);
}
console.log(`  per-case: [${scores.join(", ")}]`);

console.log("\n[VERIFY] after the run — check the mean against the sealed bar");
const rc = await verify(lock, scores);

console.log("\n[ADVERSARIAL] the threshold is quietly lowered after seeing 0.75");
const moved = JSON.parse(JSON.stringify(lock));
moved.manifest.threshold = 0.5;
const rc2 = await verify(moved, scores);
console.log(`  -> the results record alone cannot catch this; the locked manifest does (exit ${rc2}).`);
line();
process.exit(rc);
