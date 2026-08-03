---
name: end-to-end-coding-session
description: Take a coding objective through four beats — a peered plan, an adversarial review of that plan, a peered implementation, and an adversarial review of the result — then hand off before commit unless the plan carried release steps the user authorized. Use when the user wants a multi-stage or cross-module change handled end to end with a plan they approve first. Do not use for a single bounded review, for the autonomous auto-commit variant, or for an exhaustive bug hunt.
---

# End-to-End Coding Session

Four beats, in order:

1. **Plan, peered** — cheap agents gather the real context; you write the plan.
2. **Adversarial review of the plan** — a fresh peer tries to break it.
3. **Implementation, peered** — build it on an isolated branch, with proof.
4. **Adversarial review of the result** — a fresh peer tries to break that.

Everything below serves those four. `coding-peers` decides who every peer is,
how to reach it, and what a verdict must look like; this skill never names a
model.

## Process skills, and the one rule that outlived them

Invoke a process skill where it genuinely applies and say which. Do not work
through a checklist of them — a mandated list gets skipped and teaches that the
rest of this skill is optional too.

One rule does not survive as a habit and has to be written down: **show the
failure before you change the behaviour.** A test that has never failed proves
nothing about the fix. Where a failing check is impractical, say so and name what
you used instead. Then run the mapped checks before claiming any of it works.

That rule has a second half that gets skipped: a green suite you inherited is not
evidence you broke nothing. It covers the seam you touched only if it would go red
when that seam breaks, and you have not seen it do that. Before citing an existing
green as regression proof, break the seam in a throwaway copy and confirm the test
fails. If it stays green, you have found a second defect — report it.

Apply `ponytail` throughout: the smallest change that actually works, at the root
cause, after you understand the whole flow. Never be lazy about understanding the
problem, input validation, error handling, security, accessibility, or anything
the user explicitly asked for.

## Peers in parallel

This skill is standing authorization to fan out. Any beat may run a swarm — as
wide as the stage genuinely divides — exploring an unfamiliar surface, probing
separate seams, implementing disjoint slices, reviewing along orthogonal risks.
Where the harness has a workflow orchestrator, use it: this skill's instructions
are the opt-in it requires. Where it does not, dispatch subagents directly.

Spawn the general tier from `coding-peers`, not the bulk-sweep one — Terra and
Sol in Codex, Sonnet subagents in Claude — and always name the model explicitly.
Gates run at the adversarial tier. Lanes must be genuinely independent: never
send several agents the same broad question and call the agreement evidence.
Collect the wave once rather than waking the coordinator per result.

Fan out because the work divides, not to look thorough. One agent on one clear
question beats six on a vague one.

## Before the first beat

Restate the objective in plain language and put it in front of the user: the
outcome, what is explicitly out of scope, the assumptions you are making, what
will count as acceptance evidence, and any ambiguity that would change behaviour
or authority. Ask about the ambiguity now — one short question beats a wrong
plan.

One thing must be settled in that same first exchange. **Which release steps, if
any, the objective reaches** — named one by one and authorized here. Nothing
later in the run can grant that authority.

Nothing else gets front-loaded. State the adversarial peer you will use rather
than asking for it, and check external-peer availability only if a send actually
comes.

Then write the living plan at `docs/superpowers/plans/YYYY-MM-DD-<goal>.md`, or
wherever the repo keeps plans. **Do not trust memory: write the plan, decisions,
evidence and open questions to markdown as the run proceeds, and treat those
files rather than recollection as the record.** Keep them with the run's
artifacts; trim the scratch, never the record.

Read the repo before planning: instructions, the real code path and its callers,
tests, `git status`, and the lineage of anything generated. For a broad or
unfamiliar surface, send read-only explorers down separate lanes — repo
conventions, code path, tests and tooling, and whatever else the surface
genuinely divides into.

## Beat 1 — Plan, peered

The plan states the goal and non-goals, the smallest change that reaches it, the
seams it touches, the state transitions and invariants that must hold, ordered
tasks with the command that verifies each, and what would falsify the approach.

For stateful work, name the identities, the legal transitions, every authoritative
reader and writer, and what happens on restart, retry, and rollback. For anything
generated, name the producer, the source and its freshness, and the consumer.

If the plan carries release steps, each one gets its own acceptance evidence and
its own rollback, written here.

## Beat 2 — Adversarial review of the plan

Freeze the plan and hand the real artifact to a fresh peer with no prior
conclusions. Ask it to find hidden scope, missing tests, business or data risk,
and a simpler seam that already exists. When external peers are available, send
them the same frozen plan — a reader with none of your assumptions is cheapest
here, before any code exists.

Verify every claim yourself before acting on it. Revise for confirmed issues,
record what you accepted and rejected in the living plan, and stop for the user
when the same authority question comes back twice.

Then put the plan in front of the user for approval. Where the harness has a
plan-approval mechanism of its own, use it rather than hand-rolling one. Where it
does not, show at most five plain bullets — outcome, the rule you are protecting,
the proof, the scope boundary, the plan path.

Either way, name each release step separately and ask for release authorization
separately. Approving a plan is edit authority and nothing more.

## Beat 3 — Implementation, peered

Work on an isolated `agent/<goal>` branch or linked worktree unless the user or
repo requires in-place work. Use the harness's own worktree tooling where it has
some. A dirty shared checkout is not isolation; preserve unrelated dirt and never
stage it.

Make the smallest change at the root cause. Grep every caller before patching one
path. Delegate slices to peers only when file ownership is disjoint, and give each
one explicit boundaries.

Prove it as you go: the narrow check for the change, then the sibling and
lifecycle checks, then whatever the repo's conventions require. Non-trivial logic
leaves one runnable check behind.

Commit as you go too, and for the same reason you branch: a turn can be killed
without warning and cannot write its own handoff, so no slice is left only in the
tree once it lands, and no wave dispatches while the previous wave's output is still
uncommitted. Disjoint slices still run in parallel — this binds when work is
written down, not when the next may start. The branch is isolated precisely so that
"it is not clean yet" costs nothing. Where the repo requires in-place work there is
no isolated branch to commit to — persist to a written patch file instead, at the
same cadence, and say so at the handoff. Never commit to the user's branch to
satisfy this. The write-up waits until the end; the work never does.

Update the living plan as you go — decisions, surprises, and anything that turned
out different from the plan.

## Beat 4 — Adversarial review of the result

Freeze the exact patch bytes and hand a fresh peer the real diff, the
verification output, and the approved plan. Ask for correctness, missed
requirements, security and data risk, over-engineering, and missing proof. Send
the same frozen target to the external peers when available — this is the second
and last external consultation.

Ask this reviewer for one more thing, in the `OMISSIONS` line of its verdict:
what the work and the write-up leave out, soften, or overclaim — one field on the
review already running, not a second pass. Anything it raises that you verify
goes into the handoff.

Every finding is a hypothesis. Reproduce it, fix only confirmed defects that are
in scope, re-run the mapped checks, and re-review. Keep going while each round
confirms a new in-scope defect; stop when a round finds none. Adjacent problems
get documented, not silently absorbed.

Offer the heavy `peer-bug-review` before handing off and respect the answer. If
it changes code, repeat beats 3 and 4 without re-offering.

## Last check — the product, in a browser

**The cycle does not end until you have driven what you built and clicked
through it.** A product with a UI is not verified until someone drove it — not a
screenshot, not a green unit suite, the real thing in a browser exercising what
this change created. This runs last, after the review and before anything is
handed off, committed, or released.

- Launch Chrome with a throwaway profile and remote debugging. Never the user's
  own profile, never their logged-in session.
- Walk the changed journey end to end, the way a person would — not one widget in
  isolation. Then walk one path that should fail: empty, invalid, unauthorized,
  refreshed mid-flow, or navigated back into.
- Record the routes, the actions, what was actually visible, the console and
  network evidence, and the state left behind. A screenshot alone proves the page
  rendered, not that the feature works.
- Use local or preview state and disposable data. Never a destructive or
  production mutation without explicit authority.

Three outcomes, and one of them must be stated out loud:

- **Passed** — the journey and its negative path behaved as the plan said.
- **Failed** — say what broke; it goes back to the previous beat.
- **Unavailable** — say why (no browser, no environment, no fixture). The change
  is then unverified on that surface, and it is reported that way.

A change with no reachable UI records "no UI surface" and moves on. That is a
stated outcome, not a silent skip.

## Authority

Three authorities, granted separately, never inferred from each other:

- **Edit** comes from the user approving the plan.
- **Commit** comes from asking at the handoff.
- **Release** comes only from the naming in the first exchange.

Checkpointing your own work on your own isolated branch is not the commit this
governs, and never needs asking — it lands nothing, it only stops a killed turn
from taking the work with it. What needs asking is the commit that delivers:
anything onto a branch the user shares, and the commit steps the handoff proposes.

Approval of the code is not approval of the release. A plan that never mentioned
production does not acquire it later, and no peer can grant it.

## Release and production

Touching production is scope, not a forbidden category. Deploying, promoting,
merging, pushing, and migrating are ordinary steps when they are what the work is
for. A release step runs when all four hold: the approved plan names it with its
own acceptance evidence and rollback; the user authorized that exact action; the
gates guarding it accepted; and it is reversible, or its irreversibility was
disclosed before it was authorized.

Run them in the plan's order, verify each before starting the next, and stop at
the first failure with the rollback state stated.

## Handoff

Report what changed and what it means for the user, the exact verification you
ran, what you could not prove, the branch and dirty state, the saved patch, the
dirt you deliberately excluded, and the proposed commit and push steps. Ask
before commit.

Report each release step as executed, failed with its rollback state, not
reached, or — only when the user never authorized it — proposed. A run that
reached production says so plainly and never calls a finished release proposed.

Do not commit, push, merge, deploy, promote, or migrate unless the user
explicitly asks. Checkpoints on the isolated branch are the one exception, stated
in Authority above: they deliver nothing, and they are why there is still work to
hand off after a turn dies.

## What is not done

The user reads a finished report as a finished feature. Correcting that is your
job, not theirs, and it is the part of the handoff that gets skipped.

Say plainly, in their words and without softening:

- **Asked for and not built.** Anything they raised that this change does not do,
  and whether it was deferred, ruled out of scope, or blocked. Name it even if
  they seemed to drop it — people remember what they asked for.
- **Looks done and is not.** Stubs, TODOs, hardcoded values, a happy path with no
  error handling, a case that silently does nothing. Anything that would pass a
  demo and fail on a Tuesday.
- **Built but not proven.** What you could not verify, what environment or data
  would have been needed, and what that leaves unknown.
- **What this could break.** The surfaces that share a seam with the change and
  were not exercised.

Lead with the largest gap. If a category is genuinely empty, say so — "no
unhandled cases" is information; silence is not. Never end a handoff whose only
shape is what went well.

## Then say it simply

What lands in chat is short and plain. A few lines, ordinary words, no tables, no
dumps of evidence:

- What now works that did not.
- What it means for the person reading, not what you did to get there.
- What is missing or unproven — the honest part, kept honest.

No step-by-step, no method, no file inventory, no counts of reviews and rounds.
The plan, the diff, the evidence and the full gap list already exist as
artifacts; offer them in one line. If the user wants to go deeper, that is their
next message, not your current one.

## Limits

Iterate while each round produces something new. These are the stop conditions,
not attempt counts — a run that is still converging keeps going.

| Stage | Stop when |
|---|---|
| Plan review | The same authority blocker repeats |
| Failing check | Two consecutive attempts produce no new evidence about the cause |
| Result review | A round confirms no new in-scope defect |
| External peer | One retry fails — fall back to the local reviewer |
| Authorized release | First failure — no retry, rollback state stated |

Repeat only the stage that failed. Never restart the whole run because one stage
did. When a stop condition triggers, say what is blocked and hand the decision
back to the user.

The release row is the one hard bound: an irreversible action gets one pass. The
rest are judgment, and judgment favours finishing the feature.
