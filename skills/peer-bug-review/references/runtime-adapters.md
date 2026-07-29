# Runtime adapters

## Cheap-agent routing

- Detect the active harness from the runtime, never from the skill path.
- In Claude or Claude Code, run every spawned explorer, verifier, reviewer,
  implementer, and integration adversary with a permitted Sonnet model.
- In Codex, run every spawned agent in those roles with permitted GPT-5.6 Luna.
- Keep the selected cheap model at every gate; freshness and blind inputs provide
  independence, not a more expensive model.
- Never substitute Opus in Claude or Terra/Sol in Codex.

## Codex local Luna runner

If the thread subagent tool does not expose Luna, use the validated local runner:

```bash
codex exec \
  --ignore-user-config \
  -m gpt-5.6-luna \
  -c 'model_reasoning_effort="medium"' \
  --ephemeral \
  -s read-only \
  -C <repo> \
  --output-schema <skill>/references/review-output.schema.json \
  -o <batch-result.json> \
  < <batch-prompt.txt>
python3 <skill>/scripts/render_review_batch.py \
  <batch-result.json> <evidence-directory>
```

`--ignore-user-config` avoids loading unrelated personal plugins/hooks while keeping
Codex authentication. Because those instructions are not inherited, embed the
applicable user/repo/model constraints and data boundaries in every frozen review
packet. Use this flag only for read-only reviewers. For an explicitly owned
`workspace-write` implementation task, omit it and accept the heavier startup.

Start at most three local runners in one bounded wave and collect them once after
process completion. Do not wake the coordinator with 30-second polling. Batch at
most four unrelated targets at the same stage per runner.

Use medium reasoning by default. Escalate effort, not model, only after a concrete
rejection or for a critical security/concurrency/money gate.

## Codex rules

- Keep one coordinator responsible for classifications and final decisions.
- Make that coordinator the only writer of the state ledger. Subagents return
  evidence; they never mutate the ledger directly. The script intentionally uses
  atomic replacement without multi-writer locking.
- Reserve one concurrency slot for the coordinator.
- Run cheap discovery agents in waves; use fresh cheap reviewers at gates.
- Obey the actual thread cap and repository model restrictions.
- Record model substitutions and failed endpoints in the final skill-use audit.
- Do not leak finder conclusions into blind confirmation prompts.

When the user explicitly invokes a persistent full audit/repair and `create_goal` is
available, create one goal for the entire run. Do not create a goal per bug.

Keep the goal active while useful work remains. Mark complete only after the final
integration gate. Mark blocked only under the runtime’s blocked-status contract and
after the same true blocker repeats enough times.

Use GPT-5.6 Luna for discovery and every confirmation/plan/fix/integration gate.
Prefer the thread tool when it exposes Luna; otherwise use the local runner above.
Use the no-subagents path only when both routes are unavailable or prohibited.

With a four-slot cap, use:

- coordinator;
- two discovery explorers;
- one blind verifier;

then rotate new waves. During repair, replace explorers with one bounded implementer
and one review batch when file ownership does not overlap.

## No subagents available

Use this only when neither native Sonnet/Luna nor the local Luna runner is available.
Do not fake independence. Run sequential no-context self-reviews from raw artifacts,
label the limitation, and do not claim independent adversarial confirmation.

## External peers

Apply the active data-boundary/redaction skill before sending anything externally.
Retry an empty/transport failure once, then fall back locally. Never stall the audit
on a flaky peer endpoint.
