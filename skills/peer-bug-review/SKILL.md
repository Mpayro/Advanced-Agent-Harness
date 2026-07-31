---
name: peer-bug-review
description: The same four beats as end-to-end-coding-session, aimed at bugs instead of features — find candidates with cheap peers, prove or kill each one with a blind adversarial reviewer, fix only what survived, and adversarially review the assembled product. Use for a repo overview, an exhaustive module or business-flow audit, a UI click sweep, a disputed finding, or an end-to-end repair loop that must separate real bugs from intended behaviour.
---

# Peer Bug Review

The same four beats as `end-to-end-coding-session`, pointed at bugs:

1. **Find, peered** — cheap agents sweep the surface by different methods.
2. **Prove or kill, adversarially** — a blind reviewer grades each candidate.
3. **Fix, peered** — only what survived, smallest root cause, failure first.
4. **Review the assembled product** — one fresh adversary over the whole set.

`coding-peers` decides who every peer is and what a verdict must look like. Apply
`ponytail` throughout. In repair mode, `end-to-end-coding-session` owns the
branch, the plan approval, and the stop before commit.

## What you may promise

Evidence discipline, never the absence of bugs. Say "every enumerated surface was
covered and every candidate was classified." Never say the repo has no bugs.

Exhaustion is not acceptance. A surface you could not observe is blocked, not
clean, and turning "I could not look" into "nothing there" is the one failure
this skill exists to prevent.

## Two modes, and the line between them

**Audit** is the default for review, audit, find bugs, repo overview. It is
read-only apart from the review artifacts the user asked for.

**Repair** requires the user to have asked for the fix as well. A review request
is not edit authorization.

Read `references/evidence-contract.md` and `references/detection-and-evaluation.md`
before starting, `references/repo-overview.md` when the scope is a whole repo or
module, and `references/runtime-adapters.md` before spawning anything.

## Beat 1 — Find, peered

First prove you can observe the thing: real entrypoints, safe fixtures, logs and
state, required services. Record what is not observable as blocked, with the
reason, before anything else.

Then enumerate the surface — modules and entrypoints, public functions and risky
private seams, jobs and migrations and external I/O, business state machines,
UI routes and their empty, error, and permission states, and the test and
deployment surfaces. Give each item a stable id and a risk, and freeze that
inventory. Candidates found later reference an existing id; they never quietly
add one.

Send explorers down disjoint lanes with orthogonal methods, not several agents
repeating the same static read. Each returns what it covered, the commands it
ran, its candidates, and its gaps. Explorers report candidates, never bugs, and
never edit.

Never start from random file sampling. An inventory you did not build is a
coverage claim you cannot make.

## Beat 2 — Prove or kill, adversarially

Deduplicate by root cause first. Then give the verifier the raw code and runtime
artifacts, the authority sources, and the reproduction surface — never the
finder's conclusion or intended fix. A verifier that knows the answer is not a
second opinion.

Each candidate ends as exactly one of: confirmed, not a bug, needs a user
decision, or duplicate. Only confirmed advances. Tests and old docs are evidence
of intent, not proof of correctness.

Freeze each target before dispatch, keep one evidence artifact and one reviewer
identity per target, and let `scripts/review_state.py` hold the counters and gate
state rather than prose. Never normalize a verdict by hand.

## Beat 3 — Fix, peered

One spec per confirmed bug from `assets/bug-spec-template.md`: root cause, every
affected caller, the invariant it breaks, the failing test, the smallest seam
that fixes it, and what is deliberately out of scope.

Then, per bug: reproduce the failure on the baseline, change the smallest shared
seam, run the narrow check, run the sibling and lifecycle checks, and send the
real diff and raw output to a fresh reviewer. Verify every reviewer claim
yourself before touching code.

Work in waves. Parallelize only across disjoint file ownership; serialize
anything sharing files, state, schema, or an invariant.

A low or medium-risk bug with a deterministic failing test may skip the separate
plan reviewer, but never one touching security, money, authorization,
concurrency, migrations, destructive behaviour, or a cross-module contract. The
script does not enforce that list — you do. The post-fix review is never skipped.

## Beat 4 — Review the assembled product

Per-bug green is not product green. Run the targeted tests, the integration
checks across shared seams, a comparison against the baseline failures you
recorded at the start, and a real smoke of the affected journeys. For UI changes,
click the matrix in a throwaway browser profile.

Then one fresh adversary over the whole set: the original request, the coverage
map, the specs, the final diff, the exact evidence, and everything still
unclassified. Its job is the interaction between the fixes, not another pass over
each patch.

## When it is finished

Every inventory item covered, skipped with a reason, or blocked with the reason
it could not be observed. Every candidate terminally classified. Every confirmed
bug documented. In repair mode, every fix accepted by a reviewer, the assembled
product passing its mapped checks, and the final adversary accepting the set.

A blocked surface does not stop the run from closing — it stops the run from
claiming coverage. Report it as blocked, name what would unblock it, and close.

## Limits

The script enforces these; the numbers below are the real ones.

| Stage | Fast (default) | Exhaustive |
|---|---:|---:|
| Candidate confirmation | 3 | 3 |
| Plan review, per bug | 3 | 10 |
| Fix review, per bug | 3 | 10 |
| Integration gate | 3 | 3 |
| Explorer transport retry | 1 | 1 |

At the ceiling, or when the same blocker repeats twice with no new evidence, mark
the bug documented-blocked and ask the user for the smallest decision that would
move it. A documented-blocked bug can close an audit; it cannot close a repair.

Repeat only the stage that failed. Never restart the whole workflow because one
stage did.

## What is not done

The user reads a finished report as a finished audit. Correcting that is your
job, not theirs, and it is the part of the handoff that gets skipped.

Say plainly, without softening:

- **Surfaces nobody looked at.** Every inventory item blocked or skipped, what it
  would have taken to observe it, and what that does to the coverage claim.
- **Found and not fixed.** Confirmed bugs left open, candidates still waiting on
  a user decision, and anything documented-blocked. An audit that reads clean
  because the hard bugs were deferred is a lie told by omission.
- **Fixed but not proven.** What you could not verify and what that leaves
  unknown.
- **What this could break.** Surfaces sharing a seam with the fixes that were not
  exercised.

Lead with the largest gap. If a category is genuinely empty, say so — silence is
not information. Never end a handoff whose only shape is what went well.

## Handoff

Coverage by lane with its honest exclusions. Confirmed bugs, rejected candidates,
duplicates, and decisions needed. Per-bug review counts. The final verdict. The
exact tests and journeys exercised, and the probes and negative findings behind
them. What remains uncertain. Branch and dirty state. In repair mode, the stop
before commit.

Close with a short account of the run itself: what you followed, what you
substituted and why, which agents failed, and what went wrong.
