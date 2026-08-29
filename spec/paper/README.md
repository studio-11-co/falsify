# PRML v0.1 — arXiv Preprint

**File:** `prml-v0.1-preprint.tex` (694 lines, ~12 page output)
**Author:** Cüneyt Öztürk
**Target arXiv categories:** `cs.CR` (primary), `cs.CY` (cross), `cs.SE` (cross)

---

## Build to PDF (no local TeX required)

The fastest path: **Overleaf** (free, no install).

1. Go to https://www.overleaf.com → Sign up (free).
2. New Project → Upload Project → upload only `prml-v0.1-preprint.tex`.
3. Click "Recompile" — PDF builds in ~10 seconds.
4. Download PDF + `.tex` source for arXiv.

If you prefer local: install MacTeX (`brew install --cask mactex-no-gui`, ~2GB), then:
```bash
cd spec/paper
pdflatex prml-v0.1-preprint.tex
pdflatex prml-v0.1-preprint.tex   # second pass for refs
```

---

## Submit to arXiv

### 1. arXiv account

If no account: register at https://arxiv.org/user/register
- Use email: `hello@falsify.dev` (matches paper correspondence)
- Affiliation: `Independent`
- ORCID optional but boosts credibility

### 2. Endorsement

arXiv requires endorsement for first-time submissions in cs.* categories.

**Strategy:**
- **First try:** submit to `cs.CR` (Cryptography and Security) — endorsement bar is lower than `cs.LG`
- **If rejected for endorsement:** the email arXiv sends includes an endorsement code. Forward to:
  1. Gary Marcus (already in our endorsement email loop)
  2. Any prior arXiv author in our network (LinkedIn search)
  3. As a last resort, post in the falsify GitHub Discussion #6 asking for an endorsement

### 3. Submission flow

1. arxiv.org → "Submit" → "New submission"
2. License: **CC BY 4.0** for the preprint (the spec itself moved to the Community Specification License 1.0 on 2026-08-29)
3. Categories:
   - Primary: `cs.CR`
   - Cross-list: `cs.CY`, `cs.SE`
4. Upload: `prml-v0.1-preprint.tex` (and PDF if available — arXiv prefers source)
5. Title: *Pre-Registered ML Manifests: A Content-Addressed Format for Verifiable Evaluation Claims*
6. Abstract: copy from `\begin{abstract}` block in the tex file
7. Comments field: "Working draft v0.1; spec at spec.falsify.dev/v0.1; reference implementation at github.com/studio-11-co/falsify; v0.2 freeze 2026-05-22"
8. Submit → wait for moderation (typically 1-3 business days)

### 4. After acceptance

- arXiv assigns a permanent ID like `arXiv:2605.XXXXX`
- Add this ID to spec.falsify.dev/v0.1 footer
- Add to GitHub README
- Post to LinkedIn / X as standalone update: "PRML v0.1 preprint now on arXiv: [link]"

---

## Fallback: real-name submission

If the anonymous identity fails moderation:

1. Re-edit `\author[1]{Cüneyt Öztürk}` → `\author[1]{Cüneyt Öztürk}`
2. `\affil[1]{Independent...` → `\affil[1]{Cüneyt Öztürk, Independent. Correspondence: hello@falsify.dev`
3. Re-upload to same arXiv submission (use "replace" before moderation, "v2" after)

---

## Status

- [x] LaTeX draft written (2026-05-01)
- [ ] Compile to PDF on Overleaf
- [ ] Read-through (catch typos, broken refs)
- [ ] arXiv account created (or use existing)
- [ ] Endorsement obtained
- [ ] Submitted to cs.CR
- [ ] Accepted + arXiv ID assigned
- [ ] Cross-promote in spec footer / GitHub / social
