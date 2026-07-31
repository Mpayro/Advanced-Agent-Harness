---
name: peer-bug-review
description: Run an evidence-gated, multi-agent bug audit or repair workflow over a reported bug or an entire repository. Use when the user asks for a repo overview, exhaustive module/function review, business-logic bug hunt, UI click exploration, adversarial bug confirmation, per-bug plans, reviewed fixes, a swarm audit, or an end-to-end repair loop that must distinguish real bugs from intended behavior and finish with a whole-product integration review.
---

# Peer Bug Review

## Purpose

Find credible bug candidates, prove or reject each one independently, and—only
when repair is authorized—carry confirmed bugs through reviewed plans, TDD fixes,
adversarial re-review, and a final whole-product gate.

Promise evidence discipline, not mathematical absence of bugs. Say “all enumerated
surfaces were covered and all candidates were classified,” never “the repo has no
bugs.”

## Required companions

- Always apply `ponytail` full.
- In repair mode, use `end-to-end-coding-session` for branch/worktree, plan gate,
  TDD, verification, and stop-before-commit behavior.
- Use `coding-peers` or local subagents for independent review when available.
- Route every spawned explorer, verifier, reviewer, implementer, and integration
  adversary through the cheap native model for the active harness: Sonnet in
  Claude/Claude Code, or the cheap Codex tier in Codex. Slugs live only in
  `coding-peers` §3b; never pin a version here. Detect the harness from the
  runtime, not the skill path. In Codex, use the local `codex exec` adapter when
  the thread subagent tool does not expose that tier. Never upgrade this
  workflow's subagents to the review or implementation tiers.
- Keep exactly one workflow owner for confirmation, planning, fix review, and
  verification. If an outer loop already owns a compatible gate, use that evidence
  instead of spawning a duplicate gate.
- Follow repository `AGENTS.md`, model restrictions, data boundaries, and
  concurrency limits before this skill.

## Load the resources

- Always read `references/evidence-contract.md`.
- Always read `references/detection-and-evaluation.md`.
- Read `references/repo-overview.md` when no concrete bug is supplied or the user
  requests whole-repo, module/function, business-flow, or UI coverage.
- Read `references/runtime-adapters.md` before creating a goal/loop or spawning the
  swarm.
- Copy `assets/bug-spec-template.md` for every confirmed bug when durable artifacts
  are authorized.
- Use `scripts/review_state.py` for counters and gate state. After writing a
  confirmed bug spec, record it with the script’s `document` command. Do not track
  verdicts only in prose. Feed coverage and review commands non-empty evidence files;
  the ledger binds their absolute paths and SHA-256 digests.
- Tell every reviewer that each required evidence label needs non-empty content on
  the same physical line. If the response violates that format, record the format
  failure and reissue the unchanged target to a fresh reviewer.
- If an accepted related fix later resolves a historical `NEEDS_DECISION`, preserve
  the original classification and record the relationship with
  `review_state.py annotate-resolution`.
- When developing or calibrating this skill, use
  `scripts/eval_peer_bug_review.py` with its hidden oracle. Do not expose the oracle
  to audit agents or treat self-agreement as an evaluation.

## Choose the mode and profile

- **Audit:** Default for “review,” “audit,” “find bugs,” or “repo overview.” Remain
  read-only except for explicitly requested review artifacts.
- **Repair:** Use only when the user explicitly asks to fix, implement, or handle
  confirmed bugs end to end. Respect the plan-approval gate from
  `end-to-end-coding-session`; a review request alone is not edit authorization.
- **Direct bug:** Start from the reported symptom, but still trace sibling callers
  and adjacent lifecycle states.
- **Repo overview:** Build the coverage inventory first, then run the swarm. Never
  start with random file sampling.
- **Fast profile:** Default. Inspect every frozen inventory item once, work in
  closed repair waves of at most eight bugs, batch up to four unrelated targets
  at the same review stage, and use at most three plan iterations. Low/medium-risk
  bugs with deterministic RED proof may waive the separate plan-review agent;
  confirmation and post-fix review remain mandatory.
- **Exhaustive profile:** Use only when the user explicitly requests exhaustive,
  prolonged, swarm, or multi-round coverage. Preserve separate confirmation,
  plan, fix, and integration gates with the existing 10-iteration ceiling.

## Progress contract

Begin progress messages with:

`Peer Bug Review step <N>/8 - <name>: <status>.`

When a stage repeats, include the bug ID and iteration, such as:

`Peer Bug Review step 6/8 - Fix review: BUG-004 rejected, iteration 2/10.`

## Workflow

### 1. Bootstrap one controlled run

Inspect repo instructions, git/worktree/dirty state, available tools, test commands,
runtime, model permissions, and concurrency cap. Record pre-existing changes and
baseline failures before attributing anything to this run.

Run the legibility preflight from `references/detection-and-evaluation.md`: prove the
real entrypoints, safe fixtures, logs/state inspection, and required services are
observable. Register an unobservable surface as blocked; never translate missing
evidence into “no candidate.”

Create exactly one persistent objective for the whole run. Use one Codex goal only
when the user explicitly invoked a persistent audit/repair and the goal tool is
available; otherwise use the state file as the loop owner.

Initialize the state ledger with `--profile fast` unless exhaustive work was
explicitly requested. Keep it outside product paths in audit mode unless the user
requested repo artifacts.

### 2. Inventory the actual surface

For a direct bug, map the entrypoint, callers, writers/readers, persistence,
downstream consumers, tests, and user journey.

For repo overview, follow `references/repo-overview.md` and enumerate:

- modules/packages and entrypoints;
- public functions/classes and high-risk private seams;
- jobs, CLIs, workers, migrations, schemas, caches, and external I/O;
- business state machines and time-dependent flows;
- UI routes/tabs/forms/buttons/modals and empty/error/permission states;
- test, build, deployment, security, and observability surfaces.

Build both maps from `references/detection-and-evaluation.md`: the coverage map and
the risk/dependency-ranked attack map. Every item must be assigned to a lane,
covered, or skipped with a reason. Generated, vendored, fixture, and unreachable code
may be skipped explicitly. In fast profile, scope the frozen inventory to the
current bounded pass; do not claim whole-repo exhaustiveness.

Register every item with a stable inventory ID containing a type separator, such as
`module:pricing`, `symbol:pricing.calculate`, or `ui:orders/submit`. Write the
inventory manifest, then freeze it with `review_state.py freeze-coverage
--manifest-file <path>`. Candidates may only be added after that freeze and must
reference an existing inventory ID. Later coverage updates may change
status/evidence but may not add or reassign items.

Register `--risk low|medium|high|critical` and a numeric `--priority` for each item.
Start with central high-risk seams, but exhaust the full coverage map before closing.

### 3. Run the discovery swarm

Reserve one concurrency slot for the coordinator. Fill remaining slots with small,
read-only explorers.

- Use the active harness's required cheap model for every explorer: Sonnet in
  Claude/Claude Code, or the cheap Codex tier from `coding-peers` §3b in Codex.
- Never violate repo/model instructions to satisfy a preferred model name.
- Give each explorer a disjoint code or failure-method lane and an output budget.
- Require covered symbols/journeys, commands/evidence, candidates, and gaps.
- Explorers report `CANDIDATE`, never `BUG`, and never edit.

Use orthogonal methods rather than several agents repeating the same static review.
Run the deterministic probe phase from `references/detection-and-evaluation.md`;
covered evidence must name `PROBES:`, `NEGATIVE_FINDINGS:`, and `COMMANDS:`. Use only
repo-native, standard-library, or already-installed tools.

In fast profile, inspect each inventory item once and immediately record it as
covered, skipped, or blocked with evidence. Do not rescan a covered lane. Candidates
discovered later go to the next wave unless they are critical or caused by the
current diff. In exhaustive profile, run additional waves until the frozen inventory
is exhausted; clean-round repetition is not required unless the user requested it.

For UI, click every enumerated action in isolated Chrome with a temporary profile and
remote debugging; include normal, empty, invalid, retry, permission, refresh, and
back/forward states where applicable. Capture console/network evidence and downstream
state, not only screenshots.

### 4. Confirm candidates blindly

Deduplicate candidates by root cause before review. Dispatch remaining candidates
in same-stage batches of at most four unrelated targets. A cheap agent may review one
batch, but it must grade every target independently from its own raw bundle and may
not review the same finding at another stage.

Give the verifier raw code/runtime artifacts, the applicable authority sources, and
the reproduction surface. Do not provide the finder’s conclusion or intended fix.
Freeze those raw inputs with `review_state.py freeze-target` before dispatch. Persist
one evidence artifact and one logical reviewer identity per target. For a batched
local runner use `agent:<runner-id>/<batch-id>/<finding-id>/<stage>`; the ledger
rejects logical-identity, response-evidence, or frozen-target reuse.

Use the stage-locked packet and structured-output rules from
`references/evidence-contract.md` at every confirmation, plan, fix, and integration
gate. With the local runner, pass `references/review-output.schema.json`, then render
canonical per-target evidence with `scripts/render_review_batch.py`. Never normalize
an agent verdict manually.

Apply `references/evidence-contract.md`. Classify each candidate as exactly one:

- `CONFIRMED_BUG`
- `NOT_A_BUG`
- `NEEDS_DECISION`
- `DUPLICATE`

Only `CONFIRMED_BUG` advances to planning. Tests and old docs are evidence, not
automatic product truth.

If a plan, fix, or integration gate discovers a new authority conflict, follow the
linked-decision and target-supersession protocol in
`references/evidence-contract.md`. Do not turn it into a technical rejection or
consume that gate's iteration.

### 5. Write and attack one plan per bug

Create one spec per confirmed bug from `assets/bug-spec-template.md`. Include root
cause, all affected callers, business invariant, RED test, lifecycle matrix,
minimal seam-level change, targeted checks, product proof, and excluded scope.
Record the existing non-empty spec artifact before plan review; the ledger rejects
plans without it and detects later artifact changes.

In fast profile, a confirmed bug may waive the separate plan-review agent only when
its inventory risk is low or medium, the spec contains deterministic RED proof, and
the change excludes security, money, authorization, concurrency, migrations,
destructive behavior, and cross-module contracts. Record the waiver with
`review_state.py waive-plan`; the post-fix review remains mandatory.

Otherwise send the plan to a fresh adversarial review context. Ask it to find:

- a simpler shared seam;
- missing readers/writers or cross-module parity;
- time, cache, restart, retry, concurrency, partial-state, and degraded-mode gaps;
- stale tests/specs that encode old intent;
- missing negative controls and regression proof.

Freeze the current spec and plan evidence as that iteration’s plan target before
dispatch.

Record `ACCEPTED` or `REJECTED` in the state ledger. Revise only the rejected plan,
not the whole audit.

If two root-cause seams remain equally plausible, use the conditional patch tournament
from `references/detection-and-evaluation.md`: at most two minimal patches against the
same RED proof. Do not generate alternative patches when one root cause is established.

### 6. Repair with failure-first evidence

After plan approval or a valid fast-profile waiver and user authorization, let
`end-to-end-coding-session` own the safe branch/worktree and implementation
discipline.

When an end-to-end session invokes this skill from its terminal heavy-review offer,
run in **embedded mode**: the outer approved plan, authorization, branch/worktree, and
terminal state remain authoritative. Do not re-enter end-to-end Steps 1 or 4, create
another branch, commit, or emit another terminal heavy-review offer. Return
`completed` only after this skill’s integration gate accepts; return `blocked` for
missing authority/environment so the outer workflow cannot commit.

Repair non-overlapping bugs in closed waves of at most eight. For each bug:

1. Reproduce RED on the baseline.
2. Change the smallest shared root-cause seam.
3. Run the narrow GREEN check.
4. Run sibling/lifecycle checks.
5. Send the actual diff and raw test output to a fresh review context; batch up to
   four unrelated fixes in one cheap-agent call.
6. Verify every reviewer claim locally before changing code.
7. Repeat only that bug’s failed stage.

Parallelize implementation only across non-overlapping ownership. Serialize bugs
that share files, state, schema, or business invariants.

### 7. Prove the assembled product

Run narrow RED/GREEN and sibling checks per bug. Run the full suite, lint, typecheck,
build, and security checks once per repair wave when relevant, then again only at the
final assembled-product gate. After all individual fixes are accepted, run
risk-mapped verification:

- targeted tests per bug;
- integration tests across shared seams;
- baseline comparison for pre-existing failures;
- full suite when blast radius or repo convention justifies it;
- real product smoke for affected journeys;
- UI click matrix in isolated Chrome for user-facing changes;
- DB/invariant/migration checks for persistence changes;
- build/type/lint/security checks only when relevant.

Then spawn one fresh integration adversary. Give it the original user request,
coverage map, bug specs, final diff, exact test/smoke evidence, and unresolved
classifications. Require it to check interactions among fixes and the final product,
not merely review each patch again.

Freeze that assembled packet as the integration target before dispatch.

Preserve the ledger’s append-only `.events.jsonl` trajectory with the review
artifacts. It is diagnostic evidence, not an approval authority.

### 8. Close only on the real stop condition

Finish only when:

- every inventory item is covered or explicitly skipped;
- every candidate has a terminal classification;
- every confirmed bug is documented;
- in repair mode, every confirmed bug’s fix is adversarially accepted;
- the assembled product passes its mapped checks;
- the integration adversary accepts the set;
- remaining uncertainty and untested surfaces are stated plainly.

If a bug reaches 10 review iterations, or the same blocker repeats twice without
new evidence, mark it documented-blocked and request the smallest necessary user
decision. A documented-blocked bug may close an audit report, but it prevents a
repair run from completing. Never convert exhaustion into acceptance.

## Final handoff

Report:

- coverage by lane and honest exclusions;
- confirmed bugs, rejected candidates, duplicates, and decisions needed;
- historical decisions resolved by related accepted fixes;
- per-bug plan/fix/review counters;
- final integration verdict;
- exact tests and product journeys exercised;
- deterministic probes, negative findings, and trajectory path;
- remaining uncertainty;
- branch/worktree and dirty state;
- in repair mode, the stop-before-commit plan from `end-to-end-coding-session`.

Include a short skill-use audit: steps followed, substitutions, failed agents,
loops, what went right, and what went wrong.

## Hard limits

| Stage | Default | Hard stop |
|---|---:|---:|
| Explorer transport retry | 1 | 1 |
| Candidate confirmation | 2 | 3 |
| Plan review, fast | 1 | 3 per bug |
| Plan review, exhaustive | 2 | 10 per bug |
| Fix review | 3 | 10 per bug |
| Suite/product retry | 2 | 3 |
| Repeated identical blocker | 2 | Document and escalate |

Do not restart the whole workflow when one stage fails.
