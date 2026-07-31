---
name: fable-architect-policy
description: "Fable 5 is architect not worker — delegation map, 750K auto-compact, Monitor over polling"
metadata:
  type: feedback
---

**Fable 5 is the ARCHITECT, never the worker.**

**Why:** Fable is the most expensive model in the Claude ladder. The priciest
model, times a huge context window, times one wake-up per subagent result, is
the worst-case cost multiplier that exists. Two real sessions proved it: one
re-read ~400K of context on every wake-up, another spawned 10 Fable subagents
across 520 turns. Both root causes were the same — subagents *inheriting* the
Fable root, plus guardrails that only existed as advice in text.

**How to apply:**
- Never spawn Fable subagents — enforced by the `fable_guard` hook
  ([[subagent-model-policy]]). Subagent models: `sonnet` by default, `opus`
  only for genuinely hard synthesis, `haiku` for trivial mechanical work.
- External delegation: heavy coding → Codex **Terra** (latest tier);
  adversarial/independent review → Codex **Sol** (latest flagship). Never pin
  model versions — the current slugs live ONLY in the `coding-peers` skill.
  Everywhere else says "Codex Sol/Terra (see coding-peers)". Claude subagents
  use the aliases `sonnet`/`opus`, never full model IDs.
- Which peer does what depends on the harness you are in, not on the task.
  Sonnet and Luna are the same tier: bulk bug-review labor goes to Sonnet in
  Claude and to Luna in Codex. Heavy implementation goes to Terra in Codex; in
  Claude, Sonnet writes it and Opus reviews it. The adversarial gate goes to
  Sol; running in Claude, **ask at the start of the run** — Sol or an
  adversarial Opus subagent — alongside the other opening questions, and reuse
  that answer at every gate of that run. Never halt mid-run to ask who reviews;
  the answer does not cross runs. No Codex installed, no question: Opus. The
  table lives in the `coding-peers` peer table, where the slugs name a tier, not a version.
- `autoCompactWindow: 750000` in settings.json is the "don't crash on a long
  session" setting. It is deliberately expensive; a lower value (~450000) costs
  less and compacts more often. Pick knowingly.
- Launching Codex: canonical call and liveness rules in
  [[codex-exec-invocation]]. Never pipe its output.
- Babysit external/background work with a lean Sonnet subagent or the Monitor
  tool — never wake the fat Fable root per result. Batch delegations, collect
  once. Prefer Monitor over `/loop` polling; keep any fixed poll under 5 minutes
  (prompt-cache TTL) or every check pays the full context re-read.
- Memory/observation checks: session start, plus when a task cites past work.
  Not every turn.

Canonical text lives in `~/.claude/hooks/posture_session_context.md` and the
`ponytail` skill — single source of truth, deliberately NOT copied into every
skill ([[ponytail-default]]).
