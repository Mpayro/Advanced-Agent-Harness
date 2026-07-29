#!/usr/bin/env python3
"""PreToolUse guard on Agent/Task: never spawn Fable subagents.

Policy: **Fable 5 is the ARCHITECT, never the worker.**

Fable 5 sits at the top of the Claude ladder — the most capable model, and the
most expensive one. It is the right model to hold a whole problem in its head,
plan the work, and make the calls. It is the wrong model to run ten parallel
greps.

The trap: when you spawn a subagent WITHOUT naming a model, it inherits the
session model. If your session is Fable, every helper agent is Fable too. A
fan-out of ten scouts costs ten times what it should, and you find out on the
invoice rather than in the moment.

This is not hypothetical. Two real sessions produced it: one re-read ~400K of
context on every wake-up, another spawned 10 Fable subagents across 520 turns.
Same root cause both times — Fable-root inheritance, plus guardrails that
existed only as advice in a prompt. The written preference was ignored roughly
15:1. Hence: enforced in code.

Behavior:
- model fable / best  -> rewritten to sonnet
- model absent        -> rewritten to sonnet (blocks inheriting a Fable root)
- explicit sonnet/opus/haiku -> allowed through untouched

Every spawn is logged to ~/.claude/logs/fable_guard.log for visibility.

TUNING — edit BANNED below:
- As shipped it blocks Fable and leaves `opus` available, so you can still reach
  for Opus explicitly on genuinely hard synthesis where it earns its cost.
- The absent -> sonnet rewrite is the half that matters most, and it protects you
  no matter which model you run as your session default. Keep it either way.
- If you run something other than Fable as your expensive default, add its name
  to BANNED — but only if you never want to select it explicitly for a subagent.
"""
import datetime
import json
import os
import sys

# Substrings matched against the requested model name (lowercased).
# "best" is here because it resolves to the top-tier model — i.e. Fable.
BANNED = ("fable", "best")

try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)  # malformed input: never block the tool

ti = d.get("tool_input") or {}
model = (ti.get("model") or "").strip().lower()
banned = any(b in model for b in BANNED) if model else False
inherit = model == ""

log_path = os.path.expanduser("~/.claude/logs/fable_guard.log")
os.makedirs(os.path.dirname(log_path), exist_ok=True)
stamp = datetime.datetime.now().isoformat(timespec="seconds")
desc = ti.get("description", "")

if banned or inherit:
    shown = model or "inherit"
    with open(log_path, "a") as f:
        f.write(f"{stamp} REWROTE model='{shown}' -> sonnet desc='{desc}'\n")
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "permissionDecisionReason": f"fable_guard: model '{shown}' -> sonnet (Fable is the architect, not the worker)",
            "updatedInput": {**ti, "model": "sonnet"},
        }
    }))
else:
    with open(log_path, "a") as f:
        f.write(f"{stamp} ALLOWED model='{model}' desc='{desc}'\n")
sys.exit(0)
