#!/usr/bin/env bash
# SessionStart hook: make the coding posture active by default in every session.
# Injects posture_session_context.md as additionalContext (Claude Code format).
#
# Requires `jq` (brew install jq).
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
jq -n --rawfile ctx "$DIR/posture_session_context.md" \
  '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $ctx}}'
