---
name: end-to-end-coding-session-automatic
description: The same four beats as end-to-end-coding-session, with a fresh adversarial reviewer approving the plan and the final diff in place of the user, and an automatic commit on an isolated branch. Use only when the user explicitly asks for the autonomous variant and authorizes that commit. Release steps run only when the opening consent named them. Never infer this mode from a request to implement something, to move fast, or to work end to end.
---

# End-to-End Coding Session — Automatic

Same four beats as `end-to-end-coding-session`: a peered plan, an adversarial
review of it, a peered implementation, an adversarial review of the result. Read
that skill; this one only says what changes.

What changes is who approves. A fresh reviewer approves the plan and the final
diff instead of the user, and the accepted diff is committed automatically to an
isolated branch. Everything else — the peer table, the release conditions, the
verification discipline, the limits — is inherited unchanged.

The base skill's Superpowers table applies here unchanged — brainstorming before
the shape is settled, tests before implementation, systematic debugging before
any fix, verification before any claim — and so does `ponytail`. Nobody is
watching this run, which is the reason to follow them, not to skip them.

Human-gated remains the default for long work. This variant is allowed only when
both the authority and the task are explicit.

## Consent, once, up front

Say exactly what will happen and get it confirmed before anything else:

- The plan will be approved by a reviewer, not by you.
- The approved diff will be committed automatically to an isolated branch.
- The reviewer approves within the authorized objective; it cannot invent intent,
  widen scope, or authorize a production effect.
- Release steps — push, merge, deploy, promote, migrate — run automatically only
  if named right here. Anything unnamed stops as a proposal.
- One yes-or-no question about the heavy bug review still comes to the user.

Settle the adversarial peer and external-peer availability in this same exchange,
for the same reason the base skill does: an autonomous run that stops at its own
review gate to ask who reviews is not autonomous.

A generic "implement it" is not this consent.

## When to refuse the mode

Hand the work back to the human-gated skill, before starting, when any of these
is true: the business intent is unresolved; a constraint needs the user's
judgment; the source lineage or freshness is unknown; the checkout cannot be
isolated; required live proof is unavailable; the commit scope or target branch
is ambiguous; or a reviewer would have to invent intent to approve.

Also refuse when a production, destructive, or irreversible action is in scope
and the consent above did not name it. Whether the plan carries that action's
rollback is not knowable yet — the plan does not exist — so the plan gate below
tests it instead.

## Beat 2 — the reviewer approves the plan

Do not ask the user. Freeze the plan and give it, with the authorized objective,
to a fresh reviewer with no context. It defaults to rejecting when evidence is
missing.

```text
TARGET_ARTIFACT: <sha256> <canonical-path>
VERDICT: APPROVE or REJECT
PLAN: same-line assessment
COUNTEREVIDENCE: same-line concern or none
```

Reject the plan outright, in either direction, since this is the first moment the
plan exists:

- The consent named a release action and the plan does not carry that action's
  rollback and verification.
- The plan contains a production, destructive, or irreversible step the consent
  never named. Return it to the user for naming; an autonomous run may not take
  that authority from its own plan. This is not a technical rejection and does
  not consume an attempt.

On rejection, verify each blocker, revise only for the confirmed ones, freeze the
new plan, and use a fresh reviewer. Record the plan digest as approved; the diff
reviewer will be asked to echo it back.

## Beat 4 — the reviewer approves the diff, then it commits

Freeze the approved plan digest, the exact patch, and the verification evidence,
and dispatch a fresh reviewer. It returns the same five labels plus the approved
plan digest. Compare that digest to the one you recorded: any mismatch goes back
to the user, because it means the diff under review is not the plan that was
approved.

Commit only after that acceptance and after the heavy-review question is
resolved, from a clean isolated worktree, using the accepted patch as the sole
staging input. Verify the staged diff digest equals the accepted one and abort on
any other staged bytes.

If the heavy bug review changes code, re-verify and re-review once before
committing, and compare digests again.

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

The base skill's last check is not optional here, and it is not the reviewer's
job. Run it before the commit. A required browser check that came back failed or
unavailable blocks the auto-commit: an autonomous run may not commit a UI change
that nobody drove.

## Beat 5 — the authorized release

Announce this step as `release` when the consent named one; a run with no release
has no fifth beat.

Perform a release step — every verb the consent enumerates, migrations included —
only when that consent named that exact action and the base skill's four release
conditions all hold. Commit authority is not release authority; never infer one
from the other.

Run only after the commit exists and the heavy-review question is resolved.
Execute the plan's steps in its order, verify each before the next, and stop at
the first failure with the rollback state stated. One pass, no retry.

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

## Closing

The run is finished when the plan was accepted, the diff was accepted, the
heavy-review question was answered, the commit exists on the isolated branch, and
every authorized release step finished. Not before.

Report what changed, the verification you ran, the reviewer round counts, the
commit and its branch, the dirty state, what remains uncertain, and each release
step as executed, failed with its rollback state, not reached, or — only for
something the consent never named — proposed.

Never push or merge as a side effect of committing. Anything the consent did not
name comes back as a proposal, never as a completed step.
