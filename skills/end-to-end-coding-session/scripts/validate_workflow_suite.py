#!/usr/bin/env python3
"""Validate the shared safety contract for the three coding workflow skills."""

from __future__ import annotations

import json
import re
from pathlib import Path


SKILLS_ROOT = Path(__file__).resolve().parents[2]
HOME = Path.home()
NAMES = (
    "end-to-end-coding-session",
    "end-to-end-coding-session-automatic",
    "coding-peers",
    "peer-bug-review",
)


def require(text: str, needle: str, label: str, errors: list[str]) -> None:
    if needle not in text:
        errors.append(f"{label}: missing {needle!r}")


def inherits_base_step_one(text: str) -> bool:
    return bool(
        re.search(
            r"\b(?:run|follow|apply|execute|inherit)\s+(?:the\s+)?base step 1\b",
            text,
            flags=re.IGNORECASE,
        )
    )

def flat(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()

def ordered_wrong(text: str, first: str, second: str) -> bool:
    """True when `second` precedes `first`, or either anchor is missing.

    Compares flattened text because the contract lists are checked against
    flat() too: a raw .find() returns -1 for any anchor that wraps across a
    line, and -1 > -1 is False, so the comparison would pass while asserting
    nothing. A missing anchor is reported as a violation rather than ignored,
    so a rename can never silently disarm the check.
    """
    flattened = flat(text)
    a, b = flattened.find(first), flattened.find(second)
    if a < 0 or b < 0:
        return True
    return a > b


def contract_errors(
    text: str, phrases: tuple[str, ...], label: str
) -> list[str]:
    normalized = flat(text)
    return [
        f"{label}: missing contract {phrase!r}"
        for phrase in phrases
        if phrase not in normalized
    ]


def remove_contract_phrase(text: str, phrase: str) -> str:
    pattern = re.escape(phrase).replace(r"\ ", r"\s+")
    return re.sub(pattern, "", text, count=1)


BASE_PHRASES = (
    "Human-gated is the default",
    "Read the continuation handle before",
    "`workflow_owner`, `living_plan`, `terminal_contract`, and",
    "do not overwrite, complete, or close it",
    "explicitly record the authorization to open",
    "`persistence_mode=persistent` opens the handle this harness has",
    "`persistence_mode=persistent` or",
    "`persistence_mode=none`",
    "Recommend `persistent`",
    "Recommend `none`",
    "Do not infer the choice",
    "skip every open/close call",
    "inventory index and worktree dirt separately",
    "exact task-owned patch bytes",
    "validate it with the harness's UI proof tool from `coding-peers` §3b before Step 7",
    "temporary profile and remote debugging",
    "do not mark the UI verified",
    "Only in `persistence_mode=persistent`, close the handle as complete",
    "three consecutive handle turns",
    "living execution plan",
    "`terminal_peer_review_state`",
    "`coding-peers`; no handle",
    "Touching production is scope, not a forbidden category",
    "Commit authority is not release authority; never infer one from the other",
    "The user authorized that exact action for this run, naming it",
    "It is reversible, or its irreversibility was disclosed and accepted",
    "Release steps, whenever the objective plausibly reaches production",
    "Ask before commit",
    "Do not commit, push, merge, deploy, promote, or migrate unless the user",
    "A plan that never mentions production does not acquire it later",
    "`end-to-end-coding-session-automatic`",
    "`peer-bug-review`",
)

AUTOMATIC_PHRASES = (
    "explicit-opt-in workflow",
    "does not invoke a nested base workflow",
    "replace its handle timing and stop-before-commit disclosure",
    "explicitly confirms",
    "persistence mode",
    "eligibility-before-handle",
    "without opening an Automatic handle",
    "`workflow_owner=end-to-end-coding-session-automatic`",
    "auto-commit authority",
    "generic \"implement it\" is insufficient",
    "Recommend `persistent`",
    "Recommend `none`",
    "Do not infer the choice",
    "open no handle and make no handle-state transitions",
    "Limit: ten plan-gate attempts",
    "| Plan approval | 10 fresh reviewers |",
    "immutable `approved_plan_target`",
    "APPROVED_PLAN: <sha256> <canonical-path>",
    "mechanically compare both `APPROVED_PLAN` digest",
    "atomically set it to `pending`",
    "after that gate accepts, set `completed`",
    "sole staging input",
    "cached diff digest equals the accepted code-gate patch",
    "require the base Step 6 Computer Use smoke",
    "temporary profile and remote debugging",
    "Do not advance to the code gate or auto-commit when required UI proof is missing",
    "Only in `persistence_mode=persistent`, close the handle as complete",
    "three consecutive handle turns",
    "Commit authority is not release authority",
    # A release the consent gate authorized must have a step that performs it.
    "The plan contains a production, destructive, or irreversible step the consent gate never named",
    "the plan does not carry that action's rollback and verification",
    "A release step the consent gate named is never reported as proposed",
    # Ordering-check anchors: asserted here so a rename cannot turn the
    # comparisons below into -1 > -1 and pass vacuously.
    "read the continuation handle before the first alignment",
    "open the handle. Record outcome",
    "After consent and before opening the handle",
    "If eligible and `persistence_mode=persistent`, open the handle",
)

PEER_PHRASES = (
    "Read-only is the default",
    "No persistent handle",
    "**Repair authorized:**",
    "Never infer Repair authority",
    "Do not recursively invoke",
    "Use one fresh adversarial reviewer by default",
    "Use two parallel reviewers only when their lanes are truly independent",
    "Require non-empty content on every label's same physical line",
    "always save and SHA-256 hash the exact patch bytes",
    "review manifest containing that patch path/digest",
    "canonical review manifest",
    "canonical review manifest is the one target identity for dispatch and response",
    "validate it with the harness's UI proof tool from §3b before the verdict",
    "temporary profile and remote debugging",
    "do not accept the UI claim as verified",
    "Under Review-only authority",
    "Under Repair authority",
)

PEER_BUG_PHRASES = (
    # Honesty about what a bug hunt can promise.
    "Promise evidence discipline, not mathematical absence of bugs",
    "all enumerated surfaces were covered and all candidates were classified",
    "Never convert exhaustion into acceptance",
    # Model routing stays in one place.
    "Slugs live only in `coding-peers` §3b; never pin a version here",
    "Detect the harness from the runtime, not the skill path",
    # Authority.
    "a review request alone is not edit authorization",
    "Explorers report `CANDIDATE`, never `BUG`, and never edit",
    # Coverage cannot be improvised or back-filled.
    "Never start with random file sampling",
    "Candidates may only be added after that freeze",
    "Reserve one concurrency slot for the coordinator",
    # Blind confirmation.
    "Do not provide the finder\u2019s conclusion or intended fix",
    "Only `CONFIRMED_BUG` advances to planning",
    "Tests and old docs are evidence, not automatic product truth",
    "the ledger rejects logical-identity, response-evidence, or frozen-target reuse",
    "Never normalize an agent verdict manually",
    "the post-fix review remains mandatory",
    # Repair discipline.
    "Reproduce RED on the baseline",
    "Verify every reviewer claim locally before changing code",
    "Serialize bugs that share files, state, schema, or business invariants",
    "It is diagnostic evidence, not an approval authority",
    "Do not restart the whole workflow when one stage fails",
    "Do not expose the oracle to audit agents",
)

PEER_RESPONSE_LABELS = (
    "TARGET_ARTIFACT:",
    "VERDICT:",
    "FINDINGS:",
    "TESTS:",
    "COUNTEREVIDENCE:",
)

METADATA_FIELDS = ("display_name", "short_description", "default_prompt")


def metadata_contract_errors(text: str, owner: str) -> list[str]:
    errors: list[str] = []
    lines = text.splitlines()
    if not lines or lines[0] != "interface:":
        return [f"{owner}: metadata must start with 'interface:'"]
    values: dict[str, str] = {}
    for line_number, line in enumerate(lines[1:], 2):
        if not line.strip():
            continue
        match = re.fullmatch(r"  ([a-z_]+): (.+)", line)
        if not match:
            errors.append(f"{owner}: malformed metadata line {line_number}")
            continue
        key, raw_value = match.groups()
        try:
            value = json.loads(raw_value)
        except (json.JSONDecodeError, TypeError):
            errors.append(f"{owner}: invalid quoted metadata value for {key}")
            continue
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{owner}: metadata {key} must be a non-empty string")
            continue
        values[key] = value
    for field in METADATA_FIELDS:
        if field not in values:
            errors.append(f"{owner}: metadata missing {field}")
    prompt = values.get("default_prompt", "")
    if prompt and f"${owner}" not in prompt:
        errors.append(f"{owner}: default_prompt must reference ${owner}")
    return errors


def peer_response_errors(text: str) -> list[str]:
    return [
        f"coding-peers response: {label} needs same-line content"
        for label in PEER_RESPONSE_LABELS
        if not re.search(
            rf"(?m)^{re.escape(label)}[ \t]+\S",
            text,
        )
    ]


def mutation_control(
    text: str,
    phrase: str,
    phrases: tuple[str, ...],
    label: str,
    errors: list[str],
) -> None:
    mutated = remove_contract_phrase(text, phrase)
    if mutated == text or not contract_errors(mutated, phrases, label):
        errors.append(f"validator: mutation control failed for {label} {phrase!r}")


def main() -> int:
    errors: list[str] = []
    texts: dict[str, str] = {}
    if not all(
        inherits_base_step_one(sample)
        for sample in (
            "Run base Step 1",
            "Follow the base Step 1",
            "Apply base step 1 unchanged",
        )
    ) or inherits_base_step_one(
        "Use base Step 1 only for evidence gathering"
    ):
        errors.append("validator: base Step-1 inheritance controls failed")

    for name in NAMES:
        skill_path = SKILLS_ROOT / name / "SKILL.md"
        metadata_path = SKILLS_ROOT / name / "agents" / "openai.yaml"
        if not skill_path.is_file():
            errors.append(f"{name}: missing SKILL.md")
            continue
        if not metadata_path.is_file():
            errors.append(f"{name}: missing agents/openai.yaml")
        else:
            metadata_text = metadata_path.read_text(encoding="utf-8")
            errors.extend(metadata_contract_errors(metadata_text, name))
        text = skill_path.read_text(encoding="utf-8")
        texts[name] = text
        if not text.startswith("---\n"):
            errors.append(f"{name}: invalid frontmatter start")
        # Naming a model tier is fine — these skills are shared and have to say
        # who does the work. Pinning a *version* is not: it rots the moment the
        # model is superseded. The one peer table in coding-peers carries the
        # example slugs and the "use the newest of that tier" rule; every other
        # skill names tiers only.
        if name != "coding-peers":
            for pattern in (
                r"\bgpt-\d",
                r"\bclaude-(?:opus|sonnet|haiku|fable)-\d",
            ):
                if re.search(pattern, text, flags=re.IGNORECASE):
                    errors.append(f"{name}: pinned model version {pattern}")
        mirror = HOME / ".claude" / "skills" / name / "SKILL.md"
        if not mirror.is_file():
            errors.append(f"{name}: missing required mirror")
        elif mirror.read_text(encoding="utf-8") != text:
            errors.append(f"{name}: mirror is stale")

    base = texts.get("end-to-end-coding-session", "")
    automatic = texts.get("end-to-end-coding-session-automatic", "")
    peers = texts.get("coding-peers", "")

    errors.extend(contract_errors(base, BASE_PHRASES, "base"))
    if ordered_wrong(
        base,
        "Read the continuation handle before",
        "explicitly record the authorization to open",
    ):
        errors.append("base: the handle is opened before it is read")

    errors.extend(contract_errors(automatic, AUTOMATIC_PHRASES, "automatic"))
    if ordered_wrong(
        automatic,
        "read the continuation handle before the first alignment",
        "open the handle. Record outcome",
    ):
        errors.append("automatic: the handle is opened before it is read")
    if ordered_wrong(
        automatic,
        "After consent and before opening the handle",
        "If eligible and `persistence_mode=persistent`, open the handle",
    ):
        errors.append("automatic: eligibility must precede opening the handle")
    if inherits_base_step_one(automatic):
        errors.append("automatic: inherits contradictory base Step-1 disclosure")

    errors.extend(contract_errors(peers, PEER_PHRASES, "coding-peers"))
    errors.extend(
        contract_errors(
            texts.get("peer-bug-review", ""), PEER_BUG_PHRASES, "peer-bug-review"
        )
    )
    errors.extend(peer_response_errors(peers))

    for phrase in (
        "do not overwrite, complete, or close it",
        "inventory index and worktree dirt separately",
        "A plan that never mentions production does not acquire it later",
        "Commit authority is not release authority; never infer one from the other",
        "Release steps, whenever the objective plausibly reaches production",
        "validate it with the harness's UI proof tool from `coding-peers` §3b before Step 7",
    ):
        mutation_control(base, phrase, BASE_PHRASES, "base", errors)
    for phrase in (
        "eligibility-before-handle",
        "open no handle and make no handle-state transitions",
        "Limit: ten plan-gate attempts",
        "immutable `approved_plan_target`",
        "atomically set it to `pending`",
        "after that gate accepts, set `completed`",
        "sole staging input",
        "Do not advance to the code gate or auto-commit when required UI proof is missing",
        "A release step the consent gate named is never reported as proposed",
    ):
        mutation_control(
            automatic, phrase, AUTOMATIC_PHRASES, "automatic", errors
        )
    for phrase in (
        "Use one fresh adversarial reviewer by default",
        "Use two parallel reviewers only when their lanes are truly independent",
        "Require non-empty content on every label's same physical line",
        "review manifest containing that patch path/digest",
        "canonical review manifest is the one target identity for dispatch and response",
        "validate it with the harness's UI proof tool from §3b before the verdict",
    ):
        mutation_control(peers, phrase, PEER_PHRASES, "coding-peers", errors)
    for phrase in (
        "Never convert exhaustion into acceptance",
        "a review request alone is not edit authorization",
        "Candidates may only be added after that freeze",
        "Verify every reviewer claim locally before changing code",
    ):
        mutation_control(
            texts.get("peer-bug-review", ""),
            phrase,
            PEER_BUG_PHRASES,
            "peer-bug-review",
            errors,
        )
    split_response = peers.replace(
        "FINDINGS: concise same-line summary or none",
        "FINDINGS:\nconcise summary or none",
        1,
    )
    if split_response == peers or not peer_response_errors(split_response):
        errors.append("validator: split response-line self-control failed")

    # Ordering self-control. A contract list cannot prove an ordering check
    # bites, so prove it here: an inversion must be caught, a wrapped anchor
    # must be caught, and the correct order must pass.
    if (
        ordered_wrong("... beta ... alpha ...", "alpha", "beta")
        and ordered_wrong("... alpha ... missing", "alpha", "beta")
        and not ordered_wrong("... alpha ...\n... beta ...", "alpha", "beta")
    ):
        pass
    else:
        errors.append("validator: ordering self-control failed")

    # Every path and section the skills tell an agent to read must exist. The
    # suite reads only SKILL.md, so a deleted reference or a renamed heading is
    # otherwise invisible.
    if "## 3b." not in peers:
        errors.append("coding-peers: §3b heading missing; three skills point at it")
    for relative in (
        "peer-bug-review/references/evidence-contract.md",
        "peer-bug-review/references/detection-and-evaluation.md",
        "peer-bug-review/references/repo-overview.md",
        "peer-bug-review/references/runtime-adapters.md",
        "peer-bug-review/references/review-output.schema.json",
        "peer-bug-review/assets/bug-spec-template.md",
        "peer-bug-review/scripts/review_state.py",
        "peer-bug-review/scripts/render_review_batch.py",
        "peer-bug-review/scripts/eval_peer_bug_review.py",
    ):
        if not (SKILLS_ROOT / relative).is_file():
            errors.append(f"missing referenced file: {relative}")

    valid_metadata = (
        'interface:\n'
        '  display_name: "Sample"\n'
        '  short_description: "Short"\n'
        '  default_prompt: "Use $sample now."\n'
    )
    if metadata_contract_errors(valid_metadata, "sample"):
        errors.append("validator: valid metadata self-control failed")
    for sample in (
        "",
        "interface:\n  display_name: \"Sample\"\n",
        "interface:\n  display_name: [\n",
        valid_metadata.replace("$sample", "$other"),
    ):
        if not metadata_contract_errors(sample, "sample"):
            errors.append("validator: invalid metadata self-control failed")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
