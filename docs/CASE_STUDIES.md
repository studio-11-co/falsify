# Case studies

Three short, concrete scenarios describing how teams in different
contexts would adopt falsify. The specifics are illustrative; the
workflows are literal — every command shown works in v0.1.0.

### Case 1: ML team shipping a recommendation model

**Context.** A 20-person ML team at a B2C product company retrains
a ranking model weekly. Their internal SLO is a single line of
policy: *offline NDCG@10 stays above 0.42 before any model gets
promoted to staging.* That line has lived in a Confluence page
since the SLO was adopted. Last month somebody quietly lowered the
bar to 0.40 to unblock a release; nobody noticed until a customer
complained about worse results and a postmortem surfaced the edit.

**What falsify adds.** The SLO stops being a line in a doc and
becomes a locked [claim](GLOSSARY.md#claim) whose [spec
hash](GLOSSARY.md#hash-spec-hash) is part of the repo. Any attempt
to lower the bar without an [honest
relock](GLOSSARY.md#honest-relock) fails CI with exit code `3`.

**Workflow.**

    falsify-engine init --template accuracy --name ranking_ndcg
    # edit claims/ranking_ndcg/spec.yaml to point metric_fn at the
    # team's NDCG implementation and set threshold = 0.42
    falsify-engine lock ranking_ndcg
    git add .falsify/ranking_ndcg/spec.lock.json \
            claims/ranking_ndcg/
    git commit -m "Lock NDCG@10 >= 0.42 claim"

    # CI step on every PR:
    falsify-engine run ranking_ndcg && falsify-engine verdict ranking_ndcg

**What they get.** A PR that edits `spec.yaml` to lower the
threshold without `--force` produces exit code `3` and a clear
"spec modified after lock" message. Model promotions are gated on
`falsify-engine verdict` exit `0`. Weekly `make dogfood` keeps the three
self-claims green so the team knows the tool itself has not
regressed.

**Operational rhythm.** Quarterly, the team runs
`falsify-engine export --output q2_audit.jsonl` followed by
`falsify-engine verify q2_audit.jsonl` — a single command chain that
hands their audit committee a replayable, tamper-evident record of
every threshold ever shipped.

The threshold is still the team's call. But lowering it now
leaves a hash trail.

### Case 2: DevOps team guarding p95 API latency

**Context.** A platform team at a fintech runs a public API with a
p95 latency SLO of 200ms. Three days after a misconfigured retry
policy landed, somebody finally noticed that p95 had doubled.
Grafana had been showing the spike the whole time — there just
wasn't anything blocking the deploy that caused it.

**What falsify adds.** Observability *reports*; falsify *gates*.
A locked latency claim turns "the deploy is bad" from a dashboard
story into a CI exit code the merge queue can read.

**Workflow.**

    falsify-engine init --template latency --name api_p95
    # edit claims/api_p95/metric.py to query the Prometheus export
    # for the last hour and return (p95_ms, sample_count)
    falsify-engine lock api_p95
    git add .falsify/api_p95/spec.lock.json claims/api_p95/
    git commit -m "Lock public-API p95 latency claim (< 200ms)"

    # CI step on every PR that touches api/* paths:
    falsify-engine run api_p95 && falsify-engine verdict api_p95

**PR-review integration.** The team wires the
[`claim-review`](../.claude/skills/claim-review/SKILL.md) Claude
skill into their PR automation. Any diff that touches
`api_p95/spec.yaml` (threshold bump, direction flip,
`metric_fn` swap) gets a review comment before a human reviewer
sees it.

**What they get.** The next time a retry tweak lands, the
`api_p95` run returns `p95_ms = 380` and `falsify-engine verdict` exits
`10`. The merge queue refuses the PR within minutes — instead of
silent drift over days. If somebody tries to "fix" CI by editing
the threshold, the commit that does it is the commit that runs
`lock --force` and writes a new hash to the audit trail.

**Shared side effect.** Every p95 run adds a line to the
exportable [audit trail](GLOSSARY.md#audit-trail). Incident
review no longer has to dig through Grafana screenshots to prove
the SLO was ever actually green.

### Case 3: Research group pre-registering an LLM evaluation

**Context.** A four-person research group is evaluating an
open-weights LLM on a private reasoning benchmark. The paper will
be read by external reviewers, so the evaluation needs to be
credible — which means pre-registering the claim before anyone
touches the test set.

**What falsify adds.** Pre-registration platforms exist
(OSF, AsPredicted) but they don't run in CI and they don't hash
the spec. falsify does both; the lock file *is* the
pre-registration artifact, and the git tag *is* the proof-of-time.

**Workflow.**

    falsify-engine init --template llm-judge --name reasoning_bench_v1
    # edit claims/reasoning_bench_v1/metric.py to invoke the team's
    # judge harness; set threshold = 0.75 agreement
    falsify-engine lock reasoning_bench_v1

    # commit the lock BEFORE the test set is ever touched:
    git add claims/reasoning_bench_v1/ \
            .falsify/reasoning_bench_v1/spec.lock.json
    git commit -m "Pre-register reasoning bench claim (agreement >= 0.75) before test set"
    git tag pre-registration-reasoning-v1

Later, once the test set is ready:

    falsify-engine run reasoning_bench_v1
    falsify-engine verdict reasoning_bench_v1     # PASS or FAIL is on record
    falsify-engine export --output reasoning_v1_audit.jsonl

**What reviewers see.** The git tag proves the claim was locked
before the evaluation ran. The audit JSONL is replayable
end-to-end via `falsify-engine replay <run_id>`, so a skeptical reviewer
can reproduce the verdict on their own machine using only the
repo and the private test set.

**Outcome.** The paper cites the commit SHA of the pre-registration
line. A follow-up evaluation that revisits the threshold must
`lock --force` and leave its own entry in the audit log — so
readers can see not just the final number but the history of how
the bar moved.

falsify does not replace OSF for formal publication. It makes the
fastest path the honest one.

### Shared patterns

Three very different teams; four recurring moves:

- **Lock before running.** Every case creates the lock file before
  a single run is invoked. [Pre-registration](GLOSSARY.md#pre-registration)
  is the only discipline all three cases share, because it is the
  only one that closes the threshold-drift loophole.
- **Commit the lock file.** The spec hash lives in git alongside
  the code it guards. No hash, no pre-registration.
- **CI treats exit codes as policy.** `0` merges, `3` and `10`
  block, `2` surfaces an INCONCLUSIVE run. No custom parsing, no
  bespoke dashboards.
- **The honest path is always fast.** `lock --force` takes one
  command and writes one audit line. The dishonest path — editing
  the spec and hoping nobody notices — is the one that gets
  caught.

None of the three cases required more than ~30 minutes of setup.
The ongoing cost is one CI step per claim; the reward is that the
claim cannot move silently.

### Further reading

- [TUTORIAL.md](../TUTORIAL.md) — 15-minute hands-on walkthrough
  from zero to first locked claim.
- [docs/EXAMPLES.md](EXAMPLES.md) — five template walkthroughs
  (`accuracy`, `latency`, `brier`, `llm-judge`, `ab`).
- [docs/COMPARISON.md](COMPARISON.md) — feature matrix versus
  MLflow, W&B, DVC, OSF, pytest, pre-commit.
- [docs/FAQ.md](FAQ.md) — "why not just X?" objections addressed
  in detail.
- [docs/ADVERSARIAL.md](ADVERSARIAL.md) — the threat model
  behind the lock discipline.
