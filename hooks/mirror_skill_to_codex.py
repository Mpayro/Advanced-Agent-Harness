#!/usr/bin/env python3
"""
mirror_skill_to_codex.py

Mirror a Claude skill (~/.claude/skills/<name>) into the Codex skills location
(~/.codex/skills/<name>), rewriting the "driver" name and Claude config paths so
the skill reads as if Codex were running it:

  * "Claude" / "Claude Code"   ->  "Codex"        (the acting agent / harness)
  * ".claude/" paths           ->  ".codex/"      (config-dir references)
  * "Anthropic"                ->  "OpenAI"        (the company behind the driver)
  * "claude.ai"                ->  "chatgpt.com"   (the app)
  * "claude.com"               ->  "openai.com"    (the company site)
  * model ids (claude-opus/sonnet/haiku/fable-*)  ->  "the appropriate Codex
                                                       model for the task"
                                                       (Codex picks per task)

Genuine tool / plugin identifiers are left ALONE on purpose, so nothing breaks:
  * tool names like   claude-mem
  * MCP names like    Claude_in_Chrome
  * plugin/source ids claude-plugins-official, claude-code

Managed gstack skills are not mirrored. gstack already generates Codex-facing
skills under ~/.agents/skills, and mirroring those aliases into ~/.codex/skills
would create a second copy of the same use case.

Usage
-----
  # As a Claude Code PostToolUse hook (reads the hook JSON on stdin):
  python3 mirror_skill_to_codex.py

  # Manually, for one or more skills (by name, by dir, or by any file inside):
  python3 mirror_skill_to_codex.py resume
  python3 mirror_skill_to_codex.py ~/.claude/skills/resume/SKILL.md

  # Mirror EVERY skill once (full backfill):
  python3 mirror_skill_to_codex.py --all

Update/complement semantics: files that exist in the Claude skill are
created/overwritten (transformed) in the Codex copy. Files that exist only in
the Codex copy are left untouched — the mirror never deletes Codex-only content.

If Codex can also see a same-name user skill at ~/.agents/skills/<name>, the hook
adds a disabled skills.config entry for that ~/.agents path in ~/.codex/config.toml.
That keeps the Codex copy canonical without deleting skills other tools may use.
"""

import os
import re
import sys
import json
import time
import shutil

HOME = os.path.expanduser("~")
SRC_ROOT = os.path.join(HOME, ".claude", "skills")
DST_ROOT = os.path.join(HOME, ".codex", "skills")
AGENTS_ROOT = os.path.join(HOME, ".agents", "skills")
CODEX_CONFIG = os.path.join(HOME, ".codex", "config.toml")
LOG = os.path.join(HOME, ".claude", "hooks", "mirror_skill.log")

# Files we copy byte-for-byte instead of transforming.
BINARY_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico", ".pdf", ".zip",
    ".gz", ".tar", ".woff", ".woff2", ".ttf", ".otf", ".eot", ".mp4", ".mov",
    ".mp3", ".wav", ".so", ".dylib", ".bin", ".pyc", ".class", ".jar",
}

# Code and data: copied verbatim, never renamed. The transform rewrites the word
# "claude" anywhere it appears, which inside source is not prose but an
# identifier or a string literal — it silently turned {"codex", "claude"} into
# {"codex", "codex"} in review_state.py and collapsed the runtime set.
VERBATIM_EXTS = {
    ".py", ".sh", ".bash", ".zsh", ".js", ".mjs", ".cjs", ".ts", ".tsx",
    ".json", ".sql", ".toml", ".lock",
}

# Directories we never mirror.
SKIP_DIRS = {".git", "__pycache__", "node_modules", ".DS_Store"}

# Cross-harness skills: mirrored byte-for-byte, never renamed.
#
# The driver rename assumes a skill describes ONE harness, so it can be made to
# read as if Codex wrote it. These four deliberately describe BOTH — they carry
# a per-harness peer table and per-harness routing rules. Renaming collapses the
# distinction they exist to draw: "| Role | In Claude | In Codex |" became
# "| Role | In Codex | In Codex |", and "In Claude or Claude Code" became
# "In Codex or Codex", leaving the Codex copy unable to pick a column.
#
# Marking the skill is the fix, not rewording it. Prose written to survive a
# rename has to avoid the word "Claude" entirely, which either loses the
# distinction or replaces it with a label ("native subagents") that is ambiguous
# in a harness that also has subagents.
NO_TRANSFORM_SKILLS = {
    "coding-peers",
    "end-to-end-coding-session",
    "end-to-end-coding-session-automatic",
    "peer-bug-review",
}


def log(msg):
    try:
        os.makedirs(os.path.dirname(LOG), exist_ok=True)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")
    except Exception:
        pass


# --- transformation ---------------------------------------------------------
# Specific rules run first (model ids, urls, brand), then the generic driver
# rename, so the specific tokens are consumed before the broad pass.

# Claude model ids -> let Codex choose the model per task (no hard-coded id).
# Tier-anchored so it never touches claude-mem / claude-code / claude-plugins-*.
_MODEL = re.compile(r"claude-(?:opus|sonnet|haiku|fable)(?:[\w.\-]*\w)?", re.IGNORECASE)
_MODEL_REPL = "the appropriate Codex model for the task"

# Brand URLs.
_URL_AI = re.compile(r"claude\.ai")    # the app  -> ChatGPT
_URL_COM = re.compile(r"claude\.com")  # the site -> OpenAI

# The company behind the driver (case-preserving).
_ANTHRO = re.compile(r"Anthropic|anthropic|ANTHROPIC")


def _anthro_repl(m):
    return {"Anthropic": "OpenAI", "anthropic": "openai", "ANTHROPIC": "OPENAI"}[m.group(0)]


# "Claude Code" (product/harness) as a whole phrase.
_PHRASE = re.compile(r"\bClaude Code\b")

# A ".claude" directory reference -> ".codex" (".claude-mem" preserved: it is "-").
_PATH = re.compile(r"\.claude(?=/|[\"'\s)\]]|$)")

# Standalone driver name "Claude" -> "Codex". Still preserves genuine
# tool/plugin identifiers, because it is skipped when the token is:
#   preceded by a word char, "/", "." or "-"
#   followed by a word char or "/"  (claude-mem, claude-code, Claude_in_Chrome)
_WORD = re.compile(r"(?<![\w/.\-])(?:Claude|claude|CLAUDE)(?![\w/])(?!\.\w)(?!-\w)")


def _word_repl(m):
    return {"CLAUDE": "CODEX", "claude": "codex"}.get(m.group(0), "Codex")


# Phrases kept VERBATIM in the Codex copy: statements where both "Claude" and
# "Codex" must coexist (e.g. "both Claude and Codex are fully trusted"). Without
# this, the driver rename collapses "Claude y Codex" -> "Codex y Codex".
_PROTECTED = ("Claude y Codex", "Claude and Codex", "Codex y Claude", "Codex and Claude")


def transform_text(s):
    held = []
    for i, phrase in enumerate(_PROTECTED):
        if phrase in s:
            token = "\x00PROT%d\x00" % i
            s = s.replace(phrase, token)
            held.append((token, phrase))
    s = _MODEL.sub(_MODEL_REPL, s)
    s = _URL_AI.sub("chatgpt.com", s)
    s = _URL_COM.sub("openai.com", s)
    s = _ANTHRO.sub(_anthro_repl, s)
    s = _PHRASE.sub("Codex", s)
    s = _PATH.sub(".codex", s)
    s = _WORD.sub(_word_repl, s)
    for token, phrase in held:
        s = s.replace(token, phrase)
    return s


# --- mirroring --------------------------------------------------------------
def mirror_file(src, dst, transform=True):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    ext = os.path.splitext(src)[1].lower()
    if not transform or ext in BINARY_EXTS or ext in VERBATIM_EXTS:
        shutil.copy2(src, dst)
        return
    try:
        with open(src, "r", encoding="utf-8") as f:
            content = f.read()
    except (UnicodeDecodeError, ValueError):
        shutil.copy2(src, dst)  # not text -> copy verbatim
        return
    with open(dst, "w", encoding="utf-8") as f:
        f.write(transform_text(content))
    # Preserve the executable bit (e.g. for scripts/*.sh).
    try:
        shutil.copymode(src, dst)
    except Exception:
        pass


def _toml_string(s):
    return json.dumps(s)


def disable_agents_duplicate_for_codex(name):
    duplicate = os.path.join(AGENTS_ROOT, name)
    if not os.path.isdir(duplicate):
        return

    # If both roots somehow resolve to the same directory, do nothing.
    try:
        if os.path.samefile(duplicate, os.path.join(DST_ROOT, name)):
            return
    except FileNotFoundError:
        pass

    path_line = "path = " + _toml_string(duplicate)
    try:
        with open(CODEX_CONFIG, "r", encoding="utf-8") as f:
            current = f.read()
    except FileNotFoundError:
        current = ""

    if path_line in current:
        return

    os.makedirs(os.path.dirname(CODEX_CONFIG), exist_ok=True)
    prefix = "" if not current or current.endswith("\n") else "\n"
    with open(CODEX_CONFIG, "a", encoding="utf-8") as f:
        f.write(prefix)
        f.write("\n# Auto-added by ~/.claude/hooks/mirror_skill_to_codex.py to avoid duplicate Codex skills.\n")
        f.write("[[skills.config]]\n")
        f.write(path_line + "\n")
        f.write("enabled = false\n")
    log("disabled duplicate agents skill for Codex: %s" % duplicate)


def is_managed_gstack_skill(name):
    if name == "gstack":
        return True
    skill_md = os.path.join(SRC_ROOT, name, "SKILL.md")
    if not os.path.exists(skill_md):
        return False
    gstack_root = os.path.realpath(os.path.join(SRC_ROOT, "gstack")) + os.sep
    try:
        return os.path.realpath(skill_md).startswith(gstack_root)
    except OSError:
        return False


def mirror_skill(name):
    if is_managed_gstack_skill(name):
        log("skipped managed gstack skill '%s'" % name)
        return False
    src = os.path.join(SRC_ROOT, name)
    if not os.path.isdir(src):
        return False
    dst = os.path.join(DST_ROOT, name)
    transform = name not in NO_TRANSFORM_SKILLS
    count = 0
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        rel = os.path.relpath(root, src)
        for fn in files:
            if fn == ".DS_Store":
                continue
            s = os.path.join(root, fn)
            d = os.path.join(dst, fn) if rel == "." else os.path.join(dst, rel, fn)
            mirror_file(s, d, transform=transform)
            count += 1
    disable_agents_duplicate_for_codex(name)
    log("mirrored '%s': %d files -> %s%s"
        % (name, count, dst, "" if transform else " (verbatim, cross-harness)"))
    return True


def skill_name_from_path(p):
    """Return the skill name if path p lives under the Claude skills dir, else None."""
    p = os.path.abspath(os.path.expanduser(p))
    root = os.path.abspath(SRC_ROOT) + os.sep
    if not p.startswith(root):
        return None
    name = p[len(root):].split(os.sep, 1)[0]
    if not name or name.startswith("."):  # skip .system and other hidden dirs
        return None
    return name


def handle_target(t):
    if os.path.isdir(os.path.join(SRC_ROOT, t)):
        return mirror_skill(t)
    name = skill_name_from_path(t)
    return mirror_skill(name) if name else False


def main():
    args = sys.argv[1:]

    if args:
        if args[0] == "--all":
            ok = 0
            for n in sorted(os.listdir(SRC_ROOT)):
                if not n.startswith(".") and os.path.isdir(os.path.join(SRC_ROOT, n)):
                    if mirror_skill(n):
                        ok += 1
            print("mirrored %d skills -> %s" % (ok, DST_ROOT))
            return
        for t in args:
            print(("ok    " if handle_target(t) else "skip  ") + t)
        return

    # Hook mode: the Claude Code hook payload arrives as JSON on stdin.
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    p = ((data.get("tool_input") or {}).get("file_path")
         or (data.get("tool_response") or {}).get("filePath"))
    if not p:
        return
    name = skill_name_from_path(p)
    if name:
        mirror_skill(name)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # never let a hook break the turn
        log("ERROR: " + repr(e))
