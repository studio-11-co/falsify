# mastra × PRML — lock the scoring bar before the run

Mastra's scorer results record the **run**. PRML is the receipt of the **bar**: the scorer's
id, the pass threshold, and the exact test set (content-hashed) — committed to a SHA-256
**before** any score exists, so none of them can be quietly adjusted after the results are known.

```
npm i @mastra/core falsify-js
node prml_gate.mjs        # lock -> real scorer.run() -> verify -> tamper demo
```

The scorer is real `@mastra/core/evals` (`createScorer().generateScore()`, judge-free, runs
locally, no API key). The hashing is the real `falsify-js` reference — byte-equivalent with the
Python, Go and Rust implementations.

What it proves: the bar existed, in exactly this form, before the results did.
What it does not prove: that the scores are right — that stays with the scorer.
