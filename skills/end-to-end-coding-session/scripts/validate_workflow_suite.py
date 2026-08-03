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


# These lists assert BEHAVIOUR that would be a defect to lose, not wording.
# A phrase earns its place only if deleting it changes what an agent does. The
# suite deliberately does not freeze prose: a rewrite should be free to say the
# same thing better, and a list long enough to forbid that just blesses the next
# rewrite once someone updates it.

BASE_PHRASES = (
    # The shape itself.
    "Four beats, in order",
    "this skill never names a model",
    # Release authority is granted before the run, or never.
    "Which release steps, if any, the objective reaches",
    "Nothing later in the run can grant that authority",
    # Findings are hypotheses; proof is real or absent, never substituted.
    "Verify every claim yourself before acting on it",
    "Every finding is a hypothesis",
    "failure before you change the behaviour",
    # The three authorities never collapse into one.
    "Three authorities, granted separately, never inferred from each other",
    "Approval of the code is not approval of the release",
    "A plan that never mentioned production does not acquire it later",
    "it is reversible, or its irreversibility was disclosed before it was authorized",
    # Isolation.
    "A dirty shared checkout is not isolation",
    # The browser check vanished once in a rewrite; it is asserted now.
    "Last check \u2014 the product, in a browser",
    "A product with a UI is not verified until someone drove it",
    "Never the user's own profile",
    "That is a stated outcome, not a silent skip",
    # The handoff must correct a false impression of completeness.
    "The user reads a finished report as a finished feature",
    "Never end a handoff whose only shape is what went well",
    # Work not persisted is work a killed turn takes with it. The automatic
    # variant's landing gate is built on this rule by name — it verifies a
    # recorded sha precisely because the work is already committed in
    # checkpoints. Delete the rule here and keep that gate, and the gate asserts
    # nothing; nothing else in the suite noticed that hole.
    "no slice is left only in the tree once it lands",
    "Never commit to the user's branch to satisfy this",
    # Commit and release are asked for, never assumed.
    "Ask before commit",
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
    # The mode refuses itself when it should.
    "When to refuse the mode",
    "a reviewer would have to invent intent to approve",
    # The plan gate tests both directions, because it is the first moment the
    # plan exists.
    "Reject the plan outright, in either direction",
    "the plan does not carry that action's rollback and verification",
    "a production, destructive, or irreversible step the consent never named",
    "an autonomous run may not take that authority from its own plan",
    # The landed sha contains the accepted bytes, by construction.
    # The gate reads a recorded sha, because checkpoint commits mean the staging
    # area is empty by the time the reviewer accepts and the tip keeps moving.
    # Only the invariant and the recorded-sha rule are frozen; the mechanism
    # around them stays free to be rewritten.
    "Commit the frozen bytes first, then record that commit's sha",
    "What lands is that recorded sha",
    "Re-review re-records",
    "Nothing lands that the reviewer did not accept",
    "blocks the landing and every release step after it",
    "any mismatch goes back to the user",
    # Release authority is separate and consumable exactly once.
    "Commit authority is not release authority; never infer one from the other",
    "One pass, no retry",
    "Never push or merge as a side effect of committing",
    "never as a completed step",
    # Automatic-only: unwatched runs may not commit unverified UI.
    "The base skill's last check is not optional here",
    "an autonomous run may not ship a UI change that nobody drove",
    "Nobody is watching this run, which is the reason to follow them",
)

PEER_PHRASES = (
    "A peer is a fresh reviewer with no memory of how the work was made",
    "The harness you are running in picks the column, never the task",
    "Slugs name a tier, not a version",
    "This table is the only place any skill names a model",
    # The default is taken, not asked for; a standing instruction still wins.
    "A standing instruction outranks this table",
    # The artifact under review is the real one, provably.
    "Freeze the target before dispatch",
    "A summary explains intent and cannot replace the thing under review",
    "A malformed response is not a verdict",
    # The unavailable-and-carry-on escape is forbidden inside a ledger gate.
    "there is no unavailable outcome",
    "counterevidence against itself",
    # Findings and proof.
    "Nothing, until you reproduce it",
    "Documentation is not runtime proof",
    "the verdict waits on the browser",
    "rather than letting a green unit suite stand in for it",
    # Authority and data boundary.
    "Read-only is the default, and a request to review never grants an edit",
    "This skill dispatches none of them with write access",
    "A key on disk is a capability, never a standing consent",
    "it is a data boundary, not a formality",
    # The runner and its liveness rules. This is the operational knowledge the
    # whole suite cannot re-derive; it cost a 14-minute false hang to learn.
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
    "The script does not enforce the excluded list \u2014 you do",
    "The post-fix review is never skipped",
    # One state authority per run, named out loud, and the ledger is the default
    # where the harness has no orchestrator of its own.
    "Pick one state authority per run and say which",
    "the exception is a run holding a single candidate",
    # Work that is not persisted is work a killed turn takes with it.
    "Nothing is left only in the tree",
    # Every mode needs a place to persist. In-place repair has no branch, and
    # the run that discovers that mid-flight is the one that commits to the
    # user's branch to satisfy the rule above.
    "Where a repair runs in place because the repo requires it",
    "Not summarised, committed",
    # Bound persistence, never start order — the earlier wording serialized the
    # parallel lanes beats 1 and 2 depend on.
    "lanes still run in parallel",
    # A compressed list in SKILL.md must name the reference it compresses, at
    # the point of use. Every one of these three once stated a full-looking
    # checklist with no local pointer, and each dropped a step that changed what
    # an agent did: the preflight lost persisted-state inspection, the inventory
    # lost auth/secrets/money/destructive operations, the waiver lost its
    # recorded artifact and its high-risk exclusion.
    "Run the preflight in `references/detection-and-evaluation.md`",
    "enumerate the surface against the inventory in `references/repo-overview.md`",
    "the full waiver in `references/evidence-contract.md`",
    # Closing honestly.
    "Per-bug green is not product green",
    "Surfaces nobody looked at",
    "is a lie told by omission",
    "it stops the run from claiming coverage",
    "Repeat only the stage that failed",
)

# The reviewer is not asked to echo the frozen digest back: the renderer stamps
# it from the frozen target, and every observed instance of the echo failing was
# a model forgetting to copy a hash, never a peer reading the wrong artifact.
PEER_RESPONSE_LABELS = (
    "VERDICT:",
    "FINDINGS:",
    "TESTS:",
    "COUNTEREVIDENCE:",
    "OMISSIONS:",
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


def unreachable(skill_text: str, bodies: dict[str, str]) -> list[str]:
    """Names in `bodies` that `skill_text` cannot reach in one hop.

    Reachable means: named in SKILL.md, or named in a file SKILL.md names. Pure,
    so the self-control below can prove it bites without touching the disk.
    """
    def names(filename: str, text: str) -> bool:
        # Plain substring matching would make `contract.md` reachable through
        # `evidence-contract.md` — exactly the orphan this exists to catch. The
        # boundary excludes word characters, dots and dashes but *not* `/`,
        # because every real mention is written as `references/<name>`.
        # Bounded on both sides: the left boundary keeps `contract.md` from
        # matching inside `evidence-contract.md`, the right keeps `plan.md` from
        # matching inside `plan.md.bak`. Neither excludes `/`, because every real
        # mention is written `references/<name>`.
        return (
            re.search(rf"(?<![\w.-]){re.escape(filename)}(?![\w.-])", text)
            is not None
        )

    reachable = skill_text
    pending = dict(bodies)
    # To a fixed point: a pointer chain can run in any order, and a single pass
    # follows only the ones that happen to come out in the right one.
    while True:
        found = [name for name in pending if names(name, reachable)]
        if not found:
            break
        for filename in found:
            reachable += pending.pop(filename)
    return sorted(pending)


def orphan_reference_errors() -> list[str]:
    """Every reference and asset must be reachable from its SKILL.md.

    A file nobody points at is a file nobody reads, and adding one is the easiest
    way to move a rule out of an agent's path without noticing. Reachability is
    one hop: named in SKILL.md, or named in something SKILL.md names. That is
    deliberately structural — it asserts the pointer exists, never what the prose
    around it says, so a rewrite stays free.
    """
    errors: list[str] = []
    for name in NAMES:
        skill_path = SKILLS_ROOT / name / "SKILL.md"
        if not skill_path.is_file():
            continue
        for directory in ("references", "assets"):
            source_dir = SKILLS_ROOT / name / directory
            if not source_dir.is_dir():
                continue
            bodies: dict[str, str] = {}
            for candidate in sorted(source_dir.iterdir()):
                if not candidate.is_file():
                    continue
                try:
                    bodies[candidate.name] = candidate.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    bodies[candidate.name] = ""
            errors.extend(
                f"{name}: {directory}/{orphan} is named nowhere an agent reads"
                for orphan in unreachable(
                    skill_path.read_text(encoding="utf-8"), bodies
                )
            )
    return errors


def installed_mirror_errors() -> list[str]:
    """Check the installed Codex mirror, when one exists on this machine.

    These four skills are cross-harness: they carry a per-harness peer table, so
    the mirror hook copies them verbatim instead of renaming Claude -> Codex.
    That rename is what silently produced "| Role | In Codex | In Codex |" and
    "In Codex or Codex" in the shipped Codex copies, leaving them unable to pick
    a column. The corruption survived because nothing compared the two trees.

    Deliberately opt-in: absent ~/.codex this returns nothing, so packaging the
    skills on a machine without Codex is not a failure. Every text file is
    compared, not just SKILL.md — the worst corruption lived in a reference file.
    """
    mirror_root = HOME / ".codex" / "skills"
    if not mirror_root.is_dir():
        return []
    errors: list[str] = []
    hazards = ("In Codex | In Codex", "Codex or Codex", "Opus in Codex")
    for name in NAMES:
        source_dir = SKILLS_ROOT / name
        mirror_dir = mirror_root / name
        if not mirror_dir.is_dir():
            errors.append(f"{name}: not mirrored to ~/.codex/skills")
            continue
        for source in sorted(source_dir.rglob("*")):
            if not source.is_file() or source.suffix.lower() != ".md":
                continue
            relative = source.relative_to(source_dir)
            copy = mirror_dir / relative
            if not copy.is_file():
                errors.append(f"{name}: mirror missing {relative}")
                continue
            mirrored = copy.read_text(encoding="utf-8")
            if mirrored != source.read_text(encoding="utf-8"):
                errors.append(f"{name}: mirror of {relative} differs from source")
            for hazard in hazards:
                if hazard in mirrored:
                    errors.append(
                        f"{name}: mirror of {relative} was renamed — {hazard!r}"
                    )
    return errors


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
        canonical = HOME / ".claude" / "skills" / name / "SKILL.md"
        if canonical.resolve() != skill_path.resolve():
            if not canonical.is_file():
                errors.append(f"{name}: missing canonical copy under ~/.claude")
            elif canonical.read_text(encoding="utf-8") != text:
                errors.append(f"{name}: drifted from the canonical ~/.claude copy")

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
        "put the plan in front of the user for approval",
        "Make the smallest change at the root cause",
    ):
        errors.append("base: implementation precedes its approval")
    if ordered_wrong(
        base,
        "Every finding is a hypothesis",
        "Last check \u2014 the product, in a browser",
    ) or ordered_wrong(
        base,
        "Last check \u2014 the product, in a browser",
        "Ask before commit",
    ):
        errors.append("base: the browser check is not the last verification")
    errors.extend(contract_errors(automatic, AUTOMATIC_PHRASES, "automatic"))
    if ordered_wrong(
        automatic,
        "Consent, once, up front",
        "Reject the plan outright, in either direction",
    ):
        errors.append("automatic: the plan gate precedes consent")
    if ordered_wrong(
        automatic,
        "land only after that acceptance",
        "Run only after the landing happened",
    ):
        errors.append("automatic: release precedes the landing")
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
        "A product with a UI is not verified until someone drove it",
        "Never end a handoff whose only shape is what went well",
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

    # Reachability self-control. Direct naming passes, the second hop passes, an
    # orphan is caught, and a file that names only itself does not bootstrap
    # itself into being reachable.
    if (
        unreachable("read alpha.md", {"alpha.md": ""})
        # Second hop, and the same chain running backwards alphabetically — the
        # ordering a single pass follows only by luck.
        or unreachable("read alpha.md", {"alpha.md": "then beta.md", "beta.md": ""})
        or unreachable("read zulu.md", {"alpha.md": "", "zulu.md": "then alpha.md"})
        or "orphan.md" not in unreachable("read alpha.md", {"alpha.md": "", "orphan.md": ""})
        # A name must not be reachable as the tail of a longer one.
        or "contract.md" not in unreachable(
            "read evidence-contract.md", {"evidence-contract.md": "", "contract.md": ""}
        )
        # Nothing bootstraps itself into being reachable.
        # Nor as the prefix of a longer one.
        or "plan.md" not in unreachable("read plan.md.bak", {"plan.md.bak": "", "plan.md": ""})
        # Nothing bootstraps itself into being reachable.
        or "self.md" not in unreachable("read nothing", {"self.md": "self.md"})
    ):
        errors.append("validator: reachability self-control failed")

    errors.extend(orphan_reference_errors())
    errors.extend(installed_mirror_errors())

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
