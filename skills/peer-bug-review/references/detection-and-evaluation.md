# Detection and evaluation

## Legibility preflight

Before judging code, prove the product is observable enough to judge:

- identify the real app, CLI, worker, DB, and browser entrypoints;
- locate accepted fixtures, logs, metrics/traces, and test commands;
- prove the gates can fail — the gates whose green you are about to lean on, which
  is the test configs, the CI gate scripts, and any baseline or golden file they
  read, not every job in the repo. Their inputs are non-empty, their failure branch
  is reachable, and every key their config declares is read by something. A
  baseline nobody populated, a glob that matches no file, a declared assertion no
  code parses — each turns every green behind it into noise, and none can be caught
  by mutating the product;
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

## Vacuous green

A passing test is not coverage until you have seen it fail. Two shapes recur often
enough to hunt for them by name in every block you touch:

- **Dead anchor** — the test compares output against an artifact frozen at an
  earlier moment: a pinned fixture, a recorded snapshot, a checked-in golden file.
  Green means nothing changed since the freeze, not that current behaviour is
  right. The assertion is real; the thing it asserts against is dead.
- **Uncompared twin** — two paths resolve the same fact by different routes, each
  with its own green test, and nothing asserts they agree. The defect lives in the
  gap between them, so no test that stays inside one path can see it.
- **Borrowed authority** — the test names a source in its title or comment and
  never opens it, asserting instead against a literal copied out of it. Red-first
  does not catch this one: break the module and it goes red, so it reads healthy.
  The drift is between the copy and the source, not between the test and the code.
  The probe is to open the named source and diff it against the literal.

The first two show up in no static read — both sides look correct in isolation.
The rule that catches them:

> A passing test may not be cited as the reason a candidate is not a bug until you
> have broken what it claims to protect and watched it go red.

Bounded on purpose: this is the price of killing a candidate or calling a touched
seam safe, never a sweep over the inventory. The orchestrator breaks it, in a copy
outside the tree or with an existing mutation runner, and restores — this holds in
audit mode, where a copy is not a product write. Where nobody can, the test is not
available as a reason: kill the candidate on the code or leave it open. Record the
result. A test that stays
green under mutation is itself a candidate: register it against the inventory ID
it was supposed to cover. Where two resolutions of the same fact exist, the probe
is a differential check across them, never more tests on either side.

## Orthogonal swarm

Divide agents by failure method as well as code ownership. Useful independent lanes:

- contract and business-invariant reconstruction;
- static data/control-flow and caller tracing;
- boundary/property/metamorphic probes;
- persistence/state-machine/restart probes;
- UI journey plus console/network inspection;
- tests-as-tests review: vacuous green above, missing assertions, stale fixtures;
- operational recovery, degraded mode, observability, and deployment drift.

Pick lanes by inventory risk, and include tests-as-tests whenever a candidate will
be confirmed or killed on the word of a test.

Lanes with a textual signature screen before they read: on a large surface the
first move is a grep for that lane's own failure signatures across every file, then
a full read of only the strongest hits. Front-to-back reading costs hours and finds
less. Lanes without one — invariant reconstruction, UI journey, operational
recovery — go straight to reading. Report how many files were screened and how many
were opened, so the coverage claim stays honest about which was which.

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
