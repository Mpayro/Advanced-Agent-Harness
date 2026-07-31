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

## Superpowers along the way

These are process skills, and they belong inside the beats rather than after
them. Invoke each where it applies, say so out loud, and follow it:

| Where | Skill |
|---|---|
| Before the plan exists, while the shape is still open | `superpowers:brainstorming` |
| Writing the plan itself | `superpowers:writing-plans` |
| Isolating the workspace | `superpowers:using-git-worktrees` |
| Implementing, test first | `superpowers:test-driven-development` |
| Working through the plan's tasks | `superpowers:executing-plans` |
| Splitting independent slices across peers | `superpowers:subagent-driven-development` |
| Anything unexpected, before proposing a fix | `superpowers:systematic-debugging` |
| Before claiming any of it works | `superpowers:verification-before-completion` |
| Asking for and reading the adversarial review | `superpowers:requesting-code-review`, `superpowers:receiving-code-review` |
| Deciding how the branch lands | `superpowers:finishing-a-development-branch` |

Apply `ponytail` throughout: the smallest change that actually works, at the root
cause, after you understand the whole flow. Never be lazy about understanding the
problem, input validation, error handling, security, accessibility, or anything
the user explicitly asked for.

## Before the first beat

Restate the objective in plain language and put it in front of the user: the
outcome, what is explicitly out of scope, the assumptions you are making, what
will count as acceptance evidence, and any ambiguity that would change behaviour
or authority. Ask about the ambiguity now — one short question beats a wrong
plan.

Settle three things in that same first exchange, because each one interrupts the
run if you leave it for later:

- Which adversarial peer, when `coding-peers` offers a choice in this harness.
- Whether external peers are available, per its External Peers section.
- Which release steps, if any, the objective reaches — named one by one and
  authorized here. Nothing later in the run can grant that authority.

Then write the living plan at `docs/superpowers/plans/YYYY-MM-DD-<goal>.md`, or
wherever the repo keeps plans. It is the only record of continuity: everything
that must survive an interruption goes in it, and it is updated as the run
proceeds, not at the end.

Read the repo before planning: instructions, the real code path and its callers,
tests, `git status`, and the lineage of anything generated. For a broad or
unfamiliar surface, send up to three read-only cheap-tier explorers down separate
lanes — repo conventions, code path, tests and tooling. Never fake parallelism by
asking several agents the same question.

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

Then show the user at most five plain bullets — outcome, the rule you are
protecting, the proof, the scope boundary, the plan path — plus one naming each
release step if there are any. Ask for implementation approval, and ask for
release authorization separately.

## Beat 3 — Implementation, peered

Work on an isolated `agent/<goal>` branch or linked worktree unless the user or
repo requires in-place work. A dirty shared checkout is not isolation; preserve
unrelated dirt and never stage it.

Make the smallest change at the root cause. Grep every caller before patching one
path. Delegate slices to peers only when file ownership is disjoint, and give each
one explicit boundaries.

Prove it as you go: the narrow check for the change, then the sibling and
lifecycle checks, then whatever the repo's conventions require. Non-trivial logic
leaves one runnable check behind.

Update the living plan as you go — decisions, surprises, and anything that turned
out different from the plan.

## Beat 4 — Adversarial review of the result

Freeze the exact patch bytes with their SHA-256 and hand a fresh peer the real
diff, the verification output, and the approved plan. Ask for correctness, missed
requirements, security and data risk, over-engineering, and missing proof. Send
the same frozen target to the external peers when available — this is the second
and last external consultation.

Every finding is a hypothesis. Reproduce it, fix only confirmed defects that are
in scope, re-run the mapped checks, and re-review once. Adjacent problems get
documented, not silently absorbed.

Offer the heavy `peer-bug-review` exactly once before handing off, and respect
the answer. If it changes code, repeat beats 3 and 4 without re-offering.

## Last check — the product, in a browser

This runs last, after the review and before anything is handed off, committed, or
released. A product with a UI is not verified until someone drove it.

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
stated outcome, not a silent skip. A green unit suite never substitutes for this.

## Authority

Three authorities, granted separately, never inferred from each other:

- **Edit** comes from the user approving the plan.
- **Commit** comes from asking at the handoff.
- **Release** comes only from the naming in the first exchange.

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
explicitly asks.

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

## The summary gets reviewed too

Draft the handoff, then hand the draft plus the real change and its evidence to
one fresh peer before the user sees it. You wrote the work, so you are the worst
judge of what the write-up quietly leaves out.

Ask it for exactly that: what the summary omits, softens, or overclaims — above
all in what is not done. Anything it adds that you verify goes into the summary.
This is one cheap pass, not another review round; the code was already reviewed.

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

| Stage | Limit | Stop when |
|---|---:|---|
| Plan review | 2 revisions | The same authority blocker repeats |
| Failing check | 3 attempts | The root cause is still unclear |
| Result review | 2 rounds | No new confirmed in-scope defect |
| External peer | 1 retry | Repeated empty or failed response |
| Heavy bug review | 1 offer, 1 run | Declined, finished, or blocked |
| Authorized release | 1 pass, no retry | First failure, rollback state stated |

Repeat only the stage that failed. Never restart the whole run because one stage
did. When a stage exhausts its limit, say what is blocked and hand the decision
back to the user.
