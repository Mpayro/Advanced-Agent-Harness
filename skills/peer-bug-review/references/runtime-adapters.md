# Runtime adapters

## Codex rules

- Keep one coordinator responsible for classifications and final decisions.
- Make that coordinator the only writer of the state ledger. Subagents return
  evidence; they never mutate the ledger directly. The script intentionally uses
  atomic replacement without multi-writer locking.
- Reserve one concurrency slot for the coordinator.
- Run inexpensive discovery agents in waves; use fresh stronger reviewers at gates.
- Obey the actual thread cap and repository model restrictions.
- Record model substitutions and failed endpoints in the final skill-use audit.
- Do not leak finder conclusions into blind confirmation prompts.

When the user explicitly invokes a persistent full audit/repair and `create_goal` is
available, create one goal for the entire run. Do not create a goal per bug.

Keep the goal active while useful work remains. Mark complete only after the final
integration gate. Mark blocked only under the runtime’s blocked-status contract and
after the same true blocker repeats enough times.

Discovery preference:

1. permitted Luna explorer at low effort;
2. permitted Terra explorer at low effort;
3. nearest inexpensive explorer allowed by current instructions.

Use the strongest permitted fresh reviewer for confirmation/plan/fix gates. Never
spawn a prohibited model merely because this reference names a preference.

With a four-slot cap, use:

- coordinator;
- two discovery explorers;
- one blind verifier;

then rotate new waves. During repair, replace explorers with one bounded implementer
and one fresh reviewer when file ownership does not overlap.

## No subagents available

Do not fake independence. Run sequential no-context self-reviews from raw artifacts,
label the limitation, and do not claim independent adversarial confirmation.

## External peers

Apply the active data-boundary/redaction skill before sending anything externally.
Retry an empty/transport failure once, then fall back locally. Never stall the audit
on a flaky peer endpoint.
