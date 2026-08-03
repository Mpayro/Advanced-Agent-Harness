---
name: end-to-end-coding-session-automatic
description: The same four beats as end-to-end-coding-session, with a fresh adversarial reviewer approving the plan and the final diff in place of the user, and an automatic commit on an isolated branch. Use only when the user explicitly asks for the autonomous variant and authorizes that commit. Release steps run only when the opening consent named them. Never infer this mode from a request to implement something, to move fast, or to work end to end.
---

# End-to-End Coding Session — Automatic

Same four beats as `end-to-end-coding-session`: a peered plan, an adversarial
review of it, a peered implementation, an adversarial review of the result. Read
that skill; this one only says what changes.

What changes is who approves. A fresh reviewer approves the plan and the final
diff instead of the user, and the commit the reviewer accepted — already on an
isolated branch, because the work is checkpointed as it goes — is declared the
delivered state without asking again. Everything else — the peer table, the release
conditions, the verification discipline, the limits — is inherited unchanged.

Exactly one base rule is superseded, and naming it is the point: the base tells you
to ask before committing, at the handoff. Here that asking already happened, in the
opening consent, so the commit does not wait for a second question. Nothing else
moves with it — push, merge, deploy, promote, and migrate still wait for what the
consent named, and the base's rule governs every one of them unchanged.

The base's checkpoint commits are inherited too, and they reach this branch as
they reach any other — reaching the branch is not landing, and nothing below calls
it that. That is what beat 4's gate below is built around: the gate cannot be a
check on the staging area, because whether anything is staged depends on where the
run happens to be. Checkpoint as the base says and the tree is clean at the freeze,
so the frozen patch is already committed and the gate has nothing to stage; arrive
at the freeze with work still in the tree — after a rejected round, most often —
and it is not. Both are ordinary. The gate below works the same either way, which
is why it commits first and reads a sha rather than a staging area.

The base skill's process rules apply here unchanged — above all, show the failure
before changing the behaviour, and run the mapped checks before claiming any of
it works — and so does `ponytail`. Nobody is watching this run, which is the
reason to follow them, not to skip them.

Human-gated remains the default for long work. This variant is allowed only when
both the authority and the task are explicit.

## Consent, once, up front

Say exactly what will happen and get it confirmed before anything else:

- The plan will be approved by a reviewer, not by you.
- Work is checkpointed to an isolated branch as it goes, and the reviewer-accepted
  commit on that branch is declared the delivered state without asking you again.
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
new plan, and use a fresh reviewer. Record the approved plan's digest yourself.

## Beat 4 — the reviewer approves the diff, then it lands

Freeze the approved plan, the exact patch, and the verification evidence, and
dispatch a fresh reviewer. Before dispatching, check the plan you are sending
against the digest you recorded: any mismatch goes back to the user, because it
means the diff under review is not the plan that was approved. You hold both
artifacts — verify that yourself rather than asking the reviewer to attest to it.

**Commit the frozen bytes first, then record that commit's sha.** In that order,
always: a sha taken by clock is a pointer to whatever happened to be committed, and
the patch you froze was built from the working tree. Freeze after a rejected round
and the two are different things — the sha holds the version that was rejected and
the fix that earned the acceptance is not in any commit at all.

Then land only after that acceptance and after the heavy-review question is
resolved. **What lands is that recorded sha — not the branch, not its tip.**
Anything committed afterwards, living-plan updates included, is simply not part of
what landed; it stays on the branch for the next round.

Landing means declaring that sha the delivered state of the branch, and declaring it
in git rather than in prose: `git tag landed/<goal> <sha>`, local, never pushed. The
handoff then names it. That order matters for the same reason the checkpoints exist
— a turn can be killed without writing its handoff, and a landing that lives only in
the handoff is a landing that dies with it, leaving every byte intact and no way to
recover which commit was the accepted one. The tag survives; prose does not.

Withholding a landing is therefore not silence and not a lost tag: the branch keeps
its bytes, nothing is reset or discarded, no tag is written, and the handoff says
the run delivered nothing and which gate withheld it.

That is the whole gate, and it is shaped this way on purpose. Every earlier version
tried to *detect* drift — diff the tip, compare digests, abort on surprise — and
each one either aborted on the run's own bookkeeping or inspected a point that
predated the drift and passed while asserting nothing. Landing a fixed sha makes
drift structurally irrelevant instead of detectable. Nothing lands that the reviewer
did not accept, because the accepted thing is the only thing named.

Re-review re-records, in the same order. If the heavy bug review changes code, or
the browser check sends work back, the new bytes are committed, frozen, accepted,
and that commit's sha recorded in turn — the old sha never lands after that.

Re-verify before that re-review, and never land a sha that no reviewer accepted.

## Last check — the product, in a browser

The base skill's last check is not optional here, and it is not the reviewer's
job. Run it unchanged, before the landing.

One rule is this mode's alone: a required browser check that came back failed or
unavailable **blocks the landing and every release step after it**, because an
autonomous run may not ship a UI change that nobody drove. Say "blocks the commit"
and it blocks nothing — the bytes reached the branch at checkpoint time, before any
of this ran. What is withheld is the landing, the push, and everything the consent
named; the branch stays where it is and the handoff says why.

## Beat 5 — the authorized release

Announce this step as `release` when the consent named one; a run with no release
has no fifth beat.

Perform a release step — every verb the consent enumerates, migrations included —
only when that consent named that exact action and the base skill's four release
conditions all hold. Commit authority is not release authority; never infer one
from the other.

Run only after the landing happened and the heavy-review question is resolved. A
checkpoint on the branch is not the landing; if the landing was withheld, so is
this.
Execute the plan's steps in its order, verify each before the next, and stop at
the first failure with the rollback state stated. One pass, no retry.

## The handoff

The base skill's "What is not done" and "Then say it simply" apply unchanged.
Nobody watched this run, so the gap list is the only thing standing between a
green report and a false impression of completeness.

## Closing

The run is finished when the plan was accepted, the diff was accepted, the
heavy-review question was answered, the accepted sha landed, and every authorized
release step finished. Not before. A branch carrying checkpoints is not a landing:
a run whose landing was withheld is unfinished, and says which gate withheld it.

Say where the branch stands relative to what landed, always, because they are
rarely the same commit and only one of them was reviewed. Committed-but-not-landed
is its own category and it is not dirt: name the landed sha and its tag, say how
many commits the tip is ahead of it and what they are, and never let "the branch"
stand in for "what was accepted". In a withheld run there is no landed sha — say
that, and which gate withheld it.

Report what changed, the verification you ran, the reviewer round counts, the
landed sha and its branch, the dirty state, what remains uncertain, and each release
step as executed, failed with its rollback state, not reached, or — only for
something the consent never named — proposed.

Never push or merge as a side effect of committing. Anything the consent did not
name comes back as a proposal, never as a completed step.
