---
name: coding-peers
description: Use for a fast, bounded, independent peer review of a small or settled but important plan, code diff, shared seam, generated artifact, or focused implementation result. It is read-only by default, asks which adversarial peer to use and dispatches one fresh reviewer unless two genuinely independent risk lanes justify parallel review, verifies every claim locally, and never creates a goal, branch, or commit. Use end-to-end-coding-session for broad implementation and peer-bug-review for exhaustive unknown bug surfaces.
---

# Coding Peers

## Boundary

This is a lightweight review protocol. It runs in either harness; §3b decides
which peer does the work.

- Read-only is the default. A review request does not authorize edits.
- No persistent handle (goal or loop), plan artifact, branch, worktree, commit,
  push, or merge.
- Do not delegate implementation by default.
- The outer orchestrator owns routing and mutations.
- A peer finding is a hypothesis until reproduced against code/runtime.
- Runs in either harness. §3b resolves every peer, tool, and model from the
  harness actually detected at runtime, never from where this file is installed.
- Never route work to a provider outside §3b and External Peers unless the user
  explicitly names one and the data-boundary gate allows it.

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

In the same first response, settle the adversarial peer when the §3b table
offers a choice in this harness, and check external-peer availability per the
External Peers section. Asking later means stopping the run to ask; discovering
a missing key later means the user waited for nothing.

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

Use one fresh adversarial reviewer by default, chosen per the peer table in 3b
and already settled in step 1.

Use two parallel reviewers only when their lanes are truly independent,
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

## 3b. Peer Selection

This is the only place peers and model slugs are pinned. Every other skill
points here.

| Role | In Claude | In Codex |
|---|---|---|
| Adversarial or independent review gate | ask once at the start of the run: Sol or an adversarial Opus subagent | Sol (`gpt-5.6-sol`) |
| Bulk bug-review labor: explorers, verifiers, batches | Sonnet subagents | Luna (`gpt-5.6-luna`) |
| Heavy coding / implementation | Sonnet subagents, reviewed by Opus | Terra (`gpt-5.6-terra`) |
| UI product proof | `claude-in-chrome` | `computer-use:computer-use` |

Sonnet and Luna are the same tier. Which one does the work is decided by the
harness you are running in, never by the task. Terra is the Codex peer only;
running in Claude, heavy implementation is written by Sonnet and reviewed by
Opus.

**The slugs name a tier, not a version.** When a model is superseded, use the
newest model of that same tier and leave these roles untouched. A slug in this
table is an example of the tier, never a pin — this is the only table to update,
and no other skill may pin a version.

**Ask once, up front.** Running in Claude, settle the adversarial peer at the
start of the run, in the same breath as the other opening questions — Sol or an
adversarial Opus subagent — and reuse that answer for every gate in the run. A
review must never halt mid-flight to ask who should review it. The answer holds
for one run only; a new run asks again. If the `codex` command is not installed
there is nothing to ask: use the Opus subagent. Bulk labor is never asked about;
it always goes to the harness's cheap tier.

## 3c. Runner — How To Invoke Codex

Canonical read-only review call:

```bash
codex exec \
  --ignore-user-config \
  -m <slug> \
  -c 'model_reasoning_effort="medium"' \
  --ephemeral \
  -s read-only \
  --skip-git-repo-check \
  -C <repo> \
  < <packet.md> > <out.txt> 2>&1
```

- **Never pipe the output.** `| tail`, `| head`, `| grep` hold everything until
  the process exits, so a live run and a dead one look identical. Redirect to a
  file and watch its byte count.
- **Prompt over stdin** (`< packet.md`), not `"$(cat packet.md)"` in argv.
- **Pin `-m` and `model_reasoning_effort`.** Without both, the call silently
  inherits `~/.codex/config.toml` — today `gpt-5.6-sol` at `xhigh`, the slowest
  and costliest combination available.
- `--ignore-user-config` also drops the user's plugins, MCP servers, and hooks.
  Use it for every reviewer this skill dispatches. This skill never runs a peer
  with `-s workspace-write`: reviewers are read-only, and under Repair authority
  the outer orchestrator makes the change itself (§6). A workflow that owns a
  branch may relax the sandbox; this one owns none.

### Is it working or stuck?

Two valid signals: the output file's byte count is still growing (`wc -c`), and
`pgrep -f 'codex exec'` still returns the vendored binary.

These signals are dead — never conclude anything from them:

- `~/.codex/sessions/` — Codex stopped writing rollouts there on 2026-07-23;
  state lives in `~/.codex/state_*.sqlite`. A healthy run leaves nothing there.
- `%CPU` from `ps` — a lifetime average. A run streaming a long reasoning turn
  sits near 0% while perfectly alive.
- `ps ... | grep -i codex` — the ChatGPT desktop app's helper processes match
  the same pattern and bury the real one.

A review at high reasoning against a real repo runs for tens of minutes and
prints nothing for long stretches. Do not kill it while its output file grows.

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
through a running UI, validate it with the harness's UI proof tool from §3b
before the verdict:

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

## External Peers

A third-party peer sees the work without any of this session's assumptions, so
it catches what a same-family reviewer rationalizes. Consult one at the two
moments where being wrong is expensive: the finalized plan, and the finished
implementation.

**Check availability in the opening gate, not at the review gate.** Read
`~/NVIDIA_API_KEY.env`. Never pin model names here — that file declares which
models exist, their priority, and how to call them; follow its embedded
instructions.

- File present: external consultation is part of the run. Before the first send,
  name the peers and say what artifact leaves the machine, so the user can refuse
  it. A key on disk is a capability, never a standing consent.
- File absent: in the opening gate, tell the user once to create it and point
  to `setup/NVIDIA-KEYS.md`. Say plainly that it is optional and they can ignore
  it. Then continue — never block, never ask again this run — and mark the
  external perspective unavailable in the verdict. Never discover a missing key
  at the review gate; by then the user has waited for the whole run.

Every send:

- First use `delegating-to-external-models`. It is a data boundary, not a
  formality.
- Redact secrets, customer data, private logs, and sensitive image/video content.
- Send only the relevant exact artifact/diff.
- Disclose what was sent and redacted.
- Validate a non-empty response.
- Retry transport once, then fall back to the permitted local reviewer.

External findings are hypotheses like any other: reproduce them locally before
accepting one. External authorization never overrides current user/repo/model/
data policy.

## Output

Keep the handoff short:

- Verdict.
- Confirmed findings with evidence.
- False positives/needs-decision items.
- Checks run or unavailable.
- Mutation status: none, or explicitly authorized repair.
- Routing recommendation if the task outgrew this skill.
