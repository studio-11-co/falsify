> **Superseded 26 Sep 2026.** The current 60-second demo is the acceptance-record walkthrough (`spec/demo/index.html`, rendered to `spec/demo/demo.mp4` and `demo.gif`); every value in it comes from `examples/acceptance-record/`. This storyboard describes the earlier PRML walkthrough and is kept for history.

# Demo video script — 90 seconds

## Target

90-second run-time, 1080p60, silent-compatible with captions burned
in. Human voiceover preferred — the creator's voice reads
cleaner at this pace than any TTS. Fallback: ElevenLabs "Adam"
(lower register, slower). No on-camera presenter. Designed for
end-to-end offline recording; no live typing.

The first 8 seconds decide whether a hackathon juror keeps watching.
Everything before 0:08 must earn the next 82.

## Pacing principle

- **0:00-0:08 HOOK.** Concrete, unforgettable, specific. One number
  that went wrong and cost someone something real.
- **0:08-0:18 PROMISE.** One sentence: what falsify does and why it
  is different from tests, CI, or linting.
- **0:18-1:10 PROOF.** Live terminal. Lock, run, tamper, block,
  relock. The audit trail writes itself.
- **1:10-1:22 SCALE.** Claude Code composition — 5 skills, 2
  subagents, 3 slash commands, 1 MCP server. Why the workflow
  matters, not just the CLI.
- **1:22-1:30 CLOSE.** One sentence, one URL. Silence.

## Shot list

| Time       | Dur. | Shot                              | Voiceover                                                                                                                      | On-screen text                             | Terminal command                                                                                |
|------------|------|-----------------------------------|--------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------|-------------------------------------------------------------------------------------------------|
| 0:00-0:08  | 8s   | Close-up of a release note.       | Your team claims ninety-four percent accuracy. You ship it. Three weeks later a customer proves the real number is seventy-one. | 94 percent -> 71 percent                    | (none)                                                                                          |
| 0:08-0:18  | 10s  | Text slide, dissolve.             | The claim was never falsifiable. Nobody locked the metric, the threshold, or the dataset before the experiment ran.            | not falsifiable                            | (none)                                                                                          |
| 0:18-0:26  | 8s   | Title card, falsify logo cut-in.  | Falsify fixes that. Pre-register the claim with a cryptographic hash before you see the data.                                  | Falsify. Lock the claim before the data.  | (none)                                                                                          |
| 0:26-0:40  | 14s  | Terminal; scaffold + lock.        | Scaffold a claim from a template. Lock it. A SHA-256 hash fingerprints the spec.                                               | hash = spec fingerprint                    | `falsify init --template accuracy --name acc && falsify lock acc`                               |
| 0:40-0:54  | 14s  | Terminal; green PASS line.        | Run the experiment. The verdict is PASS. Exit code zero. CI passes.                                                            | PASS. exit 0.                              | `falsify run acc && falsify verdict acc; echo "exit: $?"`                                        |
| 0:54-1:08  | 14s  | Terminal; red exit-3 flash.       | Now watch a tamper. Edit the threshold silently. Run again. Exit code three. The lie is blocked automatically.                 | exit 3. the lie is blocked.                | `sed -i '' 's/0.80/0.70/' .falsify/acc/spec.yaml && falsify run acc; echo "exit: $?"`            |
| 1:08-1:18  | 10s  | Terminal; JSONL audit scroll.     | The honest fix re-locks with force. The audit trail writes itself.                                                             | Relock leaves an audit entry.              | `falsify lock acc --force && falsify export --output audit.jsonl && head -2 audit.jsonl`         |
| 1:18-1:26  | 8s   | Three fast cuts, 2.5s each.       | Five Claude Code skills, two subagents, three slash commands, and one Model Context Protocol server compose the workflow.      | 5 skills. 2 agents. 3 commands. 1 MCP.    | `/new-claim acc` -> claim-review agent -> MCP honesty query                                      |
| 1:26-1:30  | 4s   | End card. Fade out.               | Lock the claim before the data. Or it didn't happen.                                                                           | github.com/studio-11-co/falsify                  | (none)                                                                                          |

Transition convention: hard cut between terminal shots; dissolve
between text slides; text overlays fade in at 120ms, hold, fade
out at 120ms.

## Voiceover full script (90 seconds at 125 WPM)

Record this as one take against the shot list. Sentences kept
under 15 words, no contractions, no idioms, no passive voice.
Target pace is 125 words per minute. 12 seconds of silent
terminal action are embedded around the money shots.

> Your team claims ninety-four percent accuracy. You ship it.
> Three weeks later a customer proves the real number is
> seventy-one. The claim was never falsifiable. Nobody locked
> the metric, the threshold, or the dataset before the
> experiment ran. Tests still passed. Code review still approved.
> The number was simply wrong, and nothing in the pipeline was
> built to catch it. Falsify fixes that. Pre-register the claim
> with a cryptographic hash before you see the data. Scaffold
> a claim from a template. Lock it. A SHA-256 hash fingerprints
> the spec. Run the experiment. The verdict is PASS. Exit code
> zero. Continuous integration passes. Now watch a tamper. Edit
> the threshold silently. Run again. Exit code three. The lie
> is blocked automatically. The honest fix re-locks with force,
> and the audit trail writes itself. Every past verdict stays
> cryptographically chained. Every reviewer can replay the
> experiment. Every number in a release note now carries its
> own proof of origin. Five Claude Code skills, two subagents,
> three slash commands, and one Model Context Protocol server
> compose the workflow. Lock the claim before the data. Or it
> did not happen.

## Hook alternatives (test all three, keep the best)

A single hook decides the video. Record each of these three,
show them to two people without context, ask which one makes
them want to keep watching. Use that one.

1. **Customer ambush (current primary).** Your team claims
   ninety-four percent accuracy. You ship it. Three weeks later
   a customer proves the real number is seventy-one.
2. **Silent relaxation.** Someone on your team lowered the
   accuracy threshold last Tuesday. The tests still pass. You
   did not notice.
3. **Paper review.** A reviewer asks to reproduce your paper's
   benchmark. You try. The number is different. You have no
   way to prove which run was the honest one.

All three end in the same pivot: "The claim was never
falsifiable." Keep the pivot regardless of which hook wins.

## Recording notes

- Record at 1080p60. Terminal capture via `asciinema` plus
  `asciinema-agg` to MP4, or OBS with a window capture source.
- Terminal: fixed-width font at 18pt, 80-column width, solid
  dark background (`#0c0c0c`) for legibility. Solarized Light
  is an acceptable alternative if the recorder's screen is
  better calibrated for warm tones.
- Use a throwaway directory (`mktemp -d && cd "$_"`) so no real
  user data, shell history, or paths appear in frame.
- Record each terminal segment separately and cut in post; do
  not live-type — typos and pauses ruin the pace.
- Voiceover: record in a closet or under a thick blanket to kill
  room reflection. One take per sentence, four takes per
  sentence, keep the best. Normalize to minus 3 LUFS integrated.
- No music on top of voiceover. Optional very quiet ambient pad
  at minus 30 LUFS only if total silence feels wrong; cut it
  during the money shots (exit 3 reveal, end card).
- Color-grade the red tint for the exit-code-3 shot in post; do
  not tint the live terminal.

## Captions (burn-in for silent autoplay)

Paste this block verbatim into `demo.srt`.

    1
    00:00:00,000 --> 00:00:08,000
    Your team claims 94% accuracy. You ship it. Three weeks later a customer proves the real number is 71%.

    2
    00:00:08,000 --> 00:00:18,000
    The claim was never falsifiable. Nobody locked the metric, the threshold, or the dataset before the experiment ran.

    3
    00:00:18,000 --> 00:00:26,000
    Falsify fixes that. Pre-register the claim with a cryptographic hash before you see the data.

    4
    00:00:26,000 --> 00:00:40,000
    Scaffold a claim from a template. Lock it. A SHA-256 hash fingerprints the spec.

    5
    00:00:40,000 --> 00:00:54,000
    Run the experiment. The verdict is PASS. Exit code zero. CI passes.

    6
    00:00:54,000 --> 00:01:08,000
    Now watch a tamper. Edit the threshold silently. Run again. Exit code three. The lie is blocked automatically.

    7
    00:01:08,000 --> 00:01:18,000
    The honest fix re-locks with force. The audit trail writes itself.

    8
    00:01:18,000 --> 00:01:26,000
    5 Claude Code skills, 2 subagents, 3 slash commands, and 1 MCP server compose the workflow.

    9
    00:01:26,000 --> 00:01:30,000
    Lock the claim before the data. Or it did not happen.

## Checklist before record

- Fresh tmux session; no prior panes or history visible.
- `clear && history -c` before each take.
- `export PS1='$ '` — minimal prompt, no user, host, or path leak.
- `mktemp -d` working directory; confirm `pwd` is anonymized.
- Terminal font 18pt; window sized to 80 columns x 24 rows.
- GitHub URL rendered large in the final frame's end card.
- Verify `asciinema --version` and `asciinema-agg --version`.
- Dry-run the full sequence once without recording.
- Silence Slack, Mail, iMessage, and system notifications.
- Close all other windows to prevent accidental focus steal.
- Phone on silent, face-down, in another room.

## Checklist before upload

- Captions burned in (not sidecar SRT) for silent-autoplay.
- Audio normalized to minus 3 LUFS integrated, peaks below -1 dBTP.
- Final cut runs under 90 seconds; trim dead frames at head and tail.
- Thumbnail: freeze-frame of the exit-code-3 red flash with "exit 3"
  rendered large in white on the red tint.
- Shortened GitHub URL tested and verified in an incognito window.
- YouTube upload set to Unlisted, not Private — hackathon jurors need
  the link to resolve without a Google login.
- Video description contains: one-sentence pitch, bullet list of tech
  (Python stdlib, 1 dep, Claude Opus 4.7 co-author), GitHub link,
  submission form reference.

## Pre-submission dry run

Two hours before the submission deadline, watch the final cut with
a stranger who has never heard of falsify. After 8 seconds, pause
the video and ask them: "What is this about?" If they cannot
answer in one sentence, the hook is broken. Re-record the hook.

Do not submit a video that fails the 8-second test.
