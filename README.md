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

1. Routes the request and checks for an existing Codex goal.
2. Reads the real repo path, callers, tests, instructions, branch, and dirty
   state before planning.
3. Restates the objective and asks you to confirm its understanding and
   persistent-goal authority.
4. Writes a living plan, has a fresh Codex reviewer attack it, and asks you to
   approve implementation.
5. Implements the approved plan in an isolated worktree with failure-first
   evidence.
6. Verifies the acceptance claims, including an isolated-Chrome product smoke
   for UI work.
7. Freezes and reviews the exact task-owned patch, not a prose summary.
8. Asks once whether to run the heavier Peer Bug Review, then stops before
   commit.

The workflow preserves unrelated changes and never commits, pushes, or merges
without explicit authority.

## Automatic variant

Run:

```text
end-to-end coding session automatic: migrate the auth middleware
```

Automatic is explicit opt-in. It first checks that the task is deterministic,
reversible, isolated, and fully provable. Fresh reviewers get up to three plan
gates and three code gates. You still choose once whether to run Peer Bug
Review. After acceptance it commits only the approved patch to the isolated
branch; it never pushes or merges.

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
    scripts/review_state.py
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

The workflow skills are Codex-only. The optional files under `hooks/` and
`memory/` are retained for people who also use Claude Code; they are not
required for the Codex workflows.

## Requirements

- Codex with subagents and goal support.
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
