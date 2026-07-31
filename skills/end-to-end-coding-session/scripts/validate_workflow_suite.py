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
    # The shape itself.
    "Four beats, in order",
    "Plan, peered",
    "Adversarial review of the plan",
    "Implementation, peered",
    "Adversarial review of the result",
    "this skill never names a model",
    # Nothing is decided mid-run that could have been decided up front.
    "Settle three things in that same first exchange",
    "Which release steps, if any, the objective reaches",
    "Nothing later in the run can grant that authority",
    "It is the only record of continuity",
    # Findings are hypotheses; proof is real or absent, never substituted.
    "Verify every claim yourself before acting on it",
    "Every finding is a hypothesis",
    "say so rather than substituting a green unit suite",
    # The three authorities never collapse into one.
    "Three authorities, granted separately, never inferred from each other",
    "Approval of the code is not approval of the release",
    "A plan that never mentioned production does not acquire it later",
    "Touching production is scope, not a forbidden category",
    "it is reversible, or its irreversibility was disclosed before it was authorized",
    # Isolation, handoff, and honest reporting.
    "A dirty shared checkout is not isolation",
    "Ask before commit",
    "never calls a finished release proposed",
    "Do not commit, push, merge, deploy, promote, or migrate unless the user",
    "Repeat only the stage that failed",
)

AUTOMATIC_PHRASES = (
    "Same four beats",
    "What changes is who approves",
    "Human-gated remains the default for long work",
    # Consent is explicit, complete, and never inferred.
    "Consent, once, up front",
    "run automatically only if named right here",
    "A generic \"implement it\" is not this consent",
    "an autonomous run that stops at its own review gate to ask who reviews is not autonomous",
    # The mode refuses itself when it should.
    "When to refuse the mode",
    "a reviewer would have to invent intent to approve",
    # The plan gate tests both directions, because it is the first moment the
    # plan exists.
    "Reject the plan outright, in either direction",
    "the plan does not carry that action's rollback and verification",
    "a production, destructive, or irreversible step the consent never named",
    "an autonomous run may not take that authority from its own plan",
    # The commit is the accepted bytes and nothing else.
    "using the accepted patch as the sole staging input",
    "abort on any other staged bytes",
    "any mismatch goes back to the user",
    # Release authority is separate and consumable exactly once.
    "Commit authority is not release authority; never infer one from the other",
    "One pass, no retry",
    "Never push or merge as a side effect of committing",
    "never as a completed step",
)

PEER_PHRASES = (
    "A peer is a fresh reviewer with no memory of how the work was made",
    "The harness you are running in picks the column, never the task",
    "Slugs name a tier, not a version",
    "This table is the only place any skill names a model",
    "ask once at the start of the run which adversarial peer to use",
    # The artifact under review is the real one, provably.
    "Freeze the target before dispatch",
    "A summary explains intent and cannot replace the thing under review",
    "A malformed response is not a verdict",
    "counterevidence against itself",
    # Findings and proof.
    "Nothing, until you reproduce it",
    "Documentation is not runtime proof",
    "never let a green unit suite stand in for it",
    # Authority and data boundary.
    "Read-only is the default, and a request to review never grants an edit",
    "This skill dispatches none of them with write access",
    "A key on disk is a capability, never a standing consent",
    "it is a data boundary, not a formality",
    # The runner and its liveness rules.
    "Never pipe the output",
    "Prompt over stdin",
    "do not kill it while its output file grows",
)

PEER_BUG_PHRASES = (
    "The same four beats",
    "Find, peered",
    "Prove or kill, adversarially",
    "Fix, peered",
    "Review the assembled product",
    # What may be promised.
    "Evidence discipline, never the absence of bugs",
    "Never say the repo has no bugs",
    "Exhaustion is not acceptance",
    # Authority.
    "A review request is not edit authorization",
    # Coverage cannot be improvised or back-filled.
    "Record what is not observable as blocked",
    "they never quietly add one",
    "Never start from random file sampling",
    # Blind confirmation.
    "never the finder's conclusion or intended fix",
    "A verifier that knows the answer is not a second opinion",
    "Only confirmed advances",
    "Never normalize a verdict by hand",
    # Repair discipline.
    "reproduce the failure on the baseline",
    "Verify every reviewer claim yourself before touching code",
    "serialize anything sharing files, state, schema, or an invariant",
    "The script does not enforce that list \u2014 you do",
    "The post-fix review is never skipped",
    # Closing honestly.
    "Per-bug green is not product green",
    "it stops the run from claiming coverage",
    "Repeat only the stage that failed",
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
        "Which release steps, if any, the objective reaches",
        "Run them in the plan's order",
    ):
        errors.append("base: release runs before it is authorized")
    if ordered_wrong(
        base,
        "Ask for implementation approval",
        "Make the smallest change at the root cause",
    ):
        errors.append("base: implementation precedes its approval")

    errors.extend(contract_errors(automatic, AUTOMATIC_PHRASES, "automatic"))
    if ordered_wrong(
        automatic,
        "Consent, once, up front",
        "Reject the plan outright, in either direction",
    ):
        errors.append("automatic: the plan gate precedes consent")
    if ordered_wrong(
        automatic,
        "Commit only after that acceptance",
        "Run only after the commit exists",
    ):
        errors.append("automatic: release precedes the commit")
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
        "Approval of the code is not approval of the release",
        "A plan that never mentioned production does not acquire it later",
        "Three authorities, granted separately, never inferred from each other",
    ):
        mutation_control(base, phrase, BASE_PHRASES, "base", errors)
    for phrase in (
        "Reject the plan outright, in either direction",
        "Commit authority is not release authority; never infer one from the other",
        "Never push or merge as a side effect of committing",
    ):
        mutation_control(
            automatic, phrase, AUTOMATIC_PHRASES, "automatic", errors
        )
    for phrase in (
        "A peer is a fresh reviewer with no memory of how the work was made",
        "Read-only is the default, and a request to review never grants an edit",
        "A key on disk is a capability, never a standing consent",
        "Never pipe the output",
    ):
        mutation_control(peers, phrase, PEER_PHRASES, "coding-peers", errors)
    for phrase in (
        "Exhaustion is not acceptance",
        "A review request is not edit authorization",
        "Never start from random file sampling",
        "The post-fix review is never skipped",
    ):
        mutation_control(
            texts.get("peer-bug-review", ""),
            phrase,
            PEER_BUG_PHRASES,
            "peer-bug-review",
            errors,
        )
    split_response = peers.replace(
        "FINDINGS: same-line summary or none",
        "FINDINGS:\nsame-line summary or none",
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
    if "## Who reviews" not in peers:
        errors.append("coding-peers: the peer table heading is missing")
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
