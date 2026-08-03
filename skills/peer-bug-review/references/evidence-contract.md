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

When authorities conflict, never silently pick the one that makes the finding
look like a bug. Classify `NEEDS_DECISION` and say which authorities disagree.

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

Every recorded artifact must also contain exactly:

```text
TARGET_ARTIFACT: <bundle-sha256> <bundle-canonical-path>
```

Never ask the reviewer to echo that digest — `render_review_batch.py` stamps it
from the frozen target. Use the structured path below for every ledger gate;
hand-written evidence is the fallback only where that path is unavailable.

The ledger re-hashes the bundle, binds it to stage/finding/iteration, and rejects
a second freeze for the same gate.

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
4. ask a fresh review context for a complete stage-valid response against the same
   frozen target.

For confirmation only, require this response:

```text
CLASSIFICATION: CONFIRMED_BUG | NOT_A_BUG | NEEDS_DECISION | DUPLICATE
REPRODUCTION: exact command/journey and observed result
AUTHORITY: why the expected result is authoritative
NEGATIVE_CONTROL: what was ruled out
ROOT_CAUSE: proven seam and affected consumers
COUNTEREVIDENCE: strongest reason this might not be a bug
```

Persist each target response in its own evidence file using the exact section labels
above. A cheap agent may evaluate up to four unrelated targets at the same stage in
one batch, but it may not review the same finding at another stage. Record a logical
identity per target as `agent:<task-path>` or
`agent:<runner-id>/<batch-id>/<finding-id>/<stage>`; the ledger binds each artifact
digest and rejects logical identity or evidence reuse. The coordinator remains
responsible for checking that the content is truthful.

## Structured batch output

For `codex exec`, pass `references/review-output.schema.json` with
`--output-schema` and capture the last message with `-o`. Render the batch into
canonical per-target evidence:

```bash
python3 scripts/render_review_batch.py <batch-result.json> <evidence-directory>
```

One stage and at most four targets per batch. The renderer is the only permitted
normalization layer; never hand-edit a malformed verdict into compliance.

Required labels per stage — plan: `VERDICT:`, `PLAN:`, `COUNTEREVIDENCE:`. Fix:
`VERDICT:`, `DIFF:`, `TESTS:`, `COUNTEREVIDENCE:`. Integration: `VERDICT:`,
`COVERAGE:`, `PRODUCT_CHECKS:`, `INTERACTIONS:`, `REMAINING_UNCERTAINTY:`. Every
label carries non-empty content on its own physical line; a heading followed only
by bullets is malformed evidence. State this in every reviewer prompt.

One controlling outcome per response: `CLASSIFICATION:` for confirmation,
`VERDICT:` everywhere else. Never record an artifact carrying another stage's
marker.

## Fast plan waiver

The fast profile may omit a separate plan-review agent only when all are true:

- the frozen inventory risk is `low` or `medium`;
- confirmation independently returned `CONFIRMED_BUG`;
- the bug spec contains a deterministic RED proof and one minimal root seam;
- the change does not touch security, money, authorization, concurrency,
  migrations, destructive behavior, or a cross-module contract.

Record a separate coordinator artifact containing:

```text
WAIVED: PLAN_REVIEW
RED_PROOF: exact failing check
ROOT_SEAM: one minimal seam
SCOPE: affected callers and bounded files
EXCLUSIONS: why every mandatory full-gate category is absent
```

Then run `review_state.py waive-plan`. This transitions the finding to `ready`
without fabricating a reviewer. Confirmation and post-fix review remain mandatory.
High/critical findings and exhaustive-profile runs may never use this waiver.

## When a finding is done

`review_state.py summary` prints the live states; it owns them, not this file.
Two rules the states do not carry on their own: an audit run holding only `ready`
and other terminal classifications is the explicit no-change success path, and in
repair mode `ready` is never completion — only `accepted` is.

## Late authority conflicts

If a plan, fix, or integration reviewer uncovers a real conflict between current
authorities, discard that technical response without consuming its iteration. Add a
separate candidate on the same inventory item with:

```text
--decision-for-stage plan|fix|integration
--decision-for-subject <finding-id|RUN>
```

Blindly confirm that candidate. A `NOT_A_BUG` or `DUPLICATE` clears the linked
gate. A `NEEDS_DECISION` blocks only that gate until a decision is appended with
`annotate-decision` (direct user authority — `DECISION:`, `AUTHORITY:`,
`RESOLVES:`) or `annotate-resolution` (a related accepted fix resolved it —
`RESOLUTION:`, `RESOLVED_BY:`, `PROOF:`, `REMAINING_UNCERTAINTY:`). The ledger
checks that `RESOLVES:` matches the linked gate and `RESOLVED_BY:` matches
`--resolved-by`.

If the gate target was already frozen, use `supersede-target --decision-id <id>`,
then retry the original gate with a fresh reviewer at the same iteration number.

Never rewrite a terminal classification because a later fix resolved it. The
target stays `NEEDS_DECISION` historically, with the `resolved_by` relationship
shown beside it.

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

Review the whole lifecycle, not only the first reproduction: the run that
inspired this skill passed every happy-path test and still shipped a public
transaction bypass.

## Review verdict rules

- Reject only with a concrete reproduction or a named missing proof, never for
  style, and never accept because the suite is green.
- Verify every reviewer claim locally before changing code.
- When the disagreement is about product intent, stop calling it a bug and ask
  for the decision.
