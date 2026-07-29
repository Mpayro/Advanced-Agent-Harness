---
name: coding-peers
description: Use for a fast, bounded, independent Codex review of a small or settled but important plan, code diff, shared seam, generated artifact, or focused implementation result. It is read-only by default, uses one fresh Terra reviewer unless two genuinely independent risk lanes justify parallel review, verifies every claim locally, and never creates a goal, branch, or commit. Use end-to-end-coding-session for broad implementation and peer-bug-review for exhaustive unknown bug surfaces.
---

# Coding Peers

## Boundary

This is a lightweight, Codex-only review protocol.

- Read-only is the default. A review request does not authorize edits.
- No persistent goal, plan artifact, branch, worktree, commit, push, or merge.
- Do not delegate implementation by default.
- The outer orchestrator owns routing and mutations.
- A peer finding is a hypothesis until reproduced against code/runtime.
- Never route work to another model provider unless the user explicitly requests
  a named external peer and the data-boundary gate allows it.

## Route Before Reviewing

| Scope | Action |
|---|---|
| Small/settled plan, diff, seam, or artifact | Use this skill |
| Multi-stage/cross-module implementation | Recommend `end-to-end-coding-session` |
| Explicit autonomous auto-commit | Recommend `end-to-end-coding-session-automatic` |
| Exhaustive repo/UI bug discovery or disputed findings | Recommend `peer-bug-review` |

Return the recommendation to the outer orchestrator. Do not recursively invoke
another outer workflow.

## 1. Confirm Review Authority

Classify the current request:

- **Review only:** inspect, reproduce, and report. Do not edit.
- **Repair authorized:** the user explicitly asked to implement/fix as well as
  review. Only then may the outer orchestrator repair confirmed in-scope defects.

Never infer Repair authority from "review," "audit," "what do you think," or a
request for a second opinion.

Inspect repo instructions and `git status`. In a dirty tree, construct the review
target from only the intended files/base/commit. Never send or review a broad
mixed diff as if it belonged to this task.

## 2. Build The Smallest Honest Review Packet

Every packet contains:

- Objective/current contract and explicit non-goals.
- Exact target artifact.
- One focused risk question per reviewer.
- Expected proof or negative control.
- Required output format.

Freeze the target before dispatch:

- Git: always save and SHA-256 hash the exact patch bytes. Save one canonical
  review manifest containing that patch path/digest and exact base/head when
  applicable.
- Non-git: canonical file paths and SHA-256 manifest.
- Plan/spec: full saved text plus SHA-256.
- Generated artifact: file plus producer, consumer, source version/freshness,
  and measurable invariants. Do not send raw operational rows unless needed and
  authorized.

The canonical review manifest is the one target identity for dispatch and
response; the peer attests to its digest and path. Review the CODE/artifact,
never a prose summary. A summary may explain intent but cannot replace the target.

## 3. Choose The Minimum Reviewer Set

Use one fresh Terra reviewer by default.

Use two parallel Terra reviewers only when their lanes are truly independent,
for example:

- Persistence/conservation vs UI/accessibility.
- Runtime/library semantics vs business invariant.
- Security/trust boundary vs ordinary correctness.
- Code diff vs generated-output provenance.

Do not ask two agents the same broad question. Do not consult every available
peer merely because it exists.

Use higher reasoning for auth, money, security, destructive operations, state
machines, or cross-module data contracts. Use lower reasoning for a small
localized review.

## 4. Demand Structured Evidence

Require non-empty content on every label's same physical line:

```text
TARGET_ARTIFACT: <sha256> <canonical-path>
VERDICT: ACCEPTED or REJECTED
FINDINGS: concise same-line summary or none
TESTS: exact checks/probes performed or unavailable
COUNTEREVIDENCE: strongest reason the finding may be false or none
```

Optional detail may follow. A malformed response is not a technical verdict;
reissue the unchanged target once to a fresh reviewer.

For plan/spec review, explicitly test:

- Identity and lifecycle/state transitions.
- Authoritative readers/writers and source of truth.
- Failure, recovery, rollback, and idempotency.
- Acceptance tests and production-promotion boundary.
- Simpler existing seam.

For code review, inspect the real diff and callers. For generated artifacts,
verify the artifact itself and its provenance, not only generator tests.

When correctness depends on a parser, library, scheduler, shell, or data source,
run a narrow runtime probe and a negative control. Documentation or peer
confidence is not runtime proof.

## 5. Verify Before Accepting A Finding

The outer orchestrator must:

1. Open the cited code/artifact.
2. Reproduce the claim or trace the controlling path.
3. Check the accepted contract/user intent.
4. Try the strongest counterexample.
5. Classify it as confirmed, false positive, needs user decision, or blocked.

Do not report an unverified causal story. This is especially important for
optimizer outputs and generated workbooks: a geometry-valid file can still
violate the business objective after a later manual/filler step.

### UI product proof

If the reviewed result builds or alters UI, or its changed behavior is reviewable
through a running UI, validate it with `computer-use:computer-use` before the
verdict:

- Launch Chrome with a temporary profile and remote debugging; do not reuse the
  user's normal browser profile.
- Exercise the affected route and changed journey plus one relevant negative or
  boundary path, and record routes, actions, visible results, and useful
  screenshots/logs.
- Stay inside review authority. Use local/preview state and disposable test data;
  do not edit source or perform destructive/production mutations without explicit
  authority.

If required UI proof is unavailable, mark it unavailable and do not accept the UI
claim as verified. Code-only findings may still be reported with that boundary.

## 6. Repair And Re-Review Only When Authorized

Under Review-only authority, stop after the verified report.

Under Repair authority:

1. The outer orchestrator fixes the smallest root cause.
2. Run the narrow mapped check.
3. Freeze the new target.
4. Use one fresh reviewer for one re-review.

Maximum: two technical review rounds total. If scope expands or intent is
unresolved, return a routing recommendation; do not escalate recursively or
invent authority.

## Optional Named External Peer

Use an external GLM/MiniMax/NVIDIA peer only when the user explicitly names it
or explicitly requests an external perspective.

- First use `delegating-to-external-models`.
- Redact secrets, customer data, private logs, and sensitive image/video content.
- Send only the relevant exact artifact/diff.
- Disclose what was sent and redacted.
- Validate a non-empty response.
- Retry transport once, then fall back to the permitted local reviewer.

External authorization never overrides current user/repo/model/data policy.

## Output

Keep the handoff short:

- Verdict.
- Confirmed findings with evidence.
- False positives/needs-decision items.
- Checks run or unavailable.
- Mutation status: none, or explicitly authorized repair.
- Routing recommendation if the task outgrew this skill.
