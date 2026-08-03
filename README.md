# Advanced Agent Harness

**True autopilot for coding agents:** prompts that keep agents working for days
with automatic review, testing, adversarial bug audits, and evidence-gated
delivery.

A portable, Codex-first bundle for taking coding work from grounded scope to
verified implementation without letting the agent grade its own homework.

The current workflows:

| Need | Skill |
|---|---|
| Plan, approve, implement, verify, stop before commit | `end-to-end-coding-session` |
| Explicitly opt into an isolated-branch auto-commit | `end-to-end-coding-session-automatic` |
| Review one settled plan, diff, seam, or artifact | `coding-peers` |
| Audit a reported bug or a whole repo with evidence gates | `peer-bug-review` |
| Force the smallest correct implementation | `ponytail` |
| Review a diff only for removable complexity | `ponytail-review` |
| Redact data before a named third-party model call | `delegating-to-external-models` |

## What the main workflow does

Run:

```text
end-to-end coding session: add rate limiting to the public API
```

The human-gated workflow:

1. Reads the real repo path, callers, tests, instructions, branch, and dirty
   state before planning, fanning explorers out across independent lanes.
2. Restates the objective and asks for exactly one thing up front: which release
   steps, if any, the work reaches. Nothing later in the run can grant that
   authority. Everything else has a default and is stated, not asked.
3. Writes a living plan, has a fresh reviewer attack it, and asks you to approve
   implementation.
4. Implements the approved plan in an isolated worktree, showing the failure
   before changing the behaviour, and checkpointing each slice as it lands so a
   turn that dies without warning cannot take the work with it.
5. Verifies the acceptance claims, including an isolated-Chrome product smoke
   for UI work.
6. Freezes and reviews the exact task-owned patch, not a prose summary. That
   same reviewer reports what the write-up omits or overclaims.
7. Asks once whether to run the heavier Peer Bug Review, then stops before
   commit.

Any beat may fan out a swarm of roughly five to ten agents when the stage
genuinely divides that many ways, using the harness's workflow orchestrator
where it has one.

The workflow preserves unrelated changes and never delivers, pushes, or merges
without explicit authority. Checkpoints on its own isolated branch are the one
exception, and they are not a delivery: they hand nothing over, they only make
sure there is still something to hand over. Where a repo forbids branching, there
are no checkpoints either — the work is written to a patch file instead, and never
committed to a branch you share.

Every rule above is there because a run broke without it. The checkpoint rule
comes from a turn that ran nearly nineteen hours and was killed by a content
filter with no final message; what survived was committed, and nothing else was.

## Automatic variant

Run:

```text
end-to-end coding session automatic: migrate the auth middleware
```

Automatic is explicit opt-in, and its opening consent is where any release step
must be named. It then checks that the task is deterministic, reversible,
isolated, and fully provable, and hands the work back to the human-gated skill
when it is not. A fresh reviewer approves the plan and the diff in your place.
You still choose once whether to run Peer Bug Review.

Work is checkpointed to the isolated branch as it goes, so a killed turn cannot
take it with it. That makes the branch and the delivery two different things, and
the workflow keeps them apart: it commits the frozen bytes, records that commit's
sha, and lands exactly that sha once the reviewer accepts it. Anything committed
afterwards stays on the branch and is reported as such — never as delivered work.
A UI change whose browser check failed or was unavailable blocks the landing and
every release step after it. It never pushes or merges.

## Peer Bug Review

For a read-only audit:

```text
peer bug review: audit this repository
```

For an authorized repair run:

```text
peer bug review: prove and fix the reported checkout bug end to end
```

Audit is the default. The workflow inventories the real product surface,
discovers candidates in disjoint lanes, blindly verifies each candidate,
classifies it, and closes with a whole-product integration gate. Repair mode
advances only confirmed bugs through reviewed plans, failure-first fixes, and
fresh adversarial re-review.

Before judging any code it proves the gates can fail — that a baseline is
populated, that a test glob matches something, that a declared assertion is read
by anything. A gate that cannot fail turns every green behind it into noise, and
no amount of probing the product will find it.

It also hunts tests that pass without meaning anything, by name: a **dead anchor**
compares output against a frozen artifact, so green means nothing changed since the
freeze; an **uncompared twin** is the same fact resolved two ways with nothing
asserting they agree; **borrowed authority** is a test that names a source in its
title and never opens it. None of the three survives a red-first test, and none
shows up in a code review, because every side looks correct on its own.

A state ledger holds the run by default, not only on big ones. It is what lets a
run survive losing its context, and its absence is what turns a long run into the
same plan written twice on two branches.

Its promise is evidence coverage, not the impossible claim that a repository
has no bugs.

## Package contents

```text
skills/
  end-to-end-coding-session/
    SKILL.md
    agents/openai.yaml
    scripts/validate_workflow_suite.py
  end-to-end-coding-session-automatic/
  coding-peers/
  peer-bug-review/
    SKILL.md
    agents/openai.yaml
    assets/bug-spec-template.md
    references/
      review-output.schema.json
    scripts/review_state.py
    scripts/render_review_batch.py
    scripts/eval_peer_bug_review.py
  delegating-to-external-models/
  ponytail/
  ponytail-review/

hooks/       optional Claude-side Fable guard and Ponytail session posture
memory/      optional Claude-side memory notes
setup/       Codex and optional NVIDIA peer setup
```

## Install

Open Codex in this folder and say:

```text
Read ONBOARDING.md and install this harness.
```

The installer must inspect existing skills first, back up collisions, install
the selected folders under `~/.codex/skills`, keep the `.claude` mirrors
aligned, and run the bundled validators.

The workflow skills run in either harness; the `coding-peers` peer table resolves peers and tools from the one detected at runtime. The optional files under `hooks/` and
`memory/` are retained for people who also use Claude Code; they are not
required for the Codex workflows.

## Requirements

- Either harness, with subagents. Persistent continuation needs a handle the harness
  actually has — goal tools, or `/loop` — and only when that mode is selected.
- Git for branch/worktree implementation flows.
- Isolated Chrome with a temporary profile and remote debugging for UI smoke
  tests.
- Python 3 for the bundled validators and Peer Bug Review ledger.

Optional external GLM, MiniMax, or NVIDIA peers are used only when explicitly
requested and only after the data-boundary gate.

## Verify the bundle

After installation:

```bash
python3 ~/.codex/skills/end-to-end-coding-session/scripts/validate_workflow_suite.py
python3 ~/.codex/skills/peer-bug-review/scripts/review_state.py self-test
python3 ~/.codex/skills/peer-bug-review/scripts/render_review_batch.py --self-test
python3 ~/.codex/skills/peer-bug-review/scripts/eval_peer_bug_review.py self-test
```

Also run Codex's `quick_validate.py` against every installed skill. See
`ONBOARDING.md` for the exact install and verification contract.

## Read next

1. `TUTORIAL.md` for normal use.
2. `skills/end-to-end-coding-session/SKILL.md` for the exact human-gated
   contract.
3. `skills/peer-bug-review/SKILL.md` for the audit and repair contract.
4. `setup/CODEX.md` and `setup/NVIDIA-KEYS.md` only when setup is needed.
