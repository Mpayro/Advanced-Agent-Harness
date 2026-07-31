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
