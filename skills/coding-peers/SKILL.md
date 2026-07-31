---
name: coding-peers
description: The peer layer for coding work — who reviews, how to send them the real artifact, and what a verdict has to look like to count. Use for a bounded independent review of one settled plan, diff, seam, or generated artifact, and as the review protocol the end-to-end skills call at their gates. Read-only by default; a review request never authorizes edits. Use end-to-end-coding-session for the full loop and peer-bug-review for an exhaustive bug hunt.
---

# Coding Peers

A peer is a fresh reviewer with no memory of how the work was made. That is the
whole value: it cannot defend a decision it never took. Everything here exists to
protect that one property.

## Who reviews

| Role | In Claude | In Codex |
|---|---|---|
| Adversarial review | Sol, or an adversarial Opus subagent | Sol (`gpt-5.6-sol`) |
| Bulk labor — explorers, verifiers, batches | Sonnet subagents | Luna (`gpt-5.6-luna`) |
| Heavy implementation | Sonnet, reviewed by Opus | Terra (`gpt-5.6-terra`) |
| UI proof | `claude-in-chrome` | `computer-use:computer-use` |

The harness you are running in picks the column, never the task. Slugs name a
tier, not a version: when a model is superseded, use the newest of that tier and
leave the roles alone. This table is the only place any skill names a model.

Running in Claude, ask once at the start of the run which adversarial peer to
use, then reuse that answer for every review in the run. Never stop mid-run to
ask. No `codex` command installed means there is nothing to ask: use the Opus
subagent.

## How to send

Freeze the target before dispatch: save the exact bytes — patch, file, or plan —
and record their SHA-256 and canonical path. The peer attests to that digest, so
both sides are provably discussing the same artifact.

Send the artifact itself. A summary explains intent and cannot replace the thing
under review. In a dirty tree, build the target from only the intended files.

Each reviewer gets one focused risk question, the objective with its explicit
non-goals, and what would count as proof. Use two reviewers only when their lanes
are genuinely independent — persistence against UI, security against ordinary
correctness, a diff against the provenance of what it generates. Never put two
agents on the same broad question.

## What a verdict looks like

Require non-empty content on each label's own physical line:

```text
TARGET_ARTIFACT: <sha256> <canonical-path>
VERDICT: ACCEPTED or REJECTED
FINDINGS: same-line summary or none
TESTS: what was actually checked or unavailable
COUNTEREVIDENCE: strongest reason the finding may be false or none
```

Detail may follow. A malformed response is not a verdict — reissue the unchanged
target once to a fresh reviewer.

Require the reviewer to report, as counterevidence against itself, any concern
whose failure sequence it could not construct. A theoretical worry with no path
to it is evidence the code is fine, and saying so is part of the job.

## What a finding is worth

Nothing, until you reproduce it. Open the cited code, trace the controlling path,
try the strongest counterexample, and check it against what the user actually
asked for. Then classify it: confirmed, false positive, needs a user decision, or
blocked for want of evidence.

Never report an unverified causal story. That matters most for generated
artifacts, where a structurally valid file can still be wrong for the business.

When correctness depends on a parser, scheduler, library, or data source, run a
narrow probe and a negative control. Documentation is not runtime proof, and
neither is a confident peer.

When the reviewed change is reachable through a running UI, the verdict waits on
the browser. Drive it with the harness's UI tool from the table above, in a
throwaway profile with disposable data: the changed journey end to end, plus one
path that should fail. Record routes, actions, what was visible, and the console
and network evidence.

State the outcome as passed, failed, or unavailable with its reason. Unavailable
means the UI claim is unverified — say so in the verdict rather than letting a
green unit suite stand in for it.

## Authority

Read-only is the default, and a request to review never grants an edit. Repair
authority exists only when the user asked for the fix as well as the review;
"what do you think" is not that request.

Peers are reviewers. This skill dispatches none of them with write access; under
repair authority the orchestrator makes the change itself. A workflow that owns a
branch may relax that — this one owns no branch, no commit, and no handle.

## External peers

A third-party peer carries none of this session's assumptions, which is why it
catches premises the family reviewers share. Read `~/NVIDIA_API_KEY.env`: it
declares which peers exist, in what order, and how to reach them. Never name
those models here.

No file: say so once at the start, point at `setup/NVIDIA-KEYS.md`, and say
plainly that it is optional. Then continue, with the external perspective marked
unavailable. Never discover this at the review gate, after the user has waited.

File present: name the peers and say what artifact is about to leave the machine
before the first send. A key on disk is a capability, never a standing consent.
Apply `delegating-to-external-models` to every send — it is a data boundary, not
a formality — and disclose what was redacted. Retry transport once, then fall
back to the local reviewer rather than stalling the run.

## Invoking Codex

```bash
codex exec \
  --ignore-user-config \
  -m <slug> \
  -c 'model_reasoning_effort="medium"' \
  --ephemeral \
  -s read-only \
  --skip-git-repo-check \
  -C <repo> \
  < <packet.md> > <out.txt> 2>&1
```

- **Never pipe the output.** `| tail`, `| head`, and `| grep` hold everything
  until the process exits, so a live run and a dead one look identical.
- Prompt over stdin, never `"$(cat packet.md)"` in argv.
- Pin `-m` and `model_reasoning_effort`, or the call silently inherits
  `~/.codex/config.toml` — the slowest and costliest setting available.

Two signals tell working from stuck: the output file still growing (`wc -c`), and
`pgrep -f 'codex exec'`. Three signals lie. `~/.codex/sessions/` stopped being
written in July 2026, so a healthy run leaves nothing there. `%CPU` is a lifetime
average and reads near zero while streaming. `ps | grep -i codex` matches the
ChatGPT desktop app. A high-reasoning review runs for tens of minutes in silence;
do not kill it while its output file grows.
