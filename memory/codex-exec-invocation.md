---
name: codex-exec-invocation
description: "How to launch codex exec, and the three liveness signals that lie"
metadata:
  type: feedback
---

A healthy `codex exec` review was killed at 14 minutes because the call was
invisible and every check used to confirm "it hung" was wrong.

**Why:** the command ended in `| tail -80`. A pipe holds all output until the
process exits, so an empty log proved nothing. Then three signals each reported
"dead" for a run that was working:

- `~/.codex/sessions/` — Codex stopped writing rollouts there in July 2026;
  state moved to `~/.codex/state_*.sqlite`. A healthy run leaves nothing there.
- `%CPU` from `ps` — a lifetime average. A run streaming a long reasoning turn
  sits near 0% while perfectly alive.
- `ps ... | grep -i codex` — the ChatGPT desktop app's helper processes match
  the same pattern and bury the real one.

**How to apply:**
- Redirect, never pipe: `> out.txt 2>&1`. Judge liveness by `wc -c` growth and
  by `pgrep -f 'codex exec'`.
- Pass the prompt over stdin (`< packet.md`), not `"$(cat packet.md)"` in argv.
- Always pin `-m` and `model_reasoning_effort`. Without both, the call silently
  inherits `~/.codex/config.toml`, usually the slowest and costliest setting.
- A high-reasoning review against a real repo runs for tens of minutes and
  prints nothing for long stretches. Do not kill it while its log grows.
- The canonical call and model slugs live in one place: the `coding-peers`
  Runner section ([[fable-architect-policy]]).
