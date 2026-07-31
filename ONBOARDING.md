# ONBOARDING — installer instructions

This file is for the agent installing the harness. The user should not need to
manually copy files.

## Contract

- Inspect before asking.
- Install user-level skills under `~/.codex/skills`, not only in a repo.
- Keep the matching `~/.claude/skills` copies aligned.
- Back up every existing target before replacing it.
- Preserve unrelated configuration and hooks.
- Verify each installed skill with real commands.
- Do not install optional external-model access unless the user asks for it.

## 1. Discover read-only state

Inspect:

```bash
ls ~/.codex/skills 2>/dev/null
ls ~/.claude/skills 2>/dev/null
codex --version
git --version
python3 --version
```

Read the user's global and repo `AGENTS.md`/`CLAUDE.md` files, existing skill
copies, and any configured model/provider restrictions. Check whether the
runtime exposes goals, subagents, and isolated browser control.

Report the exact collisions and missing capabilities. Ask only about a choice
that cannot be determined safely.

## 2. Select the skills

Install these by default:

- `end-to-end-coding-session`
- `coding-peers`
- `peer-bug-review`
- `delegating-to-external-models`
- `ponytail`
- `ponytail-review`

Install `end-to-end-coding-session-automatic` unless the user explicitly does
not want an auto-commit option. Its presence does not enable it; the workflow
still requires explicit invocation and consent.

## 3. Back up collisions

For every selected `<name>`, inspect both targets:

```text
~/.codex/skills/<name>
~/.claude/skills/<name>
```

If either exists, copy it to a sibling backup named
`<name>.bak-harness-YYYYMMDD-HHMMSS` before replacement. Never replace a
repo-owned or centrally managed skill without explicit authority.

## 4. Install Codex first

Copy each complete selected folder from `skills/` to:

```text
~/.codex/skills/<name>
```

Copy the whole folder, not only `SKILL.md`. `peer-bug-review` requires its
references, template, and scripts. The end-to-end validator requires the
`agents/openai.yaml` metadata for all three workflow skills.

Do not copy `.DS_Store`, `__pycache__`, temporary state, or evaluation outputs.

## 5. Align the Claude mirror

Mirror the same selected folders under:

```text
~/.claude/skills/<name>
```

The current end-to-end and Peer Bug Review workflows are Codex-only; this
mirror is maintained for version consistency and future runtime adapters. Do
not rewrite provider names blindly. If a runtime-specific variant already
exists, preserve its intentional boundary wording and verify the differences
explicitly.

The optional files in `hooks/` and `memory/` are Claude-side extras. Install
them only if the user explicitly wants the Fable guard or always-on Ponytail
posture. Merge settings; never replace existing hook arrays or memory indexes.

## 6. Validate

Run Codex's skill validator against every installed folder:

```bash
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py ~/.codex/skills/<name>
```

If the default interpreter cannot import `yaml`, use the existing Homebrew
site-packages path instead of changing the user's Python environment:

```bash
PYTHONPATH=/opt/homebrew/lib/python3.11/site-packages python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py ~/.codex/skills/<name>
```

Then run:

```bash
python3 ~/.codex/skills/end-to-end-coding-session/scripts/validate_workflow_suite.py
python3 ~/.codex/skills/peer-bug-review/scripts/review_state.py self-test
python3 ~/.codex/skills/peer-bug-review/scripts/eval_peer_bug_review.py self-test
```

Verify SHA-256 equality for every intended Codex/Claude mirror. Provider-specific
variants must be listed as intentional exceptions instead of silently accepted.

## 7. Handoff

Report:

- exact installed and skipped skills;
- backup paths;
- validation commands and outputs;
- Codex/Claude mirror status;
- unavailable continuation (goal/loop), subagent, browser, or Git capabilities;
- optional hooks/external peers left untouched.

Offer one small, low-risk first run. Do not open a persistent continuation handle
or mutate a real repo merely as an installation smoke test.
