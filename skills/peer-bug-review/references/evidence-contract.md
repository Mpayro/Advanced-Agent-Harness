# Evidence contract

## Authority order

Determine expected behavior from the strongest current authority:

1. explicit current user intent and accepted acceptance criteria;
2. current product/business contract approved by the user;
3. externally imposed security, legal, accounting, or protocol invariant;
4. observable product semantics and durable data invariants;
5. current tests;
6. current docs/comments;
7. historical behavior.

If authorities conflict, do not silently choose the one that makes the finding look
like a bug. Classify `NEEDS_DECISION` and tag its reason as `CONTRACT_DRIFT`;
`CONTRACT_DRIFT` is not a separate terminal verdict.

## Required proof for `CONFIRMED_BUG`

Require all:

- exact affected version, branch, environment, and inputs;
- deterministic reproduction or a bounded flaky reproduction rate;
- expected result tied to an authority;
- actual result and user/business impact;
- negative control excluding environment, bad fixture, stale cache, intended
  configuration, and explicitly requested behavior;
- source-level root cause or the narrowest proven failing seam;
- caller/consumer scope;
- independent adversarial reproduction from raw artifacts.

A failing test alone is insufficient. A suspicious code pattern alone is
insufficient. Reviewer confidence is insufficient.

## Blind verifier packet

Provide:

- relevant repo instructions;
- raw files/diff/commands and minimal fixture;
- expected-behavior authorities, including conflicts;
- permission to inspect sibling callers and run read-only checks.

Do not provide:

- the finder’s final classification;
- the proposed fix;
- rhetorical labels such as “obvious bug”;
- reviewer verdicts from earlier rounds.

## Stage-locked review protocol

Start every gate prompt with:

```text
REVIEW_STAGE: confirmation | plan | fix | integration
TARGET_ARTIFACT: exact path, diff, or raw artifact being judged
AUTHORITY: current user/repo/model constraints that bound the review
DO_NOT_GRADE: artifacts that are context only
```

Before dispatch, run `review_state.py freeze-target` for the exact stage/finding and
pass every raw code, plan, diff, command-output, and product-evidence file with a
separate `--artifact-file`. The command writes one immutable, ledger-owned bundle for
that gate's next iteration. Give the reviewer that bundle path and digest; external
references are context only.

Every valid response must also contain exactly:

```text
TARGET_ARTIFACT: <bundle-sha256> <bundle-canonical-path>
```

The ledger re-hashes the bundle, binds it to stage/finding/iteration, and rejects a
second freeze for the same gate. Schema-v2 ledgers remain readable as
`legacy_unbound` history but cannot accept new review gates.

Grade only the named stage. In particular, a plan reviewer judges whether the plan
would work; it must not reject because the unimplemented code does not contain the
planned change. A fix reviewer judges the actual diff, and an integration reviewer
judges the assembled product.

Filter every blocker through the authority order before changing work. A request that
violates current user scope, repo instructions, model restrictions, or data boundaries
is invalid feedback, not a blocker.

If the response misses the required schema or uses an invalid verdict:

1. do not record it as a gate verdict or consume a review iteration;
2. let the ledger append its reviewer, frozen target, raw path/digest, and failure
   reason to `format_failures`;
3. do not normalize or paraphrase it yourself;
4. ask a fresh agent for a complete stage-valid response against the same frozen
   target.

For confirmation only, require this response:

```text
CLASSIFICATION: CONFIRMED_BUG | NOT_A_BUG | NEEDS_DECISION | DUPLICATE
REPRODUCTION: exact command/journey and observed result
AUTHORITY: why the expected result is authoritative
NEGATIVE_CONTROL: what was ruled out
ROOT_CAUSE: proven seam and affected consumers
COUNTEREVIDENCE: strongest reason this might not be a bug
```

Persist each response in its own evidence file using the exact section labels above.
Use a distinct Codex agent for every confirmation, plan, fix, and final integration
gate. Record the actual task path as `agent:<task-path>`; the ledger binds each
artifact digest and rejects reviewer or evidence reuse across the whole run. The
coordinator remains responsible for checking that the content is truthful.

Plan-review artifacts must contain `VERDICT:`, `PLAN:`, and `COUNTEREVIDENCE:`.
Fix-review artifacts must contain `VERDICT:`, `DIFF:`, `TESTS:`, and
`COUNTEREVIDENCE:`. Final-integration artifacts must contain `VERDICT:`,
`COVERAGE:`, `PRODUCT_CHECKS:`, `INTERACTIONS:`, and
`REMAINING_UNCERTAINTY:`.
Every required label must have non-empty content on that same physical line;
additional detail may follow below it. State this explicitly in every reviewer
prompt. A heading followed only by bullets on later lines is malformed evidence,
not a technical iteration.

Each response has exactly one controlling stage outcome. `CLASSIFICATION:` is valid
only for confirmation; plan, fix, and integration responses use `VERDICT:`. Do not
record an artifact that includes a controlling marker from another stage or any
trailing text after the one allowed controlling value.

## Workflow state transitions

| Mode/stage | Accepted or classified outcome | Ledger state | Terminal here? |
|---|---|---|---|
| Audit confirmation | confirmed bug | `confirmed_bug` | No; document and review the plan |
| Audit plan | accepted | `ready` | Yes for the finding; no product mutation is required |
| Repair plan | accepted | `ready` | No; implementation has not started |
| Repair fix | accepted | `accepted` | Yes for the finding |
| Any confirmation | not a bug, duplicate, or needs decision | matching classification | Yes for the finding |
| Integration | accepted | `complete` | Yes for the run |

An audit run with only `ready` and other terminal classifications is the explicit
no-change success path. In repair mode, `ready` is never completion.

## Late authority conflicts

If a plan, fix, or integration reviewer uncovers a real conflict between current
authorities, discard that technical response without consuming its iteration. Add a
separate candidate on the same inventory item with:

```text
--decision-for-stage plan|fix|integration
--decision-for-subject <finding-id|RUN>
```

Blindly confirm that candidate. A `NOT_A_BUG` or `DUPLICATE` clears the linked gate.
A `NEEDS_DECISION` blocks only the exact linked gate until one of these is appended:

```text
DECISION: exact user decision
AUTHORITY: why that decision now controls
RESOLVES: <decision-id> <stage>:<subject>:<technical-iteration>
```

Use `annotate-decision` for direct user authority, or `annotate-resolution` when a
related accepted fix resolves it. If the gate target was already frozen, use
`supersede-target --decision-id <id>`: the ledger keeps the old bundle, copies every
original byte into the replacement, appends the decision evidence, and permits that
decision to supersede the unconsumed target once. Then retry the original gate with a
fresh reviewer; its technical iteration number is unchanged.

## Historical resolution annotation

Do not rewrite a terminal classification when a later accepted related fix resolves
its uncertainty. Use `annotate-resolution` with a separate artifact:

```text
RESOLUTION: RELATED_ACCEPTED_FIX
RESOLVED_BY: exact accepted finding ID
PROOF: evidence that the related fix resolves the old uncertainty
REMAINING_UNCERTAINTY: what still remains, including none
```

The target remains `NEEDS_DECISION` historically; reports must show the appended
`resolved_by` relationship beside it.

## Lifecycle matrix

For stateful or business logic, test applicable axes:

- create/read/update/delete;
- before/after refresh, restart, retry, and cache expiry;
- partial, empty, maximum, invalid, and duplicate input;
- current, future, late, and boundary dates;
- draft, posted, cancelled, released, received, reconciled, and degraded states;
- same-run/cross-run and same-user/cross-user;
- permission, authorization, concurrent write, rollback, and idempotent retry;
- source failure, timeout, offline data, and stale snapshot.

The session that inspired this skill passed happy-path tests while missing a public
transaction bypass, carry loss after refresh, and release after refresh. Review the
whole lifecycle, not only the first reproduction.

## Review verdict rules

- Reject with a concrete reproduction or missing proof requirement.
- Do not reject for style preference.
- Do not accept because the suite is green.
- Verify reviewer claims locally before changing code.
- Count every rejected round deterministically.
- If disagreement is about product intent, stop labeling it a bug and request the
  decision.
