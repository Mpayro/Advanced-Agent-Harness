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
branch, the plan approval, and the stop before commit — including its standing
authorization to fan out as wide as a stage divides, which this skill's beats 1
and 2 lean on harder than any other.

## Which machinery holds the run

Pick one state authority per run and say which. Two are never live at once.

**In Codex**, `scripts/review_state.py` is that authority. There is no
orchestrator that survives a lost context, so the ledger is the only thing that
can prove what was covered, what was classified, and what is still open. Use it
for every run, including small ones.

**Elsewhere**, use a workflow orchestrator for the dispatches where the harness has
one — it enforces a verdict schema at the tool layer and replays a run, so a
malformed verdict is retried by the runtime instead of costing a dispatch. It does
not replace the ledger and is not a state authority. The state stays in
`review_state.py`, because the guarantees the beats below lean on live there and
nothing else implements them: one frozen target per gate, digests bound to stage and
finding, evidence and reviewer identity that cannot be reused, a waiver that is not
a waiver until it is recorded. So the ledger holds the run by default, and the
exception is a run holding a single candidate. Say out loud which shape you are in,
because the runs that skip the ledger are the ones that end with the same plan
written twice on two branches and a worktree of unmerged work nobody can account
for.

Whichever holds the run, one coordinator writes it. Subagents return evidence
and never mutate state.

## Commit as you go, everywhere

A turn can die without warning — an external filter, a lost connection, a
compaction that eats the thread. When it does, everything not already on disk is
gone, and a killed turn cannot write its own handoff. So do not bound the length of
a turn, which you cannot control. Bound **the work that is not yet persisted**,
which you can.

Nothing is left only in the tree. Each unit — a lane, a slice, a finding, a block —
is persisted once it lands, and no wave dispatches while the previous wave's output
is still unpersisted. That binds when work is written down, never when the next
unit may start: lanes still run in parallel, which beats 1 and 2 depend on harder
than anything else here.

In repair mode persisted means committed, on the isolated branch that mode already
owns. Not summarised, committed; "it is not clean yet" is not a reason to hold work
back, it is the reason the branch is isolated. In audit mode there is no branch and
nothing to commit — there the ledger is the persistence, and a finding that lives
only in the coordinator's context is the same defect wearing a different coat.
Where a repair runs in place because the repo requires it, there is no isolated
branch either: persist to the ledger and to written patch files. Never commit to
the user's branch to satisfy this — the base skill forbids it outright and owns the
branch in repair mode, so asking does not unlock it either. What waits until the end is the write-up,
never the work.

This is the cheapest discipline in the file and the one with the most evidence
behind it. A run that committed roughly every twenty minutes lost nothing when a
turn of almost nineteen hours was killed with no final message; a run in the same
repo the same week that kept its work in the tree instead produced duplicate
branches and a worktree of staged work still unmerged days later. The ledger proves
what was classified. The commit is what keeps the work.

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
before starting, `references/repo-overview.md` before building any inventory, and
`references/runtime-adapters.md` before spawning anything.

## Beat 1 — Find, peered

First prove you can observe the thing — entrypoints, fixtures and test commands,
logs and persisted state and downstream side effects, services that start without
touching production data, and gates that can actually fail. Run the preflight in
`references/detection-and-evaluation.md`; that list is the checklist and this
sentence is only its shape. Record what is not observable as blocked, with the
reason, before anything else.

Then enumerate the surface against the inventory in `references/repo-overview.md` —
open it whenever you are building an inventory, not only when the scope is named as
a whole repo. That file holds the categories; this sentence names only the six a
summary drops first and the attack map orders first, so that their absence is
visible from here: **auth and permissions, secrets, money, destructive operations,
audit history, and calculations of date, unit and rounding**. An inventory built
from this paragraph instead of from that file is missing most of itself. Give each
item a stable id and a risk, and freeze that inventory. Candidates found later
reference an existing id; they never quietly add one.

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
of intent, not proof of correctness — a candidate is never killed by a green test
the verifier has not seen go red. See vacuous green in
`references/detection-and-evaluation.md`.

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
concurrency, migrations, destructive behaviour, or a cross-module contract, and
never a high or critical finding or an exhaustive run whatever it touches. Those are
not the whole condition and the risk they turn on is not the bug's: the full waiver
in `references/evidence-contract.md` adds further conditions and reads the risk off
the frozen inventory item — go read them there, all of them. And a waiver is not
taken by deciding it applies: it is recorded, in the artifact that file specifies,
and then `review_state.py waive-plan` is called. Skipping the reviewer without that
record is not a waiver, it is a gap. The script does not enforce the excluded list
— you do. The post-fix review is never skipped.

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

Where the ledger holds the run it enforces these and wins any disagreement.

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

The base skill's "What is not done" and "Then say it simply" apply unchanged,
with its four categories read against an audit rather than a feature:

- **Surfaces nobody looked at** replaces "asked for and not built". Every
  inventory item blocked or skipped, what it would have taken to observe it, and
  what that does to the coverage claim.
- **Found and not fixed.** Confirmed bugs left open, candidates still waiting on
  a user decision, and anything documented-blocked. An audit that reads clean
  because the hard bugs were deferred is a lie told by omission.

The beat 4 adversary returns the `OMISSIONS` line like any other reviewer; that
is where the write-up gets checked, not in a separate pass.

## Handoff

Coverage by lane with its honest exclusions. Confirmed bugs, rejected candidates,
duplicates, and decisions needed. Per-bug review counts. The final verdict. The
exact tests and journeys exercised, and the probes and negative findings behind
them. What remains uncertain. Branch and dirty state. In repair mode, the stop
before commit.

Close with a short account of the run itself: what you followed, what you
substituted and why, which agents failed, and what went wrong.
