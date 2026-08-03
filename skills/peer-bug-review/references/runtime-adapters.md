# Runtime adapters

## Agent routing

Detect the active harness from the runtime, never from the skill path.

The sweep and the per-candidate gates run at the bulk-sweep tier of the
`coding-peers` table — freshness and blind inputs provide independence, not a
bigger model. This is the one place that tier is correct; it does not licence
routing general work there.

The final assembled-product adversary of beat 4 runs at the adversarial tier,
like every other gate in the family.

## Local batch runner

If the thread subagent tool does not expose the bulk-sweep model, use the
validated local runner. Flags, model slugs, and the liveness rules come from the
`coding-peers` "Invoking Codex" section — read it before dispatching. This adds
only the batch-schema wrapper:

```bash
codex exec \
  --ignore-user-config \
  -m <bulk-sweep slug from coding-peers> \
  -c 'model_reasoning_effort="medium"' \
  --ephemeral \
  -s read-only \
  --skip-git-repo-check \
  -C <repo> \
  --output-schema <skill>/references/review-output.schema.json \
  -o <batch-result.json> \
  < <batch-prompt.txt> > <runner-log.txt> 2>&1
python3 <skill>/scripts/render_review_batch.py \
  <batch-result.json> <evidence-directory>
```

`--ignore-user-config` avoids loading unrelated personal plugins/hooks while keeping
Codex authentication. Because those instructions are not inherited, embed the
applicable user/repo/model constraints and data boundaries in every frozen review
packet. Use this flag only for read-only reviewers. For an explicitly owned
`workspace-write` implementation task, omit it and accept the heavier startup.

Run them as one bounded wave, as wide as the stage genuinely divides, and collect
the wave once after the processes finish. Do not wake the coordinator with
30-second polling. Batch at most four unrelated targets per runner — the output
schema caps the batch at four, so a wider one is rejected, not truncated.

Start at medium reasoning effort and raise it for a hard gate — a security,
concurrency, money, or migration seam, or a concrete rejection you must answer.

## Codex rules

- Keep one coordinator responsible for classifications and final decisions.
- Make that coordinator the only writer of the state ledger. Subagents return
  evidence; they never mutate the ledger directly. The script intentionally uses
  atomic replacement without multi-writer locking.
- Reserve one concurrency slot for the coordinator.
- Run discovery agents in waves; use a fresh reviewer at every gate.
- Obey the actual thread cap and repository model restrictions.
- Record model substitutions and failed endpoints in the final skill-use audit.
- Do not leak finder conclusions into blind confirmation prompts.

When the user explicitly invokes a persistent full audit/repair and `create_goal` is
available, create one goal for the entire run. Do not create a goal per bug.

Keep the goal active while useful work remains. Mark complete only after the final
integration gate. Mark blocked only under the runtime’s blocked-status contract and
after the same true blocker repeats enough times.

Use the bulk-sweep tier for discovery and the confirmation/plan/fix gates, and
the adversarial tier for the final integration gate. Prefer the thread tool when
it exposes the tier; otherwise use the local runner above. Use the no-subagents
path only when both routes are unavailable or prohibited.

Size the wave to the concurrency the runtime actually allows, always reserving one
slot for the coordinator. Under a hard four-slot cap that means a coordinator, two
discovery explorers and one blind verifier, then rotating new waves. During repair,
replace explorers with one bounded implementer and one review batch when file
ownership does not overlap.

## No subagents available

Use this only when neither native subagents nor the local runner is available.
Do not fake independence. Run sequential no-context self-reviews from raw artifacts,
label the limitation, and do not claim independent adversarial confirmation.

## External peers

Apply the active data-boundary/redaction skill before sending anything externally.
Retry an empty/transport failure once, then fall back locally. Never stall the audit
on a flaky peer endpoint.
