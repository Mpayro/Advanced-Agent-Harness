---
name: end-to-end-coding-session
description: Use when the user explicitly wants a multi-stage coding objective handled end to end with a human-approved plan, a living execution artifact, an explicit persistent-continuation or single-run choice, isolated implementation, verification, adversarial review, one optional heavy Peer Bug Review choice, and a stop-before-commit handoff. Triggers include "end-to-end coding session", "handle this objective end to end", "plan it and implement after I approve", "use a persistent goal", "córrelo en loop", and broad cross-module feature or refactor work. Do not use for a small bounded review, an explicitly automatic auto-commit workflow, or an exhaustive unknown bug hunt.
---

# End-to-End Coding Session

## Boundary

This is a human-gated workflow that runs in either harness. Human-gated is the
default for long work. The `coding-peers` §3b table resolves every peer, model,
and tool from the harness detected at runtime; never route work to a provider
outside it and External Peers. Respect stricter user, repo, data, and model
rules.

The workflow produces a tested, reviewed branch and stops before commit, unless
the approved plan carries release steps the user authorized — then it carries
those out under the same gates. See Release And Production Actions. It asks
exactly once whether to run the optional heavy `peer-bug-review`.

Use Ponytail full: understand the real flow, then make the smallest root-cause
change. Use Superpowers skills only when the user explicitly requests them or the
repo requires them.

The outer session owns routing, the selected persistence mode, the continuation
handle when used, and the terminal review state.
Sub-skills return bounded results; they do not start another outer workflow.

## Persistence Handle

Long work needs one handle so the run survives compaction and interruption. That
handle has a different name in each harness, so this skill calls the choice
`persistence_mode` and resolves the mechanism from the tools actually available:

| Available tools | Handle | Open | Read | Close |
|---|---|---|---|---|
| `create_goal`/`get_goal`/`update_goal` | goal | `create_goal` | `get_goal` | `update_goal(complete\|blocked)` |
| `ScheduleWakeup` | loop | `/loop`, re-armed each turn | canonical living plan plus the armed wakeup | `ScheduleWakeup(stop: true)` |

- `persistence_mode=persistent` opens the handle this harness has. Never invent
  goal state where no goal tool exists, and never arm a loop the user did not
  invoke or authorize in the alignment gate. If neither handle is available, say
  so and run `persistence_mode=none`.
- `persistence_mode=none` opens no handle; the living plan alone carries continuity.
- With a loop handle the canonical living plan *is* the objective record, so it
  must carry what a goal would hold: `workflow_owner`, `living_plan`,
  `terminal_contract`, and `persistence_mode`.
- Name the concrete handle out loud when asking or reporting: goal, or loop.
- A handle counts as available only if it actually holds. The loop handle
  depends on the harness re-arming it, and today it does not hold reliably in
  Claude. When it does not, say so and run `persistence_mode=none`: the living
  plan already carries continuity. Never report a run as persistent on a handle
  that is not re-arming.

## Step 0/8 — Route And Check Existing State

Start every progress update with:

`Skill step <N>/8 - <step name>: <short status>.`

Choose one lane before doing substantial work:

| Request | Lane |
|---|---|
| Small, settled plan/diff/artifact needing a second opinion | `coding-peers`; no handle |
| Multi-stage or cross-module implementation | This workflow |
| Explicit autonomous branch auto-commit | `end-to-end-coding-session-automatic` |
| Unknown/exhaustive repo or UI bug hunt | `peer-bug-review` |

An explicit request to use this full workflow overrides the small-task shortcut.
Return a routing recommendation rather than recursively invoking another outer
workflow.

Read the continuation handle before presenting a new persistence-mode choice:
`get_goal` where goal tools exist, otherwise the canonical living plan plus any
armed loop.

- No unfinished run: continue.
- Matching unfinished run: resume only when it also records the same
  `workflow_owner`, `living_plan`, `terminal_contract`, and
  `persistence_mode=persistent`; do not repeat completed investigation, re-ask
  the persistence question, or open a second handle.
- Same outcome but different workflow owner, plan identity, or terminal contract:
  treat it as a different unfinished run.
- Different unfinished run: do not overwrite, complete, or close it. Stop for the
  user's explicit decision about that run.

If a matching living plan already records a user-selected `persistence_mode=none`,
resume from it without re-asking or opening a handle. Never change modes silently.

Inspect repo instructions, current branch/worktree, and dirty state read-only.

## Step 1/8 — Ground And Confirm Alignment

Gather only the context needed to restate the objective:

- For a localized or skill-only change, use one direct scan.
- For broad or ambiguous repo work, use up to three complementary, read-only
  cheap-tier explorers: repo/instructions, code path/callers, and tests/tooling.
- For a true repo overview, use all three. Never create fake parallelism for the
  same question.
- Reuse an installed repo index if present. Do not install one for this scan;
  otherwise use structural search and `rg`.

Present a compact checklist:

- Outcome the user wants.
- In-scope tasks and explicit non-goals.
- Assumptions and constraints.
- Acceptance evidence.
- Ambiguities that could change behavior or authority.
- Persistence disclosure: the user must choose `persistence_mode=persistent` or
  `persistence_mode=none`; both modes keep the living plan and stop before commit.
- Adversarial peer, when the `coding-peers` table offers a choice in this
  harness. Settle it here so the later gates never interrupt the run.
- External-peer availability, checked here per the `coding-peers` External Peers
  section. If the key is missing, say so now with the setup pointer — never at
  the review gate, after the user has waited for the whole run.

The first alignment response must recommend one mode and ask, naming the handle
this harness would open (`goal`, or `loop`):

`¿Quieres ejecutarlo con continuidad persistente (<handle>) o sin ella? Recomiendo <modo> porque <razón breve>.`

- Recommend `persistent` when the work is long, complex, multi-stage,
  cross-module, interruption-prone, or likely to span compaction.
- Recommend `none` when the work is simple, bounded, low-risk, and likely to
  finish in one continuous run.
- Do not infer the choice from the recommendation. Wait for the user's explicit
  selection.

Ask the user to confirm the interpretation, the persistence mode, and the
adversarial peer in the same alignment gate. Record the peer in the living plan
and reuse it for every gate in this run; never stop mid-run to re-ask. For
`persistent`, explicitly record the authorization to open that handle. For `none`, record the opt-out and skip every open/close call. Do
not add a separate ceremony for it. Do not edit product files yet.

## Step 2/8 — Orient And Preflight

Read the real source-of-truth path end to end:

- Repo instructions, relevant docs, code, callers, tests, and generated artifacts.
- `git status`, current branch, linked worktrees, and ownership of existing dirt;
  inventory index and worktree dirt separately before task edits.
- Producer -> source version/freshness -> consumer lineage for generated outputs.
- Existing test, lint, typecheck, browser, database, and deployment conventions.

For stateful or data-model work, identify before planning:

- Stable identities and legal state transitions.
- Conservation/idempotency rules.
- Every authoritative reader and writer.
- Cache invalidation, restart/recovery, rollback, and audit history.

For user-facing work, plan an isolated Chrome profile with remote debugging.
For real operational data, separate read-only proof from authorized mutation.

If the request is still materially ambiguous, ask one short question. Otherwise
record the conservative assumption in the plan.

## Step 3/8 — Build And Adversarially Review A Living Plan

Create a living execution plan. Prefer the repo's plan convention; otherwise use:

`docs/superpowers/plans/YYYY-MM-DD-<short-goal>.md`

The artifact must contain:

- Goal, non-goals, scope, and acceptance evidence.
- Architecture/seams and smallest correct change.
- State transitions and business invariants when relevant.
- Producer/consumer lineage, source freshness, and artifact provenance.
- Ordered checkbox tasks and verification commands.
- Progress, decisions, surprises/blockers, review rounds, and
  `terminal_peer_review_state`.
- The user-selected `persistence_mode` and its recommendation rationale.

Use `coding-peers` as a read-only subprotocol on the full plan artifact. Use one
fresh adversarial reviewer by default, chosen per the `coding-peers` peer
table; add a second parallel reviewer only for a
distinct risk lane. The reviewer receives the real plan, not a coordinator
summary, and tries to refute hidden scope, missing tests, business/data risk,
and simpler alternatives.

Once the plan is final, also send it to the external peers per the
`coding-peers` External Peers section, when the opening gate found them
available. A third-party reader has none of this session's assumptions and is
the cheapest place to catch a wrong premise — before any code exists.

Verify each peer claim, external ones included. Revise only for confirmed issues
and record accepted, rejected, or deferred feedback in the living plan. Limit
plan review to two revisions; a repeated authority blocker returns to the user.

## Step 4/8 — Present Plan And Get Implementation Approval

Show at most five plain-language bullets: outcome, protected rule, proof, scope
boundary, and saved plan path. End by asking for explicit implementation approval.

Do not edit product code until the user approves.

After approval:

- For `persistence_mode=persistent`, re-read the handle. If no unfinished run
  exists, open it on the Step-1-authorized objective: outcome, in/out scope,
  acceptance evidence, and the pre-commit terminal condition. Record
  `workflow_owner=end-to-end-coding-session`, `persistence_mode=persistent`, the
  canonical `living_plan` path, and that `terminal_contract` — in the goal
  objective where goal tools exist, in the living plan where the handle is a
  loop. Resume an exact match; stop for the user if a different run exists.
- For `persistence_mode=none`, open no handle and mutate no handle state.
  Continue from the living plan and isolated worktree.

Never set `token_budget` unless the user supplied one.

## Step 5/8 — Implement On An Isolated Branch

Create or confirm a safe `agent/<short-goal>` linked worktree unless the user or
repo explicitly requires in-place work. Merely switching branches in a dirty
worktree is not isolation. Preserve unrelated dirt.

Record a task-owned patch manifest from exact task hunks, not only paths. When
in-place work is required, this saved patch is the review boundary; never stage
or commit unrelated index/worktree changes.

Immediately after worktree creation, run an environment-legibility preflight:

- Required non-secret local config is present or its absence is documented.
- Tests collect/start through the repo's pinned toolchain.
- Required database/browser/service endpoints are reachable when live proof is
  part of acceptance.

Unavailable live proof is `blocked/unavailable`, never silently equivalent to a
passing unit test.

Implement the approved plan continuously:

1. Add the smallest failing check for changed behavior.
2. Confirm it fails for the intended reason.
3. Make the minimal root-cause change.
4. Run the narrow check.
5. Update plan progress, decisions, and surprises.

Use subagents only for independent slices with explicit file ownership. Tell each
worker it is not alone and must preserve others' edits. Do not stop between
planned tasks. Stop only for a genuinely new scope/authority decision the user
must make.

## Step 6/8 — Verify The Outcome

Map every acceptance claim to evidence:

- Targeted unit/integration checks for changed behavior.
- Typecheck/lint only when relevant or customary.
- Full suite only when blast radius or repo convention justifies it.
- Generated artifact checks against producer, source freshness, consumer, and
  measurable business invariants.

If the implementation builds or alters UI, or the changed behavior is reviewable
through a running UI, validate it with the harness's UI proof tool from
`coding-peers` §3b before Step 7:

- Launch Chrome with a temporary profile and remote debugging; never reuse the
  user's normal browser profile for this smoke.
- Exercise the affected route and changed journey, plus one relevant negative or
  boundary path. Check the visible result rather than only DOM/code assertions.
- Use local/preview state and disposable test data. Do not perform destructive or
  production mutations without explicit authority.
- Record exact routes, actions, observed results, screenshots/logs when useful,
  and any inaccessible state.

If required UI proof cannot run, record `blocked/unavailable`; do not mark the UI
verified or substitute a green unit suite for product proof.

Record separately:

- `verified`
- `blocked/unavailable`
- `user-directed stop`
- `documented adjacent finding`

A consumer-only rerun from stale inputs may be successful but is not proof that
the upstream fix reached the output.

## Step 7/8 — Final Adversarial Review

Freeze the actual review target:

- Git repo: save and SHA-256 hash the exact task-owned patch bytes. Save one
  canonical review manifest containing that patch path/digest plus exact base/head
  when applicable; the reviewer attests to the manifest digest/path.
- Non-git files: canonical paths plus SHA-256 manifest.
- Generated output: artifact plus provenance and acceptance metrics.

Dispatch a fresh adversarial reviewer with no prior conclusions, chosen per the
`coding-peers` peer table and invoked per its Runner section. Require review of the
real target and any required Computer Use evidence for correctness, missed
requirements, security/data risk, over-engineering, and missing proof. Apply
Ponytail review to remove speculative layers.

Send the same frozen target to the external peers per the `coding-peers`
External Peers section, when the opening gate found them available. This is the
second and last external consultation: the plan was reviewed before the code
existed, and this reviews what was actually built against it.

Treat every finding as a hypothesis. Reproduce it in code/runtime, fix only
confirmed in-scope defects, re-run mapped checks, and re-review once. Adjacent
findings are documented, not silently added to scope.

## Step 8/8 — Optional Heavy Review And Pre-Commit Handoff

The outer session owns `terminal_peer_review_state`.

If absent, atomically set it to `pending` and ask exactly once:

`¿Quieres correr ahora Peer Bug Review pesado antes del commit? Audita el cambio y sus superficies afectadas con inventario, probes y revisión adversarial; puede tardar y consumir bastantes tokens. Responde sí o no.`

- While `pending`, wait. Do not ask again, commit, or claim completion.
- On **no**, set `declined`.
- On **yes**, set `accepted` and run `peer-bug-review` once in embedded mode over
  the final change and affected product surfaces. Disable recursive heavy-review
  offers. Repair only confirmed bugs inside approved scope.
- If it changes code, repeat Steps 6 and 7 without re-offering, then set
  `completed`.
- If it accepts unchanged, set `completed`.
- If incomplete, set `terminal_peer_review_state=blocked` and report the exact
  missing authority/environment.

Enter the handoff only from `declined` or `completed`. Report changed behavior,
exact verification, remaining risk, heavy-review outcome, branch/dirty state,
the saved task-owned patch, explicitly excluded unrelated dirt, and the proposed
commit/push/merge steps. Ask before commit.

If the approved plan carries release steps, execute them after that approval per
Release And Production Actions, then report what reached production.

Only in `persistence_mode=persistent`, close the handle as complete when the
tested/reviewed branch and resolved heavy-review choice have reached this
pre-commit terminal condition. Close it as blocked only after the same real
blocker recurs for at least three consecutive handle turns. A blocked terminal
review state alone does not authorize a blocked close.

In `persistence_mode=none`, close nothing; report the equivalent workflow
terminal or blocked state without creating handle state.

## Release And Production Actions

Touching production is scope, not a forbidden category. Deploying, promoting,
merging, pushing, and running a migration are ordinary steps when they are what
the work is for. Refusing them on principle would make the workflow useless for
the moment it matters most.

An action that reaches production runs when all four hold:

1. The approved plan names it, with its own acceptance evidence and rollback.
2. The user authorized that exact action for this run, naming it.
3. Every gate guarding it accepted: verification, adversarial review, and
   product proof.
4. It is reversible, or its irreversibility was disclosed and accepted before
   authorization.

Nothing else grants it. A plan that never mentions production does not acquire
it later; a reviewer cannot authorize it; approval of the code is not approval
of the release. Widening scope mid-run to include a release is the one thing
this section forbids.

Run release steps in the plan's order, verify each before the next, and stop at
the first failure with the rollback state stated. Report what reached production
and what did not.

## Stage Limits

| Stage | Limit | Stop condition |
|---|---:|---|
| Plan review | 2 revisions | Same authority blocker repeats |
| Failing check | 3 attempts | Root cause remains unclear or failure changes |
| Final diff review | 2 rounds | No new confirmed in-scope defect |
| External peer, if explicitly requested | 1 retry | Repeated empty/error/timeout |
| Heavy Peer Bug Review | 1 offer, 1 embedded run | Declined, completed, or blocked |

Repeat only the failed stage. Resume from the living plan after compaction, and
from the continuation handle only in `persistence_mode=persistent`; never restart
the whole workflow unless the user's objective changes.

## Final Response

Include:

- Changed: plain-language outcome.
- Verified: exact commands and smoke paths.
- Remaining risk or unavailable proof.
- Heavy Peer Bug Review state/verdict.
- Persistence mode and handle state; report `not used by user choice` for
  `persistence_mode=none`.
- Branch and dirty/clean state.
- Proposed commit, push/PR/merge, and cleanup plan.
- Skill-use summary: followed, changed/skipped with reason, stage retry counts,
  what worked, and what failed.

Do not commit, push, or merge unless the user explicitly asks.
