---
name: end-to-end-coding-session-automatic
description: Use only when the user explicitly requests the autonomous variant of end-to-end-coding-session, explicitly chooses persistent-goal or no-goal execution, and authorizes automatic commit on an isolated branch. Fresh adversarial Luna reviewers approve the plan and final diff, the user still chooses once whether to run heavy Peer Bug Review, and the workflow never auto-pushes or merges. Do not infer this mode from a generic request to implement, move fast, or work end to end.
---

# End-to-End Coding Session — Automatic

## Boundary

This is a Codex-only, explicit-opt-in workflow. Never route work to another model
provider. It applies the `end-to-end-coding-session` contract by reference; it
does not invoke a nested base workflow.

The outer session owns routing, the living plan, the selected goal mode, goal
state when used, reviewer iterations, `terminal_peer_review_state`, and the
branch commit.

Human-gated end-to-end remains the default for long work. Automatic is allowed
only when both authority and task eligibility are explicit.

## Required Initial Consent

Follow base Step 0 and call `get_goal` before the first alignment response:

- Resume only a goal whose objective matches
  `workflow_owner=end-to-end-coding-session-automatic`, the same canonical
  `living_plan`, `goal_mode=persistent`, and the same auto-commit
  `terminal_contract`.
- Treat a same-outcome goal with any different identity field as a different
  unfinished goal.
- If a different unfinished goal exists, stop for the user; never overwrite,
  complete, or block it.

Use base Step 1 only for evidence gathering and objective/assumption grounding.
Apply its explicit goal-choice rule, but replace its goal timing and
stop-before-commit disclosure with this Automatic consent contract. The first
alignment response must ask:

`¿Quieres ejecutarlo con goal persistente o sin goal? Recomiendo <modo> porque <razón breve>.`

- Recommend `persistent` when the work is long, complex, multi-stage,
  cross-module, interruption-prone, or likely to span compaction.
- Recommend `none` when the work is simple, bounded, low-risk, and likely to
  finish in one continuous run.
- Do not infer the choice from the recommendation. Wait for the user's explicit
  selection and record `goal_mode=persistent` or `goal_mode=none`.

- The user selected Automatic.
- Eligibility will be checked read-only after alignment; only an eligible task
  in `goal_mode=persistent` creates one persistent Codex goal.
- In `goal_mode=none`, never call `create_goal` or `update_goal`; the living plan
  carries workflow continuity.
- Approved code will be committed automatically to an isolated branch.
- Nothing will be pushed or merged.
- The user will still get one terminal yes/no heavy-review choice.

Proceed only after the user explicitly confirms the understood scope,
goal mode, eligibility-before-goal creation, and isolated-branch auto-commit
authority. A generic "implement it" is insufficient.

## Eligibility Gate

After consent and before goal creation, run a read-only eligibility preflight.
It may inspect instructions, code, source lineage, `git status`, linked worktrees,
and required proof availability, but it may not edit. Route to human-gated
end-to-end without creating an Automatic goal if any is true:

- Business semantics or product intent remain unresolved.
- A constraint needs operator calibration or preference.
- Source version/freshness or producer/consumer lineage is unknown.
- The action is destructive, production-facing, or not safely reversible.
- The checkout cannot be isolated from unrelated dirt.
- Live database/browser/artifact proof is required but unavailable.
- Commit scope, target branch, or generated-output promotion is ambiguous.
- The reviewer would need to invent intent to approve.

Do not let a surrogate decide these questions for the user.

An explicitly separate, named, opt-in prototype may qualify when production paths
remain unchanged. Passing the prototype does not authorize promotion. Its plan
must include a later promotion checklist: entrypoint/scheduler wiring, migration,
failure propagation, rollback, and production verification.

If eligible and `goal_mode=persistent`, create the goal. Record outcome, in/out
scope, acceptance evidence,
`workflow_owner=end-to-end-coding-session-automatic`,
`goal_mode=persistent`, the canonical `living_plan`, and the auto-commit
`terminal_contract`: accepted plan, accepted final diff, resolved heavy-review
choice, verified isolated-branch commit. Never set a token budget unless the user
supplied one.

If eligible and `goal_mode=none`, create no goal and make no goal-state
transitions. Record the selected mode, eligibility result, and evidence in the
living plan.

## Base Steps 2 And 3

Run base Orient/Preflight and create the same living execution plan with:

- Goal, non-goals, acceptance evidence, and commit scope.
- State/business invariants and source lineage.
- Ordered tasks, progress, decisions, surprises/blockers, and verification.
- Automatic eligibility evidence.
- The user-selected `goal_mode` and recommendation rationale.
- Plan/code reviewer iterations.
- `terminal_peer_review_state`.

Use `coding-peers` only as a read-only subprotocol. Reviewers receive exact
artifacts, never the coordinator's summary.

## Step 4 Override — Adversarial Plan Gate

Do not ask the user to approve the plan. Freeze the full plan artifact and give
it plus the authorized objective to a fresh, no-context Luna reviewer.

Required output:

```text
TARGET_ARTIFACT: <sha256> <canonical-path>
VERDICT: APPROVE or REJECT
PLAN: non-empty same-line assessment
COUNTEREVIDENCE: non-empty same-line concern or none
```

The reviewer defaults to reject when evidence is missing. It is authoritative
only inside already-authorized deterministic scope; it cannot invent business
intent, widen scope, or authorize production/destructive effects.

On rejection:

1. Verify every blocker.
2. Revise the plan only for confirmed blockers.
3. Record accepted/rejected feedback.
4. Freeze the new artifact.
5. Use a fresh reviewer.

Limit: ten plan-gate attempts. Each attempt must use a fresh reviewer and the
latest frozen plan. A repeated intent/authority blocker routes to the user and
human-gated workflow; do not self-approve.

On approval, persist the accepted plan gate's exact digest and canonical path as
the immutable `approved_plan_target`. Continue through base Steps 5 and 6 without
user checkpoints. The living progress log may grow, but it cannot replace or
widen this accepted target.

## Step 7

Run the base final adversarial review on the exact diff/artifact and verify every
claim. This is evidence gathering, not the commit gate.

If the implementation builds or alters UI, or its changed behavior is reviewable
through a running UI, require the base Step 6 Computer Use smoke in Chrome with a
temporary profile and remote debugging. Include its routes, actions, visible
results, and negative/boundary probe in the final review and code-gate evidence.
Do not advance to the code gate or auto-commit when required UI proof is missing;
the task is blocked or was not eligible for Automatic.

## Step 8 Override — Adversarial Code Gate

Freeze the exact `approved_plan_target`, final task-owned patch/review manifest,
and verification evidence. Dispatch a fresh Luna reviewer.

Required output:

```text
TARGET_ARTIFACT: <sha256> <canonical-path>
APPROVED_PLAN: <sha256> <canonical-path>
VERDICT: APPROVE or REJECT
DIFF: non-empty same-line assessment
TESTS: non-empty same-line evidence
COUNTEREVIDENCE: non-empty same-line concern or none
```

Before accepting the verdict, mechanically compare both `APPROVED_PLAN` digest
and canonical path to the accepted plan-gate target. Any mismatch or scope
expansion returns to the user; it is not reviewer authority.

On rejection, reproduce each finding, repair only confirmed in-scope defects,
re-run mapped checks, freeze the new target, and use a fresh reviewer. Limit:
three code-gate attempts. Do not commit a rejected diff.

After approval, if `terminal_peer_review_state` is absent, atomically set it to
`pending` and ask exactly once:

`¿Quieres correr ahora Peer Bug Review pesado antes del commit? Audita el cambio y sus superficies afectadas con inventario, probes y agentes Codex adversariales; puede tardar y consumir bastantes tokens. Responde sí o no.`

The outer session owns `terminal_peer_review_state`:

- While `pending`, wait; do not ask again or commit.
- On **no**, set `declined`.
- On **yes**, set `accepted` and run `peer-bug-review` once in embedded mode,
  with recursive offers disabled.
- If heavy review changes code, repeat verification and a fresh post-heavy code
  gate, maximum two attempts; after that gate accepts, set `completed`.
- If heavy review accepts unchanged, set `completed`.
- If incomplete, set `terminal_peer_review_state=blocked`; do not commit.

Auto-commit only from `declined` or `completed`, and only from a verified clean
linked worktree. Use the accepted saved task-owned patch as the sole staging
input (`git apply --cached` or an equivalent patch-to-index operation), then
verify the cached diff digest equals the accepted code-gate patch before commit.
Abort on any other staged bytes. Use a conventional outcome-focused message.
Never auto-push or auto-merge.

Only in `goal_mode=persistent`, call `update_goal(complete)` after the commit
exists, mapped verification is green or honestly bounded, the final code gate
accepted, the heavy-review choice resolved, and the branch/worktree state is
reported.

Only in `goal_mode=persistent`, call `update_goal(blocked)` after the same real
blocker recurs for at least three consecutive goal turns.
`terminal_peer_review_state=blocked` is separate workflow state and does not by
itself authorize blocking the goal. In `goal_mode=none`, never call
`update_goal`; report workflow state only.

## Stop Conditions

| Gate | Limit | Then |
|---|---:|---|
| Eligibility | 1 determination | Route to human gate if any criterion fails |
| Plan approval | 10 fresh reviewers | Stop with blockers |
| Code approval | 3 fresh reviewers | Stop before commit |
| Post-heavy approval | 2 fresh reviewers | Keep review state blocked |
| Heavy review | 1 question, 1 embedded run | Declined, completed, or blocked |

Do not reset counters after compaction. Resume from the living plan and, only in
`goal_mode=persistent`, from the goal.

## Final Response

Report changed behavior, exact verification, eligibility result, plan/code gate
counts, heavy-review state, goal mode and goal state (`not used by user choice`
for `goal_mode=none`), commit SHA/message/branch, dirty state, remaining risk,
and the proposed push/PR/merge steps.

Do not push or merge unless the user explicitly asks.
