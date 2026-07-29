---
name: subagent-model-policy
description: "Sonnet is the default subagent model — ENFORCED by the fable_guard hook, because the written preference alone was ignored ~15:1"
metadata:
  type: feedback
---

Subagents default to Sonnet. This started as a written preference and **stopped
being one** after measurement: the preference was ignored roughly 15:1 —
billions of cache-read tokens on Fable versus a fraction of that on Sonnet.

**Why:** advice in a prompt does not survive a busy agent under load. Cost
control in multi-agent workflows needs enforcement, not intention. Fable and
Opus are reserved for work whose difficulty actually justifies them.

**How to apply:** a `PreToolUse` hook (`~/.claude/hooks/fable_guard.py`, wired
in `settings.json` with matcher `Agent|Task`) rewrites `fable` / `best` /
**absent** model to `sonnet` and logs every spawn to
`~/.claude/logs/fable_guard.log`. Explicit `opus`/`haiku` pass through
untouched. The absent case matters most: an unnamed model silently inherits the
Fable root.

**The gap to remember:** Workflow `agent()` calls do NOT go through this hook.
There you still have to pass `model: 'sonnet'` by hand. See
[[fable-architect-policy]].
