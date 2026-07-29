---
name: ponytail-default
description: "The ponytail posture is auto-active every session via a SessionStart hook; superpowers' auto-injection is turned off (skills still available on demand)"
metadata:
  type: feedback
---

The `ponytail` skill (laziest-solution-that-actually-works discipline) is
active by default in **every** session, without being asked for. The
`superpowers` plugin's every-session auto-injection is turned **off** — its
skills stay available on demand, they just don't get force-injected into
every conversation.

**ponytail always-on** — a global `SessionStart` hook in
`~/.claude/settings.json` (matcher `startup|clear|compact`) runs
`~/.claude/hooks/posture_session_start.sh`, which emits
`hookSpecificOutput.additionalContext` read from
`~/.claude/hooks/posture_session_context.md`. Off-switch for any single
session: say "stop ponytail" or "normal mode".

**superpowers auto-injection disabled** — the plugin ships its own
`SessionStart` hook at
`~/.claude/plugins/cache/claude-plugins-official/superpowers/<version>/hooks/hooks.json`
that injects the full `using-superpowers` skill wrapped in
`<EXTREMELY_IMPORTANT>` on every session. Setting that file to `{"hooks":{}}`
neutralizes it (keep the original alongside as `hooks.json.bak`). The plugin
stays ENABLED, so all `superpowers:*` skills remain usable via the Skill tool
and are still referenced by [[end-to-end-coding-session]].

**Why:** ponytail is the preferred default coding posture; the superpowers
every-prompt preamble is unwanted weight on top of it.

**How to apply:** changes take effect from the NEXT session (`SessionStart`
only fires at session start; `/clear` retriggers it).

**CAVEAT:** if the superpowers plugin auto-updates to a new version directory,
its fresh `hooks.json` re-enables the injection — re-neutralize it in the new
version's folder.
