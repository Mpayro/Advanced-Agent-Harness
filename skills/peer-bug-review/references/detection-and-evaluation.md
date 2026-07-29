# Detection and evaluation

## Legibility preflight

Before judging code, prove the product is observable enough to judge:

- identify the real app, CLI, worker, DB, and browser entrypoints;
- locate accepted fixtures, logs, metrics/traces, and test commands;
- prove the app and required services can start without changing production data;
- identify safe ways to inspect persisted state and downstream side effects;
- record missing credentials, services, fixtures, or authority as `BLOCKED`.

Never turn an unobservable surface into “no candidate.” A blocked inventory item
prevents full integration acceptance.

## Build two maps

Keep both:

1. **Coverage map:** every typed inventory ID, including low-risk surfaces. This map
   proves what was and was not inspected.
2. **Attack map:** the same IDs ordered by risk and dependency centrality. Start with
   shared writers, state transitions, money/auth/destructive paths, date/unit
   calculations, persistence, external I/O, and high-fan-out UI actions.

Record `risk` (`low`, `medium`, `high`, or `critical`) and a numeric `priority` when
registering coverage. Priority controls order, never whether an item is covered.

## Deterministic probe phase

Static review proposes candidates; probes try to make behavior fail. Use only
repo-native, standard-library, or already-installed tools. Do not install a fuzzer,
mutation framework, browser dependency, or service only for the audit.

Choose probes by surface:

| Surface | Preferred probes |
|---|---|
| Pure calculation | boundary table, property/invariant, differential or metamorphic check |
| Parser/serializer | round-trip, malformed-input corpus, bounded fuzz |
| Stateful service/API | lifecycle matrix, restart/refresh, duplicate/retry, state-machine sequence |
| DB/persistence | constraints, transaction rollback, idempotency, orphan/duplicate queries |
| External I/O | timeout, partial response, retry, stale data, negative control |
| UI | click matrix plus console, network, persisted state, reload/back/duplicate submit |
| Existing tests | targeted mutation of a condition to prove the test can fail, then restore it |
| Workflow/skill contract | explicit transition table for no-op, mutation, decline, interruption, blocked state, last retry, nested invocation, and resume |

Treat agentic workflows as state machines, not prose. Trace every transition that can
stop, resume, retry, nest another workflow, or reach commit/completion. Include a
no-change success path: an accepted review that produces no diff must still reach its
documented terminal state.

Every covered evidence packet must include:

```text
PROBES: exact probes run, or why no executable probe applies
NEGATIVE_FINDINGS: risky hypotheses tested without producing a candidate
```

Never leave a mutation in the product tree. Prefer a temporary copy or an existing
mutation runner; if safe restoration cannot be guaranteed, skip it and state why.

## Orthogonal swarm

Divide agents by failure method as well as code ownership. Useful independent lanes:

- contract and business-invariant reconstruction;
- static data/control-flow and caller tracing;
- boundary/property/metamorphic probes;
- persistence/state-machine/restart probes;
- UI journey plus console/network inspection;
- tests-as-tests review: false greens, missing assertions, stale fixtures;
- operational recovery, degraded mode, observability, and deployment drift.

Agreement between agents using the same method is weak evidence. Prefer different
methods that converge on the same reproduction.

## Conditional patch tournament

Do not generate multiple patches by default. When two plausible root causes or seams
survive confirmation, permit at most two competing minimal patches. Judge them on the
same RED reproduction, sibling checks, blast radius, and contract. Keep one; discard
the other. If neither wins clearly, classify `NEEDS_DECISION`.

## Private benchmark

Use `scripts/eval_peer_bug_review.py` to measure the workflow independently of its
own confidence:

```bash
python3 scripts/eval_peer_bug_review.py generate --out /tmp/pbr-eval --seed 17
# Give only /tmp/pbr-eval/workspace to the audit agents.
python3 scripts/eval_peer_bug_review.py grade \
  --oracle /tmp/pbr-eval/grader/oracle.json \
  --report /tmp/pbr-report.json
```

The report format is documented in the generated workspace. Never expose
`grader/oracle.json` to discovery or verification agents. Track precision, recall,
classification accuracy, inventory coverage, elapsed time, and estimated tokens.
Optimize for recall without accepting false positives as confirmed bugs.

## Append-only trajectory

`review_state.py` writes a best-effort `<state>.events.jsonl` trajectory after every
successful state transition. The state JSON remains authoritative; the trajectory is
for replay, cost/quality comparison, and diagnosing loops. Never edit or truncate it
during a run. Preserve it with the final review artifacts.
