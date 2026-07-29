# Exhaustive repo overview

## Definition of exhaustive

Exhaustive means every enumerated surface is assigned and classified. It does not
mean proving that no undiscovered bug exists.

Build a coverage inventory from repository evidence before spawning agents. Prefer
an already-configured repo index; otherwise use structural search and `rg`. Do not
install a search dependency only for this audit.

Maintain two views of the same inventory: an exhaustive coverage map and a
risk/dependency-ranked attack map. The attack map controls order; it never removes
low-risk items from coverage.

Assign every inventory item a typed stable ID, risk, and numeric priority such as `module:pkg.name`,
`symbol:pkg.name/function`, `entrypoint:worker-name`, or `ui:route/action`. Register
IDs in the ledger and list them in a manifest containing `REPOSITORY:`, `COMMIT:`
(or an explicit `UNVERSIONED` value), and `INVENTORY:`. Freeze that hash-bound
manifest before candidate confirmation. Findings must reference one of those IDs.
The ledger enforces ordering and identity; the final integration reviewer still
verifies that the inventory itself matches the real repo.

## Inventory

Enumerate:

1. repo instructions, architecture docs, manifests, build/test commands;
2. source modules/packages and public symbols;
3. application, CLI, worker, cron, webhook, migration, and admin entrypoints;
4. DB schemas, transactions, caches, queues, filesystem and network boundaries;
5. auth, permissions, secrets, money, destructive operations, and audit history;
6. business state machines, calculations, dates, units, rounding, and invariants;
7. API/UI contracts and downstream consumers;
8. tests, fixtures, generated artifacts, deployment, monitoring, and recovery;
9. UI routes, navigation, tabs, forms, buttons, menus, modals, downloads, uploads,
   validation, loading, empty, error, permission, mobile, and accessibility states.

Generate a symbol inventory with the language’s native tooling when available.
Treat dynamic registration and reflection as separate surfaces rather than assuming
static symbol search found them.

## Default swarm lanes

Split large repos into bounded lanes and run waves until all inventory IDs are
claimed:

- architecture, entrypoints, config, and dependency boundaries;
- core business functions, calculations, units, and date boundaries;
- persistence, migrations, state transitions, transactions, cache, and concurrency;
- external I/O, degraded modes, retries, idempotency, and recovery;
- auth, permissions, security, privacy, money, and destructive actions;
- API contracts, serialization, compatibility, and downstream consumers;
- UI static review: state, forms, routing, accessibility, and error handling;
- UI click exploration: every interactive journey and state;
- tests/tooling/build/deploy: missing assertions, false-green tests, and drift.

Small repos may combine lanes. Large repos should divide by package within each
lane. Assign file ownership only during implementation, never discovery.

## Explorer packet

Give each explorer:

- exact inventory IDs and paths;
- risk/priority plus the reason the lane is ordered there;
- read-only constraint;
- relevant repo instructions;
- expected output budget;
- permission to run narrow, non-mutating checks;
- prohibition on calling anything a confirmed bug.

Require:

```text
COVERED: inventory IDs, files, symbols, and journeys
CANDIDATES: symptom, evidence, possible authority, repro idea
PROBES: boundary/property/state/UI probes run, or why none applies
NEGATIVE_FINDINGS: risky areas checked without a candidate
GAPS: items not actually inspected and why
COMMANDS: read-only checks performed
```

For a skipped item, its evidence packet must instead contain `SKIPPED:` and
`REASON:`. For a blocked item, use `BLOCKED:` and `MISSING:`. These are structural
guards; the integration adversary must still compare the manifest with the actual
repository and reject vague IDs such as `everything`.

## UI click matrix

Use isolated Chrome with a temporary profile and remote debugging. Start from a
known clean app state. For each route or surface, exercise applicable:

- initial load and reload;
- keyboard and pointer navigation;
- every visible action;
- valid, invalid, empty, boundary, and duplicate input;
- cancel, back, refresh, retry, and double-submit;
- loading, timeout, offline, permission-denied, and server-error states;
- filters, sorting, pagination, selection, modal focus, and downloads/uploads;
- desktop and narrow viewport;
- persisted state across refresh/login when promised.

Capture console/network errors and verify downstream state, not just visual success.
Do not use real destructive production actions unless explicitly authorized; use
fixtures, preview, sandbox, or stop before the final mutation.

## Coverage completion

Coverage is complete only when every inventory ID is one of:

- `covered` with evidence;
- `skipped` with a defensible reason;
- `blocked` with the exact missing authority or environment, reported as incomplete
  coverage that prevents a full integration acceptance.

Do not hide blocked or dynamic surfaces inside a percentage.
Store the supporting module/symbol/journey list in a non-empty evidence file; a
one-word assertion is not sufficient review evidence even though semantic quality
ultimately remains the reviewer’s responsibility. One explorer packet may support
multiple items only when its `COVERED:` content names every bound inventory ID;
the ledger rejects a coverage link when the item ID is absent.
