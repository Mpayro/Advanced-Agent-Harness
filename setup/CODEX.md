# Codex runtime

The current workflow skills in this bundle are Codex-only. They rely on Codex
subagents, task-path identities, the local approval model, and persistent goals
only when the user selects that mode.

## Install and verify

Install the current Codex CLI using OpenAI's supported installation method, log
in interactively, then verify:

```bash
codex --version
codex exec --skip-git-repo-check "reply with: OK" < /dev/null
```

Run the smoke command by itself. Standard input can otherwise consume the
prompt. Do not pipe a long review through `tail`; capture the complete output
when you need to inspect it.

## Reviewer roles

The skills describe roles instead of pinning versioned model slugs:

- a low-cost explorer for bounded discovery;
- Luna for substantial coding and every independent or adversarial review gate.

The active runtime and repository instructions decide which exact models are
available. Never route work to another provider merely because an old package
mentioned one.

## Required capabilities

- Git branches and linked worktrees for implementation flows.
- Persistent goal tools when the user explicitly selects goal mode; bounded
  workflows can run without them.
- Fresh Codex subagents for independent lanes and adversarial gates.
- Python 3 for validators and the Peer Bug Review ledger.
- Isolated Chrome with a temporary profile and remote debugging for UI proof.

If a capability is unavailable, report the corresponding proof as unavailable
or route to a smaller workflow. Do not fake independence or treat a missing UI
smoke as a passing test.

## Claude mirror

The installer keeps matching folders under `~/.claude/skills` because this
workspace requires skill mirrors to remain aligned. That mirror does not make a
Codex-only workflow executable in Claude. Runtime-specific provider boundaries
must be preserved explicitly.
