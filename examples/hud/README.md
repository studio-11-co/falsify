# hud × PRML — lock the reward bar before the rollouts

hud's Job is the receipt of the **run**. PRML is the receipt of the **bar**: the reward
threshold, the task (by content hash of its own `Task` model — env, id, args), and the
verifier it will be graded by — all committed to a SHA-256 **before** any rollout, so none
of them can be quietly adjusted after the rewards are known.

```
python3 hud_to_prml.py                       # lock -> sample job -> verify -> tamper demo
python3 hud_to_prml.py --job-json my_job.json --threshold 0.8
```

Needs `pip install hud falsify`. No HUD account or API key: `Task` is pure data by hud's
design, and the bridge reads a Job export (a faithful built-in sample ships in the file).

What it proves: the bar existed, in exactly this form, before the results did.
What it does not prove: that the rewards are correct — that stays with hud's grading.
