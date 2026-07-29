#!/usr/bin/env python3
"""Deterministic state ledger for peer-bug-review."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


SCHEMA_VERSION = 3
SUPPORTED_SCHEMA_VERSIONS = {2, 3}
FINDING_STATUSES = {
    "suspected",
    "confirmed_bug",
    "not_a_bug",
    "needs_decision",
    "duplicate",
    "ready",
    "implementing",
    "accepted",
    "documented_blocked",
}
COVERAGE_STATUSES = {"pending", "covered", "partial", "skipped", "blocked"}
TERMINAL_NON_BUG = {"not_a_bug", "needs_decision", "duplicate"}
STAGE_HARD_LIMITS = {"confirmation": 3, "plan": 10, "fix": 10}
INTEGRATION_HARD_LIMIT = 3
REVIEW_MARKERS = {
    "confirmation": (
        "CLASSIFICATION:",
        "REPRODUCTION:",
        "AUTHORITY:",
        "NEGATIVE_CONTROL:",
        "ROOT_CAUSE:",
        "COUNTEREVIDENCE:",
    ),
    "plan": ("VERDICT:", "PLAN:", "COUNTEREVIDENCE:"),
    "fix": ("VERDICT:", "DIFF:", "TESTS:", "COUNTEREVIDENCE:"),
    "integration": (
        "VERDICT:",
        "COVERAGE:",
        "PRODUCT_CHECKS:",
        "INTERACTIONS:",
        "REMAINING_UNCERTAINTY:",
    ),
}
RESOLUTION_MARKERS = (
    "RESOLUTION:",
    "RESOLVED_BY:",
    "PROOF:",
    "REMAINING_UNCERTAINTY:",
)
DECISION_MARKERS = ("DECISION:", "AUTHORITY:", "RESOLVES:")
SPEC_MARKERS = (
    "## Classification",
    "## Authority and intent",
    "## Reproduction",
    "## Root cause and scope",
    "## Failure-first proof",
    "## Minimal plan",
)
COVERED_MARKERS = ("COVERED:", "PROBES:", "NEGATIVE_FINDINGS:", "COMMANDS:")
RISKS = {"low", "medium", "high", "critical"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def append_trajectory(path: Path, state: dict, event: str) -> None:
    """Write a replayable, non-authoritative snapshot of a successful transition."""
    encoded = json.dumps(state, sort_keys=True, separators=(",", ":")).encode()
    coverage = state.get("coverage", {})
    findings = state.get("findings", {})
    record = {
        "at": now(),
        "run_id": hashlib.sha256(
            f"{path.resolve()}:{state.get('created_at', '')}".encode()
        ).hexdigest()[:16],
        "event": event,
        "state_sha256": hashlib.sha256(encoded).hexdigest(),
        "status": state.get("status"),
        "coverage": {
            status: sum(
                1
                for value in coverage.values()
                if isinstance(value, dict) and value.get("status") == status
            )
            for status in sorted(COVERAGE_STATUSES)
        },
        "findings": {
            status: sum(
                1
                for value in findings.values()
                if isinstance(value, dict) and value.get("status") == status
            )
            for status in sorted(FINDING_STATUSES)
        },
    }
    with Path(f"{path}.events.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def save(path: Path, state: dict, event: str = "state-updated") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = now()
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(state, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temp_name, path)
        try:
            append_trajectory(path, state, event)
        except OSError as exc:
            print(f"WARNING: trajectory not written: {exc}", file=sys.stderr)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def new_state(runtime: str, mode: str, max_iterations: int) -> dict:
    if runtime != "codex":
        raise ValueError("peer-bug-review is Codex-only")
    if max_iterations < 1 or max_iterations > 10:
        raise ValueError("max_iterations must be between 1 and 10")
    stamp = now()
    return {
        "schema_version": SCHEMA_VERSION,
        "runtime": runtime,
        "mode": mode,
        "status": "active",
        "max_iterations": max_iterations,
        "created_at": stamp,
        "updated_at": stamp,
        "coverage_frozen": False,
        "inventory_manifest": None,
        "coverage": {},
        "findings": {},
        "review_targets": {},
        "format_failures": [],
        "integration_reviews": [],
    }


def artifact(
    path_value: str,
    required_markers: tuple[str, ...] = (),
) -> dict[str, str]:
    if not isinstance(path_value, str) or not path_value.strip():
        raise ValueError("artifact path is required")
    path = Path(path_value).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"artifact does not exist: {path}")
    data = path.read_bytes()
    if len(data.strip()) < 32:
        raise ValueError(f"artifact is too small to contain review evidence: {path}")
    if required_markers:
        text = data.decode("utf-8", errors="replace")
        missing = [marker for marker in required_markers if marker not in text]
        if missing:
            raise ValueError(
                f"artifact missing required sections {', '.join(missing)}: {path}"
            )
        empty = [
            marker
            for marker in required_markers
            if marker.endswith(":")
            and marker != "INVENTORY:"
            and not any(
                line.startswith(marker) and line[len(marker) :].strip()
                for line in text.splitlines()
            )
        ]
        if empty:
            raise ValueError(
                f"artifact has empty required sections {', '.join(empty)}: {path}"
            )
    return {
        "path": str(path),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def raw_artifact(path_value: str) -> dict[str, str]:
    if not isinstance(path_value, str) or not path_value.strip():
        raise ValueError("artifact path is required")
    path = Path(path_value).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"artifact does not exist: {path}")
    return {
        "path": str(path),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }


def raw_artifact_error(value: object, label: str) -> str | None:
    if not isinstance(value, dict):
        return f"{label}: artifact must be an object"
    try:
        current = raw_artifact(value.get("path"))
    except (OSError, TypeError, ValueError) as exc:
        return f"{label}: {exc}"
    if current["sha256"] != value.get("sha256"):
        return f"{label}: artifact digest changed"
    return None


def artifact_error(
    value: object,
    label: str,
    required_markers: tuple[str, ...] = (),
) -> str | None:
    if not isinstance(value, dict):
        return f"{label}: artifact must be an object"
    path_value = value.get("path")
    digest = value.get("sha256")
    if not isinstance(path_value, str) or not path_value:
        return f"{label}: artifact path missing"
    try:
        current = artifact(path_value, required_markers)
    except (OSError, ValueError) as exc:
        return f"{label}: {exc}"
    if current["sha256"] != digest:
        return f"{label}: artifact digest changed"
    return None


def review_markers(stage: str, schema_version: int) -> tuple[str, ...]:
    markers = REVIEW_MARKERS[stage]
    return markers + (("TARGET_ARTIFACT:",) if schema_version >= 3 else ())


def target_key(stage: str, finding_id: str, iteration: int) -> str:
    return f"{stage}:{finding_id}:{iteration}"


def target_declaration(target: dict[str, str]) -> str:
    return f"{target['sha256']} {target['path']}"


def target_bundle_error(
    value: object,
    stage: str,
    finding_id: str,
    iteration: int,
    label: str,
) -> str | None:
    problem = artifact_error(value, label)
    if problem:
        return problem
    try:
        payload = json.loads(Path(value["path"]).read_text(encoding="utf-8"))
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return f"{label}: invalid target bundle: {exc}"
    if not isinstance(payload, dict):
        return f"{label}: target bundle must be an object"
    if payload.get("review_stage") != stage:
        return f"{label}: target stage mismatch"
    if payload.get("finding_id") != finding_id:
        return f"{label}: target finding mismatch"
    if payload.get("iteration") != iteration:
        return f"{label}: target iteration mismatch"
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        return f"{label}: target artifacts missing"
    seen_paths = set()
    for index, item in enumerate(artifacts, start=1):
        if not isinstance(item, dict):
            return f"{label}: target artifact {index} must be an object"
        path_value = item.get("path")
        digest = item.get("sha256")
        encoded = item.get("content_base64")
        if not isinstance(path_value, str) or not path_value:
            return f"{label}: target artifact {index} path missing"
        if path_value in seen_paths:
            return f"{label}: target artifact {index} path repeated"
        seen_paths.add(path_value)
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            return f"{label}: target artifact {index} digest invalid"
        if not isinstance(encoded, str) or not encoded:
            return f"{label}: target artifact {index} bytes missing"
        try:
            data = base64.b64decode(encoded, validate=True)
        except (ValueError, TypeError) as exc:
            return f"{label}: target artifact {index} encoding invalid: {exc}"
        if hashlib.sha256(data).hexdigest() != digest:
            return f"{label}: target artifact {index} digest mismatch"
    return None


def declared_text(value: dict[str, str], marker: str) -> str:
    text = Path(value["path"]).read_text(encoding="utf-8", errors="replace")
    declarations = [
        line[len(marker) :].strip()
        for line in text.splitlines()
        if line.startswith(marker)
    ]
    if len(declarations) != 1:
        raise ValueError(f"artifact must contain exactly one {marker} declaration")
    return declarations[0]


def declared_value(value: dict[str, str], marker: str) -> str:
    return declared_text(value, marker).upper()


def expected_declaration(stage: str, verdict: str) -> str:
    if stage == "confirmation":
        return {
            "confirmed": "CONFIRMED_BUG",
            "inconclusive": "NEEDS_DECISION",
            "not-a-bug": "NOT_A_BUG",
            "needs-decision": "NEEDS_DECISION",
            "duplicate": "DUPLICATE",
        }[verdict]
    return {"accepted": "ACCEPTED", "rejected": "REJECTED"}[verdict]


def declaration_error(
    value: dict[str, str],
    stage: str,
    verdict: str,
    label: str,
) -> str | None:
    marker = "CLASSIFICATION:" if stage == "confirmation" else "VERDICT:"
    try:
        actual = declared_value(value, marker)
        expected = expected_declaration(stage, verdict)
    except (KeyError, OSError, TypeError, ValueError) as exc:
        return f"{label}: {exc}"
    if actual != expected:
        return f"{label}: declared {actual}, recorded {expected}"
    return None


def control_marker_error(
    value: dict[str, str],
    stage: str,
    label: str,
) -> str | None:
    forbidden = "VERDICT:" if stage == "confirmation" else "CLASSIFICATION:"
    try:
        text = Path(value["path"]).read_text(encoding="utf-8", errors="replace")
    except (KeyError, OSError, TypeError, ValueError) as exc:
        return f"{label}: {exc}"
    if any(line.startswith(forbidden) for line in text.splitlines()):
        return f"{label}: {forbidden} is not valid for {stage}"
    return None


def manifest_inventory(value: dict[str, str]) -> set[str]:
    text = Path(value["path"]).read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    fields = {
        key: next(
            (
                line.split(":", 1)[1].strip()
                for line in lines
                if line.startswith(f"{key}:")
            ),
            "",
        )
        for key in ("REPOSITORY", "COMMIT")
    }
    if not all(fields.values()):
        raise ValueError("manifest REPOSITORY and COMMIT values must be non-empty")
    try:
        start = next(
            index for index, line in enumerate(lines) if line.strip() == "INVENTORY:"
        )
    except StopIteration as exc:
        raise ValueError("manifest INVENTORY section missing") from exc
    result = {
        line.strip()[2:].strip()
        for line in lines[start + 1 :]
        if line.strip().startswith("- ")
    }
    if not result:
        raise ValueError("manifest INVENTORY list is empty")
    return result


def evidence_names_item(text: str, item_id: str) -> bool:
    boundary = r"A-Za-z0-9_./-"
    return bool(
        re.search(
            rf"(?<![{boundary}]){re.escape(item_id)}(?![{boundary}])",
            text,
        )
    )


def evidence_section(text: str, marker: str) -> str:
    lines = text.splitlines()
    starts = [index for index, line in enumerate(lines) if line.startswith(marker)]
    if len(starts) != 1:
        raise ValueError(f"evidence must contain exactly one {marker} section")
    start = starts[0]
    result = [lines[start][len(marker) :].strip()]
    for line in lines[start + 1 :]:
        if re.match(r"^[A-Z][A-Z_]*:", line):
            break
        result.append(line)
    return "\n".join(result)


def finding_lifecycle_errors(
    finding_id: str,
    finding: dict,
    *,
    max_iterations: int,
    schema_version: int,
) -> list[str]:
    errors = []
    reviews = finding.get("reviews")
    status = finding.get("status")
    if not isinstance(reviews, list) or not isinstance(status, str):
        return errors
    valid_reviews = [
        review
        for review in reviews
        if isinstance(review, dict)
        and isinstance(review.get("stage"), str)
        and review.get("stage") in {"confirmation", "plan", "fix"}
        and isinstance(review.get("verdict"), str)
    ]
    stage_order = {"confirmation": 0, "plan": 1, "fix": 2}
    order = [stage_order[review["stage"]] for review in valid_reviews]
    if order != sorted(order):
        errors.append(f"{finding_id}: review stages are out of order")
    grouped = {
        stage: [review for review in valid_reviews if review["stage"] == stage]
        for stage in stage_order
    }
    for stage, stage_reviews in grouped.items():
        for iteration, review in enumerate(stage_reviews, start=1):
            if review.get("iteration") != iteration:
                errors.append(
                    f"{finding_id}: {stage} review iteration {iteration} mismatch"
                )
            if review.get("verdict") in {"rejected", "inconclusive"} and not (
                isinstance(review.get("blocker"), str)
                and review["blocker"].strip()
            ):
                errors.append(
                    f"{finding_id}: {stage} review iteration {iteration} blocker missing"
                )

    def exhausted(stage: str, stage_reviews: list[dict]) -> bool:
        if not stage_reviews:
            return False
        last = stage_reviews[-1]
        blocker = last.get("blocker")
        repeated = (
            sum(
                1
                for review in stage_reviews
                if review.get("verdict") in {"rejected", "inconclusive"}
                and review.get("blocker") == blocker
            )
            if isinstance(blocker, str) and blocker.strip()
            else 0
        )
        return repeated >= 2 or len(stage_reviews) >= min(
            max_iterations,
            STAGE_HARD_LIMITS[stage],
        )

    confirmations = grouped["confirmation"]
    plans = grouped["plan"]
    fixes = grouped["fix"]
    expected = "suspected"
    if confirmations:
        verdict = confirmations[-1].get("verdict")
        expected = {
            "not-a-bug": "not_a_bug",
            "needs-decision": "needs_decision",
            "duplicate": "duplicate",
        }.get(verdict, "suspected")
        if verdict == "inconclusive":
            expected = (
                "needs_decision"
                if exhausted("confirmation", confirmations)
                else "suspected"
            )
        elif verdict == "confirmed":
            expected = "confirmed_bug"
            if plans:
                if plans[-1].get("verdict") == "rejected":
                    expected = (
                        "documented_blocked"
                        if exhausted("plan", plans)
                        else "confirmed_bug"
                    )
                elif plans[-1].get("verdict") == "accepted":
                    expected = "ready"
                    if fixes:
                        if fixes[-1].get("verdict") == "accepted":
                            expected = "accepted"
                        elif fixes[-1].get("verdict") == "rejected":
                            expected = (
                                "documented_blocked"
                                if exhausted("fix", fixes)
                                else "implementing"
                            )
                    elif status == "implementing":
                        expected = "implementing"
    if status != expected:
        errors.append(
            f"{finding_id}: status {status} does not match review history {expected}"
        )
    implementation = finding.get("implementation_started")
    needs_mark = status in {"implementing", "accepted"} or bool(fixes)
    if schema_version >= 3 and needs_mark and not (
        isinstance(implementation, dict)
        and isinstance(implementation.get("at"), str)
        and implementation.get("at")
        and isinstance(implementation.get("note"), str)
        and implementation.get("note").strip()
    ):
        errors.append(f"{finding_id}: implementation start record missing")
    if schema_version >= 3 and status == "ready" and implementation is not None:
        errors.append(f"{finding_id}: ready finding has implementation start record")
    return errors


def validate(state: dict, *, require_complete: bool = False) -> list[str]:
    if not isinstance(state, dict):
        return ["state must be an object"]
    errors: list[str] = []
    schema_version = state.get("schema_version")
    if not isinstance(schema_version, int) or schema_version not in SUPPORTED_SCHEMA_VERSIONS:
        errors.append("unsupported schema_version")
        schema_version = 0
    if state.get("runtime") != "codex":
        errors.append("invalid runtime")
    if not isinstance(state.get("mode"), str) or state.get("mode") not in {
        "audit",
        "repair",
    }:
        errors.append("invalid mode")
    limit = state.get("max_iterations")
    if not isinstance(limit, int) or not 1 <= limit <= 10:
        errors.append("invalid max_iterations")

    if not isinstance(state.get("status"), str) or state.get("status") not in {
        "active",
        "complete",
        "documented_blocked",
    }:
        errors.append("invalid run status")
    if not isinstance(state.get("coverage_frozen"), bool):
        errors.append("coverage_frozen must be boolean")
    manifest = state.get("inventory_manifest")
    if state.get("coverage_frozen"):
        problem = artifact_error(
            manifest,
            "inventory manifest",
            ("REPOSITORY:", "COMMIT:", "INVENTORY:"),
        )
        if problem:
            errors.append(problem)

    coverage = state.get("coverage")
    if not isinstance(coverage, dict):
        errors.append("coverage must be an object")
        coverage = {}
    for item_id, item in coverage.items():
        if not isinstance(item_id, str) or ":" not in item_id:
            errors.append(f"coverage {item_id}: stable ID must contain ':'")
        if not isinstance(item, dict):
            errors.append(f"coverage {item_id}: entry must be an object")
            continue
        if not item.get("lane"):
            errors.append(f"coverage {item_id}: lane missing")
        risk = item.get("risk")
        if not isinstance(risk, str) or risk not in RISKS:
            errors.append(f"coverage {item_id}: invalid risk")
        priority = item.get("priority")
        if not isinstance(priority, int) or not 1 <= priority <= 9999:
            errors.append(f"coverage {item_id}: invalid priority")
        coverage_status = item.get("status")
        if not isinstance(coverage_status, str) or coverage_status not in COVERAGE_STATUSES:
            errors.append(f"coverage {item_id}: invalid status")
        if isinstance(coverage_status, str) and coverage_status in {
            "covered",
            "skipped",
            "blocked",
        }:
            markers = {
                "covered": COVERED_MARKERS,
                "skipped": ("SKIPPED:", "REASON:"),
                "blocked": ("BLOCKED:", "MISSING:"),
            }[item["status"]]
            problem = artifact_error(
                item.get("evidence"),
                f"coverage {item_id}",
                markers,
            )
            if problem:
                errors.append(problem)
            else:
                evidence_text = Path(item["evidence"]["path"]).read_text(
                    encoding="utf-8",
                    errors="replace",
                )
                try:
                    item_text = (
                        evidence_section(evidence_text, "COVERED:")
                        if item.get("status") == "covered"
                        else evidence_text
                    )
                    if not evidence_names_item(item_text, item_id):
                        errors.append(
                            f"coverage {item_id}: evidence does not name the item"
                        )
                except ValueError as exc:
                    errors.append(f"coverage {item_id}: {exc}")
    if state.get("coverage_frozen") and isinstance(manifest, dict):
        try:
            manifest_ids = manifest_inventory(manifest)
            if manifest_ids != set(coverage):
                errors.append("inventory manifest IDs do not match coverage IDs")
        except (KeyError, OSError, TypeError, ValueError) as exc:
            errors.append(f"inventory manifest: {exc}")

    review_targets = state.get("review_targets", {})
    if schema_version >= 3 and not isinstance(review_targets, dict):
        errors.append("review_targets must be an object")
        review_targets = {}
    elif schema_version == 2:
        review_targets = {}
    target_digests: list[str] = []
    for key, record in review_targets.items():
        if not isinstance(record, dict):
            errors.append(f"review target {key}: must be an object")
            continue
        stage = record.get("stage")
        finding_id = record.get("finding_id")
        iteration = record.get("iteration")
        if not isinstance(stage, str) or stage not in {
            "confirmation",
            "plan",
            "fix",
            "integration",
        }:
            errors.append(f"review target {key}: invalid stage")
            continue
        if not isinstance(finding_id, str) or not finding_id:
            errors.append(f"review target {key}: invalid finding")
            continue
        if not isinstance(iteration, int) or iteration < 1:
            errors.append(f"review target {key}: invalid iteration")
            continue
        if key != target_key(stage, finding_id, iteration):
            errors.append(f"review target {key}: key mismatch")
        problem = target_bundle_error(
            record.get("bundle"),
            stage,
            finding_id,
            iteration,
            f"review target {key}",
        )
        if problem:
            errors.append(problem)
        elif isinstance(record.get("bundle"), dict):
            target_digests.append(record["bundle"]["sha256"])
        applied = record.get("applied_decisions", [])
        if not isinstance(applied, list) or any(
            not isinstance(value, str) for value in applied
        ):
            errors.append(f"review target {key}: applied_decisions must be strings")
        elif len(applied) != len(set(applied)):
            errors.append(f"review target {key}: duplicate applied decision")
        superseded = record.get("superseded", [])
        if not isinstance(superseded, list):
            errors.append(f"review target {key}: superseded must be an array")
            continue
        supersession_ids = []
        for index, old in enumerate(superseded, start=1):
            if not isinstance(old, dict):
                errors.append(
                    f"review target {key}: superseded {index} must be an object"
                )
                continue
            decision_id = old.get("decision_id")
            if not isinstance(decision_id, str):
                errors.append(
                    f"review target {key}: superseded {index} decision missing"
                )
            else:
                supersession_ids.append(decision_id)
            problem = target_bundle_error(
                old.get("bundle"),
                stage,
                finding_id,
                iteration,
                f"review target {key} superseded {index}",
            )
            if problem:
                errors.append(problem)
            elif isinstance(old.get("bundle"), dict):
                target_digests.append(old["bundle"]["sha256"])
        if len(supersession_ids) != len(set(supersession_ids)):
            errors.append(f"review target {key}: decision superseded twice")
        if (
            isinstance(applied, list)
            and all(isinstance(value, str) for value in applied)
            and not set(supersession_ids) <= set(applied)
        ):
            errors.append(f"review target {key}: superseded decision not applied")
        chain = [
            old.get("bundle")
            for old in superseded
            if isinstance(old, dict) and isinstance(old.get("bundle"), dict)
        ] + ([record["bundle"]] if isinstance(record.get("bundle"), dict) else [])
        for index, decision_id in enumerate(supersession_ids):
            if index + 1 >= len(chain):
                break
            try:
                next_payload = json.loads(
                    Path(chain[index + 1]["path"]).read_text(encoding="utf-8")
                )
                if not isinstance(next_payload, dict):
                    raise ValueError("target bundle must be an object")
            except (KeyError, OSError, TypeError, ValueError) as exc:
                errors.append(f"review target {key}: supersession chain: {exc}")
                continue
            if (
                next_payload.get("supersedes") != chain[index]["sha256"]
                or next_payload.get("decision_id") != decision_id
            ):
                errors.append(f"review target {key}: supersession chain mismatch")
    if len(target_digests) != len(set(target_digests)):
        errors.append("review target bundle reused in run")

    findings = state.get("findings")
    if not isinstance(findings, dict):
        errors.append("findings must be an object")
        findings = {}
    unresolved_gate_decisions: list[str] = []
    for key, record in review_targets.items():
        if not isinstance(record, dict):
            continue
        stage = record.get("stage")
        finding_id = record.get("finding_id")
        if stage == "integration":
            if finding_id != "ALL":
                errors.append(f"review target {key}: integration finding must be ALL")
        elif finding_id not in findings:
            errors.append(f"review target {key}: unknown finding {finding_id}")
        if isinstance(stage, str) and stage in {"plan", "fix", "integration"}:
            gate_subject = "RUN" if stage == "integration" else finding_id
            unresolved, required = gate_decision_requirements(
                {**state, "findings": findings},
                stage,
                gate_subject,
                record.get("iteration"),
            )
            unresolved_gate_decisions.extend(unresolved)
            applied = record.get("applied_decisions", [])
            if (
                isinstance(applied, list)
                and all(isinstance(value, str) for value in applied)
                and not set(applied) <= set(required)
            ):
                errors.append(f"review target {key}: invalid applied decision")
            try:
                active_payload = json.loads(
                    Path(record["bundle"]["path"]).read_text(encoding="utf-8")
                )
                if not isinstance(active_payload, dict):
                    raise ValueError("target bundle must be an object")
                active_digests = [
                    item.get("sha256")
                    for item in active_payload.get("artifacts", [])
                    if isinstance(item, dict)
                ]
            except (KeyError, OSError, TypeError, ValueError) as exc:
                errors.append(f"review target {key}: active bundle replay: {exc}")
                active_digests = []
            if isinstance(applied, list):
                for decision_id in applied:
                    if not isinstance(decision_id, str):
                        continue
                    evidence_values = required.get(decision_id, [])
                    required_digests = [
                        value.get("sha256")
                        for value in evidence_values
                        if isinstance(value, dict)
                    ]
                    if (
                        len(required_digests) != 2
                        or any(digest not in active_digests for digest in required_digests)
                    ):
                        errors.append(
                            f"review target {key}: decision evidence missing for "
                            f"{decision_id}"
                        )
            superseded = record.get("superseded", [])
            if isinstance(superseded, list):
                bundles = [
                    old.get("bundle")
                    for old in superseded
                    if isinstance(old, dict) and isinstance(old.get("bundle"), dict)
                ] + (
                    [record["bundle"]]
                    if isinstance(record.get("bundle"), dict)
                    else []
                )
                decisions = [
                    old.get("decision_id")
                    for old in superseded
                    if isinstance(old, dict)
                ]
                for index, decision_id in enumerate(decisions):
                    if index + 1 >= len(bundles):
                        break
                    try:
                        before = json.loads(
                            Path(bundles[index]["path"]).read_text(encoding="utf-8")
                        )["artifacts"]
                        after = json.loads(
                            Path(bundles[index + 1]["path"]).read_text(
                                encoding="utf-8"
                            )
                        )["artifacts"]
                    except (KeyError, OSError, TypeError, ValueError) as exc:
                        errors.append(
                            f"review target {key}: supersession replay: {exc}"
                        )
                        continue
                    expected_append = [
                        value.get("sha256")
                        for value in required.get(decision_id, [])
                        if isinstance(value, dict)
                    ]
                    actual_append = [
                        value.get("sha256")
                        for value in after[len(before) :]
                        if isinstance(value, dict)
                    ]
                    if (
                        after[: len(before)] != before
                        or actual_append != expected_append
                    ):
                        errors.append(
                            f"review target {key}: supersession artifacts mismatch "
                            f"for {decision_id}"
                        )
    resolution_digests: list[str] = []
    decision_digests: list[str] = []
    for finding_id, finding in findings.items():
        if not isinstance(finding, dict):
            errors.append(f"{finding_id}: finding must be an object")
            continue
        finding_status = finding.get("status")
        if not isinstance(finding_status, str) or finding_status not in FINDING_STATUSES:
            errors.append(f"{finding_id}: invalid status")
        item_id = finding.get("item")
        if not isinstance(item_id, str) or item_id not in coverage:
            errors.append(f"{finding_id}: unknown coverage item {item_id}")
        counts = finding.get("iterations")
        if not isinstance(counts, dict):
            errors.append(f"{finding_id}: iterations must be an object")
            continue
        for stage in ("confirmation", "plan", "fix"):
            value = counts.get(stage)
            stage_limit = min(limit or 0, STAGE_HARD_LIMITS[stage])
            if not isinstance(value, int) or value < 0 or value > stage_limit:
                errors.append(f"{finding_id}: invalid {stage} iteration count")
        reviews = finding.get("reviews")
        if not isinstance(reviews, list):
            errors.append(f"{finding_id}: reviews must be an array")
        else:
            for index, review in enumerate(reviews, start=1):
                if not isinstance(review, dict):
                    errors.append(f"{finding_id}: review {index} must be an object")
                    continue
                reviewer = review.get("reviewer")
                if not isinstance(reviewer, str) or not re.fullmatch(
                    r"agent:[A-Za-z0-9_./-]{3,}",
                    reviewer,
                ):
                    errors.append(f"{finding_id}: invalid reviewer identity")
                stage = review.get("stage")
                verdict = review.get("verdict")
                if (
                    not isinstance(stage, str)
                    or stage not in REVIEW_MARKERS
                    or not isinstance(verdict, str)
                    or verdict not in {
                    "confirmed",
                    "inconclusive",
                    "not-a-bug",
                    "needs-decision",
                    "duplicate",
                    "accepted",
                    "rejected",
                    }
                ):
                    errors.append(f"{finding_id}: review {index} has invalid stage/verdict")
                problem = artifact_error(
                    review.get("evidence"),
                    f"{finding_id} review {index}",
                    review_markers(stage, schema_version)
                    if isinstance(stage, str) and stage in REVIEW_MARKERS
                    else (),
                )
                if problem:
                    errors.append(problem)
                elif isinstance(stage, str) and stage in {
                    "confirmation",
                    "plan",
                    "fix",
                } and isinstance(verdict, str) and verdict in {
                    "confirmed",
                    "inconclusive",
                    "not-a-bug",
                    "needs-decision",
                    "duplicate",
                    "accepted",
                    "rejected",
                }:
                    problem = declaration_error(
                        review["evidence"],
                        stage,
                        review["verdict"],
                        f"{finding_id} review {index}",
                    )
                    if problem:
                        errors.append(problem)
                    if schema_version >= 3:
                        iteration = review.get("iteration")
                        key = target_key(stage, finding_id, iteration)
                        registered = review_targets.get(key)
                        if not isinstance(registered, dict):
                            errors.append(
                                f"{finding_id} review {index}: frozen target missing"
                            )
                        elif review.get("target") != registered.get("bundle"):
                            errors.append(
                                f"{finding_id} review {index}: target does not match freeze"
                            )
                        else:
                            problem = target_bundle_error(
                                review.get("target"),
                                stage,
                                finding_id,
                                iteration,
                                f"{finding_id} review {index} target",
                            )
                            if problem:
                                errors.append(problem)
                            else:
                                try:
                                    declared = declared_text(
                                        review["evidence"],
                                        "TARGET_ARTIFACT:",
                                    )
                                    expected = target_declaration(review["target"])
                                except (
                                    KeyError,
                                    OSError,
                                    TypeError,
                                    ValueError,
                                ) as exc:
                                    errors.append(
                                        f"{finding_id} review {index} target: {exc}"
                                    )
                                else:
                                    if declared != expected:
                                        errors.append(
                                            f"{finding_id} review {index}: "
                                            "target declaration mismatch"
                                        )
                    problem = control_marker_error(
                        review["evidence"],
                        stage,
                        f"{finding_id} review {index}",
                    )
                    if problem:
                        errors.append(problem)
            for stage in ("confirmation", "plan", "fix"):
                actual = sum(1 for review in reviews if review.get("stage") == stage)
                if counts.get(stage) != actual:
                    errors.append(f"{finding_id}: {stage} counter does not match reviews")
            errors.extend(
                finding_lifecycle_errors(
                    finding_id,
                    finding,
                    max_iterations=limit if isinstance(limit, int) else 1,
                    schema_version=schema_version,
                )
            )
        annotations = finding.get("resolution_annotations", [])
        if not isinstance(annotations, list):
            errors.append(f"{finding_id}: resolution_annotations must be an array")
        else:
            if len(annotations) > 1:
                errors.append(f"{finding_id}: multiple resolution annotations")
            for index, annotation in enumerate(annotations, start=1):
                if not isinstance(annotation, dict):
                    errors.append(
                        f"{finding_id}: resolution annotation {index} must be an object"
                    )
                    continue
                resolved_by = annotation.get("resolved_by")
                resolver = (
                    findings.get(resolved_by)
                    if isinstance(resolved_by, str)
                    else None
                )
                if finding.get("status") != "needs_decision":
                    errors.append(
                        f"{finding_id}: resolution annotation requires needs_decision"
                    )
                if resolved_by == finding_id or not isinstance(resolver, dict):
                    errors.append(f"{finding_id}: invalid resolution target {resolved_by}")
                elif resolver.get("status") != "accepted":
                    errors.append(f"{finding_id}: resolver {resolved_by} is not accepted")
                if not str(annotation.get("note", "")).strip():
                    errors.append(f"{finding_id}: resolution note missing")
                problem = artifact_error(
                    annotation.get("evidence"),
                    f"{finding_id} resolution annotation {index}",
                    RESOLUTION_MARKERS,
                )
                if problem:
                    errors.append(problem)
                else:
                    evidence = annotation["evidence"]
                    resolution_digests.append(evidence["sha256"])
                    try:
                        resolution = declared_text(evidence, "RESOLUTION:")
                        declared = declared_text(evidence, "RESOLVED_BY:")
                    except (KeyError, OSError, TypeError, ValueError) as exc:
                        errors.append(f"{finding_id}: resolution declaration: {exc}")
                    else:
                        if resolution != "RELATED_ACCEPTED_FIX":
                            errors.append(
                                f"{finding_id}: invalid resolution declaration {resolution}"
                            )
                        if declared != resolved_by:
                            errors.append(
                                f"{finding_id}: resolution declares {declared}, "
                                f"recorded {resolved_by}"
                            )
        decision_for = finding.get("decision_for")
        if decision_for is not None:
            if not isinstance(decision_for, dict):
                errors.append(f"{finding_id}: decision_for must be an object")
            else:
                decision_stage = decision_for.get("stage")
                decision_subject = decision_for.get("subject")
                decision_iteration = decision_for.get("iteration")
                if not isinstance(decision_stage, str) or decision_stage not in {
                    "plan",
                    "fix",
                    "integration",
                }:
                    errors.append(f"{finding_id}: invalid decision stage")
                if not isinstance(decision_iteration, int) or decision_iteration < 1:
                    errors.append(f"{finding_id}: invalid decision iteration")
                elif decision_stage == "integration":
                    if decision_subject != "RUN":
                        errors.append(
                            f"{finding_id}: integration decision subject must be RUN"
                        )
                elif (
                    not isinstance(decision_subject, str)
                    or decision_subject == finding_id
                    or decision_subject not in findings
                ):
                    errors.append(f"{finding_id}: invalid decision subject")
                elif (
                    isinstance(findings.get(decision_subject), dict)
                    and findings[decision_subject].get("item") != finding.get("item")
                ):
                    errors.append(
                        f"{finding_id}: decision subject inventory item mismatch"
                    )
        decision_annotations = finding.get("decision_annotations", [])
        if not isinstance(decision_annotations, list):
            errors.append(f"{finding_id}: decision_annotations must be an array")
        else:
            if len(decision_annotations) > 1:
                errors.append(f"{finding_id}: multiple decision annotations")
            for index, annotation in enumerate(decision_annotations, start=1):
                if not isinstance(annotation, dict):
                    errors.append(
                        f"{finding_id}: decision annotation {index} must be an object"
                    )
                    continue
                if finding.get("status") != "needs_decision":
                    errors.append(
                        f"{finding_id}: decision annotation requires needs_decision"
                    )
                if not isinstance(decision_for, dict):
                    errors.append(
                        f"{finding_id}: decision annotation requires decision relation"
                    )
                problem = artifact_error(
                    annotation.get("evidence"),
                    f"{finding_id} decision annotation {index}",
                    DECISION_MARKERS,
                )
                if problem:
                    errors.append(problem)
                    continue
                evidence = annotation["evidence"]
                decision_digests.append(evidence["sha256"])
                try:
                    declared = declared_text(evidence, "RESOLVES:")
                    expected = (
                        f"{finding_id} {decision_for['stage']}:"
                        f"{decision_for['subject']}:{decision_for['iteration']}"
                    )
                except (KeyError, OSError, TypeError, ValueError) as exc:
                    errors.append(f"{finding_id}: decision declaration: {exc}")
                else:
                    if declared != expected:
                        errors.append(
                            f"{finding_id}: decision resolves {declared}, "
                            f"expected {expected}"
                        )

    all_reviews = []
    for finding in findings.values():
        if not isinstance(finding, dict):
            continue
        reviews = finding.get("reviews", [])
        if isinstance(reviews, list):
            all_reviews.extend(review for review in reviews if isinstance(review, dict))
    integration_reviews = state.get("integration_reviews")
    if not isinstance(integration_reviews, list):
        errors.append("integration_reviews must be an array")
    else:
        for index, review in enumerate(integration_reviews, start=1):
            if not isinstance(review, dict):
                errors.append(f"integration review {index} must be an object")
                continue
            if schema_version >= 3 and review.get("iteration") != index:
                errors.append(f"integration review {index}: iteration mismatch")
            if not re.fullmatch(
                r"agent:[A-Za-z0-9_./-]{3,}",
                str(review.get("reviewer", "")),
            ):
                errors.append(f"integration review {index}: invalid reviewer identity")
            integration_verdict = review.get("verdict")
            if not isinstance(integration_verdict, str) or integration_verdict not in {
                "accepted",
                "rejected",
            }:
                errors.append(f"integration review {index}: invalid verdict")
            if integration_verdict == "rejected" and not (
                isinstance(review.get("blocker"), str)
                and review["blocker"].strip()
            ):
                errors.append(f"integration review {index}: blocker missing")
            problem = artifact_error(
                review.get("evidence"),
                f"integration review {index}",
                review_markers("integration", schema_version),
            )
            if problem:
                errors.append(problem)
            elif isinstance(integration_verdict, str) and integration_verdict in {
                "accepted",
                "rejected",
            }:
                problem = declaration_error(
                    review["evidence"],
                    "integration",
                    review["verdict"],
                    f"integration review {index}",
                )
                if problem:
                    errors.append(problem)
                problem = control_marker_error(
                    review["evidence"],
                    "integration",
                    f"integration review {index}",
                )
                if problem:
                    errors.append(problem)
                if schema_version >= 3:
                    iteration = review.get("iteration")
                    key = target_key("integration", "ALL", iteration)
                    registered = review_targets.get(key)
                    if not isinstance(registered, dict):
                        errors.append(
                            f"integration review {index}: frozen target missing"
                        )
                    elif review.get("target") != registered.get("bundle"):
                        errors.append(
                            f"integration review {index}: target does not match freeze"
                        )
                    else:
                        problem = target_bundle_error(
                            review.get("target"),
                            "integration",
                            "ALL",
                            iteration,
                            f"integration review {index} target",
                        )
                        if problem:
                            errors.append(problem)
                        else:
                            try:
                                declared = declared_text(
                                    review["evidence"],
                                    "TARGET_ARTIFACT:",
                                )
                                expected = target_declaration(review["target"])
                            except (
                                KeyError,
                                OSError,
                                TypeError,
                                ValueError,
                            ) as exc:
                                errors.append(
                                    f"integration review {index} target: {exc}"
                                )
                            else:
                                if declared != expected:
                                    errors.append(
                                        f"integration review {index}: "
                                        "target declaration mismatch"
                                    )
        all_reviews.extend(
            review for review in integration_reviews if isinstance(review, dict)
        )
        expected_run_status = "active"
        if integration_reviews and isinstance(integration_reviews[-1], dict):
            last = integration_reviews[-1]
            if last.get("verdict") == "accepted":
                expected_run_status = "complete"
            elif last.get("verdict") == "rejected":
                blocker = last.get("blocker")
                repeated = (
                    sum(
                        1
                        for review in integration_reviews
                        if isinstance(review, dict)
                        and review.get("verdict") == "rejected"
                        and review.get("blocker") == blocker
                    )
                    if isinstance(blocker, str) and blocker.strip()
                    else 0
                )
                if repeated >= 2 or len(integration_reviews) >= INTEGRATION_HARD_LIMIT:
                    expected_run_status = "documented_blocked"
        if state.get("status") != expected_run_status:
            errors.append(
                f"run status {state.get('status')} does not match integration history "
                f"{expected_run_status}"
            )
    format_failures = state.get("format_failures", [])
    valid_format_failures = []
    if not isinstance(format_failures, list):
        errors.append("format_failures must be an array")
    else:
        for index, failure in enumerate(format_failures, start=1):
            if not isinstance(failure, dict):
                errors.append(f"format failure {index} must be an object")
                continue
            valid_format_failures.append(failure)
            stage = failure.get("stage")
            finding_id = failure.get("finding_id")
            iteration = failure.get("iteration")
            reviewer = failure.get("reviewer")
            if not isinstance(stage, str) or stage not in {
                "confirmation",
                "plan",
                "fix",
                "integration",
            }:
                errors.append(f"format failure {index}: invalid stage")
                continue
            if not isinstance(finding_id, str) or not finding_id:
                errors.append(f"format failure {index}: invalid finding")
                continue
            if not isinstance(iteration, int) or iteration < 1:
                errors.append(f"format failure {index}: invalid iteration")
                continue
            if not isinstance(reviewer, str) or not re.fullmatch(
                r"agent:[A-Za-z0-9_./-]{3,}",
                reviewer,
            ):
                errors.append(f"format failure {index}: invalid reviewer")
            if not str(failure.get("reason", "")).strip():
                errors.append(f"format failure {index}: reason missing")
            problem = raw_artifact_error(
                failure.get("evidence"),
                f"format failure {index}",
            )
            if problem:
                errors.append(problem)
            problem = target_bundle_error(
                failure.get("target"),
                stage,
                finding_id,
                iteration,
                f"format failure {index} target",
            )
            if problem:
                errors.append(problem)
            key = target_key(stage, finding_id, iteration)
            record = review_targets.get(key)
            registered = []
            if isinstance(record, dict):
                if isinstance(record.get("bundle"), dict):
                    registered.append(record["bundle"])
                registered.extend(
                    old.get("bundle")
                    for old in record.get("superseded", [])
                    if isinstance(old, dict) and isinstance(old.get("bundle"), dict)
                )
            if failure.get("target") not in registered:
                errors.append(
                    f"format failure {index}: target does not match frozen history"
                )
    reviewers = [review.get("reviewer") for review in all_reviews] + [
        failure.get("reviewer") for failure in valid_format_failures
    ]
    valid_reviewers = [value for value in reviewers if isinstance(value, str)]
    if len(valid_reviewers) != len(set(valid_reviewers)):
        errors.append("reviewer identity reused in run")
    digests = [
        review.get("evidence", {}).get("sha256")
        for review in all_reviews
        if isinstance(review.get("evidence"), dict)
        and isinstance(review.get("evidence", {}).get("sha256"), str)
    ]
    format_digests = [
        failure.get("evidence", {}).get("sha256")
        for failure in valid_format_failures
        if isinstance(failure.get("evidence"), dict)
        and isinstance(failure.get("evidence", {}).get("sha256"), str)
    ]
    digests.extend(format_digests)
    if len(digests) != len(set(digests)):
        errors.append("review evidence artifact reused in run")
    if set(digests) & set(target_digests):
        errors.append("review evidence reused as a frozen target bundle")
    spec_digests = [
        finding.get("spec", {}).get("sha256")
        for finding in findings.values()
        if isinstance(finding, dict)
        and isinstance(finding.get("spec"), dict)
        and isinstance(finding.get("spec", {}).get("sha256"), str)
    ]
    if len(spec_digests) != len(set(spec_digests)):
        errors.append("bug spec artifact reused in run")
    if len(resolution_digests) != len(set(resolution_digests)):
        errors.append("resolution evidence artifact reused in run")
    if len(decision_digests) != len(set(decision_digests)):
        errors.append("decision evidence artifact reused in run")
    coverage_digests = {
        item.get("evidence", {}).get("sha256")
        for item in coverage.values()
        if isinstance(item, dict)
        and isinstance(item.get("evidence"), dict)
        and isinstance(item.get("evidence", {}).get("sha256"), str)
    }
    if set(resolution_digests) & (
        set(digests) | set(spec_digests) | coverage_digests | set(target_digests)
    ):
        errors.append(
            "resolution evidence reused as coverage, review, spec, or target artifact"
        )
    if set(decision_digests) & (
        set(digests)
        | set(spec_digests)
        | set(resolution_digests)
        | coverage_digests
        | set(target_digests)
    ):
        errors.append(
            "decision evidence reused as coverage, review, resolution, spec, or target"
        )

    complete_gate = require_complete or state.get("status") == "complete"
    if complete_gate:
        if (
            not isinstance(integration_reviews, list)
            or not integration_reviews
            or not isinstance(integration_reviews[-1], dict)
            or integration_reviews[-1].get("verdict") != "accepted"
        ):
            errors.append("complete review requires a final accepted integration")
        unresolved_relations = []
        unapplied_relations = []
        for finding_id, finding in findings.items():
            if not isinstance(finding, dict) or not isinstance(
                finding.get("decision_for"), dict
            ):
                continue
            resolution = decision_resolution_evidence(finding, state.get("mode"))
            if resolution == {}:
                unresolved_relations.append(finding_id)
            elif isinstance(resolution, dict) and schema_version >= 3:
                decision_for = finding["decision_for"]
                target_finding = (
                    "ALL"
                    if decision_for["stage"] == "integration"
                    else decision_for["subject"]
                )
                key = target_key(
                    decision_for["stage"],
                    target_finding,
                    decision_for["iteration"],
                )
                record = review_targets.get(key)
                if not isinstance(record, dict) or finding_id not in record.get(
                    "applied_decisions",
                    [],
                ):
                    unapplied_relations.append(finding_id)
        if unresolved_relations:
            errors.append(
                "unresolved linked decisions: "
                + ", ".join(sorted(unresolved_relations))
            )
        if unapplied_relations:
            errors.append(
                "decision evidence not applied to target: "
                + ", ".join(sorted(unapplied_relations))
            )
        if not state.get("coverage_frozen"):
            errors.append("coverage inventory is not frozen")
        incomplete_coverage = [
            item_id
            for item_id, item in coverage.items()
            if isinstance(item, dict)
            if not isinstance(item.get("status"), str)
            or item.get("status") not in {"covered", "skipped"}
        ]
        if incomplete_coverage:
            errors.append("incomplete coverage: " + ", ".join(sorted(incomplete_coverage)))
        if not coverage:
            errors.append("coverage inventory is empty")
        if coverage and not any(
            isinstance(item, dict) and item.get("status") == "covered"
            for item in coverage.values()
        ):
            errors.append("coverage inventory has no covered item")
        for finding_id, finding in findings.items():
            if (
                not isinstance(finding, dict)
                or not isinstance(finding.get("status"), str)
                or finding.get("status") not in FINDING_STATUSES
            ):
                continue
            status = finding["status"]
            if state.get("mode") == "repair":
                allowed = TERMINAL_NON_BUG | {"accepted"}
            else:
                allowed = TERMINAL_NON_BUG | {"ready", "documented_blocked"}
            if status not in allowed:
                errors.append(f"{finding_id}: non-terminal status {status}")
            if status in {"confirmed_bug", "ready", "accepted", "documented_blocked"}:
                problem = artifact_error(
                    finding.get("spec"),
                    f"{finding_id} spec",
                    SPEC_MARKERS,
                )
                if problem:
                    errors.append(problem)
    if isinstance(integration_reviews, list) and integration_reviews:
        last_integration = integration_reviews[-1]
        if (
            isinstance(last_integration, dict)
            and last_integration.get("verdict") == "accepted"
            and state.get("status") != "complete"
        ):
            errors.append("accepted integration requires complete run status")
    if state.get("status") == "complete" and (
        not isinstance(integration_reviews, list)
        or not integration_reviews
        or not isinstance(integration_reviews[-1], dict)
        or integration_reviews[-1].get("verdict") != "accepted"
    ):
        errors.append("complete run lacks final accepted integration")
    return errors


def require_finding(state: dict, finding_id: str) -> dict:
    try:
        return state["findings"][finding_id]
    except KeyError as exc:
        raise ValueError(f"unknown finding: {finding_id}") from exc


def require_active(state: dict) -> None:
    if state.get("status") != "active":
        raise ValueError("review state is terminal and immutable")


def decision_resolution_evidence(finding: dict, mode: str) -> dict | None:
    status = finding.get("status")
    if not isinstance(status, str):
        return {}
    if status in {"not_a_bug", "duplicate"}:
        return None
    if status == "needs_decision":
        decision_annotations = finding.get("decision_annotations", [])
        if isinstance(decision_annotations, list) and decision_annotations:
            return decision_annotations[0].get("evidence")
        resolution_annotations = finding.get("resolution_annotations", [])
        if isinstance(resolution_annotations, list) and resolution_annotations:
            return resolution_annotations[0].get("evidence")
        return {}
    if status == "accepted":
        reviews = finding.get("reviews", [])
        accepted = [
            review
            for review in reviews
            if isinstance(review, dict)
            and review.get("stage") == "fix"
            and review.get("verdict") == "accepted"
        ]
        return accepted[-1].get("evidence") if accepted else {}
    if mode == "audit" and status == "ready":
        reviews = finding.get("reviews", [])
        accepted = [
            review
            for review in reviews
            if isinstance(review, dict)
            and review.get("stage") == "plan"
            and review.get("verdict") == "accepted"
        ]
        return accepted[-1].get("evidence") if accepted else {}
    return {}


def gate_decision_requirements(
    state: dict,
    stage: str,
    subject: str,
    iteration: int,
) -> tuple[list[str], dict[str, list[dict]]]:
    unresolved = []
    required = {}
    for finding_id, finding in state["findings"].items():
        if not isinstance(finding, dict):
            continue
        decision_for = finding.get("decision_for")
        if not isinstance(decision_for, dict) or decision_for != {
            "stage": stage,
            "subject": subject,
            "iteration": iteration,
        }:
            continue
        resolution = decision_resolution_evidence(finding, state["mode"])
        if resolution == {}:
            unresolved.append(finding_id)
            continue
        if resolution is None:
            continue
        confirmations = [
            review
            for review in finding.get("reviews", [])
            if isinstance(review, dict) and review.get("stage") == "confirmation"
        ]
        if not confirmations or not isinstance(resolution, dict):
            unresolved.append(finding_id)
            continue
        required[finding_id] = [confirmations[-1]["evidence"], resolution]
    return unresolved, required


def require_gate_ready(
    state: dict,
    stage: str,
    subject: str,
    iteration: int,
) -> dict[str, list[dict]]:
    unresolved, required = gate_decision_requirements(
        state,
        stage,
        subject,
        iteration,
    )
    if unresolved:
        raise ValueError(
            f"{stage}:{subject} has unresolved decisions: {', '.join(sorted(unresolved))}"
        )
    return required


def require_frozen_target(
    state: dict,
    stage: str,
    finding_id: str,
    iteration: int,
) -> dict[str, str]:
    if state.get("schema_version") < 3:
        raise ValueError("legacy v2 ledgers are read-only for review gates")
    key = target_key(stage, finding_id, iteration)
    try:
        record = state["review_targets"][key]
        bundle = record["bundle"]
    except (KeyError, TypeError) as exc:
        raise ValueError(f"freeze the exact review target first: {key}") from exc
    problem = target_bundle_error(
        bundle,
        stage,
        finding_id,
        iteration,
        f"review target {key}",
    )
    if problem:
        raise ValueError(problem)
    gate_subject = "RUN" if stage == "integration" else finding_id
    requirements = require_gate_ready(
        state,
        stage,
        gate_subject,
        iteration,
    )
    if set(record.get("applied_decisions", [])) != set(requirements):
        raise ValueError(
            f"frozen target {key} does not include the current decision evidence"
        )
    return bundle


def persist_format_failure(
    path: Path,
    state: dict,
    *,
    stage: str,
    finding_id: str,
    iteration: int,
    reviewer: str,
    evidence: dict[str, str],
    target: dict[str, str],
    reason: str,
) -> None:
    used_digests = {
        review.get("evidence", {}).get("sha256")
        for finding in state["findings"].values()
        for review in finding.get("reviews", [])
    } | {
        review.get("evidence", {}).get("sha256")
        for review in state["integration_reviews"]
    } | {
        failure.get("evidence", {}).get("sha256")
        for failure in state.get("format_failures", [])
        if isinstance(failure, dict)
    }
    if evidence["sha256"] in used_digests:
        raise ValueError("malformed response artifact already used in this run")
    state.setdefault("format_failures", []).append(
        {
            "stage": stage,
            "finding_id": finding_id,
            "iteration": iteration,
            "reviewer": reviewer,
            "evidence": evidence,
            "target": target,
            "reason": reason,
            "at": now(),
        }
    )
    errors = validate(state)
    if errors:
        raise ValueError("; ".join(errors))
    save(path, state, "review-format-failed")


def add_review(
    finding: dict,
    stage: str,
    verdict: str,
    reviewer: str,
    evidence: dict[str, str],
    target: dict[str, str],
    blocker: str | None,
    limit: int,
) -> tuple[int, int]:
    reviewer = reviewer.strip()
    if not re.fullmatch(r"agent:[A-Za-z0-9_./-]{3,}", reviewer):
        raise ValueError("reviewer must be an actual Codex task path prefixed with agent:")
    count = finding["iterations"][stage] + 1
    if count > min(limit, STAGE_HARD_LIMITS[stage]):
        raise ValueError(f"{stage} iteration limit reached")
    finding["iterations"][stage] = count
    finding["reviews"].append(
        {
            "stage": stage,
            "iteration": count,
            "verdict": verdict,
            "reviewer": reviewer,
            "evidence": evidence,
            "target": target,
            "blocker": blocker,
            "at": now(),
        }
    )
    repeated = sum(
        1
        for review in finding["reviews"]
        if review["stage"] == stage
        and review["verdict"] in {"rejected", "inconclusive"}
        and review.get("blocker") == blocker
    )
    return count, repeated


def cmd_init(args: argparse.Namespace) -> None:
    path = Path(args.state)
    if path.exists():
        raise ValueError(f"state already exists: {path}")
    trajectory = Path(f"{path}.events.jsonl")
    if trajectory.exists():
        raise ValueError(f"trajectory already exists without state: {trajectory}")
    save(path, new_state(args.runtime, args.mode, args.max_iterations), "init")


def cmd_coverage(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load(path)
    require_active(state)
    existing = state["coverage"].get(args.item, {})
    risk = getattr(args, "risk", None) or existing.get("risk", "medium")
    priority = getattr(args, "priority", None)
    if priority is None:
        priority = existing.get("priority", 100)
    if state["coverage_frozen"] and args.item not in state["coverage"]:
        raise ValueError("coverage inventory is frozen")
    if (
        state["coverage_frozen"]
        and state["coverage"][args.item].get("lane") != args.lane
    ):
        raise ValueError("cannot change lane after coverage freeze")
    if state["coverage_frozen"] and (
        existing.get("risk") != risk or existing.get("priority") != priority
    ):
        raise ValueError("cannot change risk or priority after coverage freeze")
    evidence = None
    if args.status in {"covered", "skipped", "blocked"}:
        if not args.evidence_file:
            raise ValueError("terminal coverage requires --evidence-file")
        markers = {
            "covered": COVERED_MARKERS,
            "skipped": ("SKIPPED:", "REASON:"),
            "blocked": ("BLOCKED:", "MISSING:"),
        }[args.status]
        evidence = artifact(args.evidence_file, markers)
        evidence_text = Path(evidence["path"]).read_text(
            encoding="utf-8",
            errors="replace",
        )
        item_text = (
            evidence_section(evidence_text, "COVERED:")
            if args.status == "covered"
            else evidence_text
        )
        if not evidence_names_item(item_text, args.item):
            raise ValueError("coverage evidence must name its inventory item")
    state["coverage"][args.item] = {
        "lane": args.lane,
        "risk": risk,
        "priority": priority,
        "status": args.status,
        "evidence": evidence,
        "updated_at": now(),
    }
    errors = validate(state)
    if errors:
        raise ValueError("; ".join(errors))
    save(path, state, "coverage")


def cmd_freeze_coverage(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load(path)
    require_active(state)
    if not state["coverage"]:
        raise ValueError("coverage inventory is empty")
    manifest = artifact(
        args.manifest_file,
        ("REPOSITORY:", "COMMIT:", "INVENTORY:"),
    )
    manifest_ids = manifest_inventory(manifest)
    if manifest_ids != set(state["coverage"]):
        raise ValueError("manifest inventory IDs must exactly match registered coverage IDs")
    state["inventory_manifest"] = manifest
    state["coverage_frozen"] = True
    errors = validate(state)
    if errors:
        raise ValueError("; ".join(errors))
    save(path, state, "coverage-frozen")


def persist_target_bundle(path: Path, payload: dict) -> dict[str, str]:
    encoded = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    bundle_dir = Path(f"{path}.targets")
    bundle_dir.mkdir(parents=True, exist_ok=True)
    bundle_name = hashlib.sha256(encoded).hexdigest() + ".json"
    bundle_path = bundle_dir / bundle_name
    if bundle_path.exists():
        existing = artifact(str(bundle_path))
        if existing["sha256"] == hashlib.sha256(encoded).hexdigest():
            return existing
        raise ValueError(f"frozen target bundle collision: {bundle_path}")
    fd, temp_name = tempfile.mkstemp(prefix=f".{bundle_name}.", dir=bundle_dir)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temp_name, bundle_path)
        os.unlink(temp_name)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise
    return artifact(str(bundle_path))


def cmd_freeze_target(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load(path)
    require_active(state)
    if state.get("schema_version") < 3:
        raise ValueError("legacy v2 ledgers are read-only for review gates")
    if not state.get("coverage_frozen"):
        raise ValueError("freeze coverage before review targets")
    stage = args.stage
    finding_id = args.id
    if stage == "integration":
        if finding_id != "ALL":
            raise ValueError("integration target requires --id ALL")
        iteration = len(state["integration_reviews"]) + 1
        if iteration > INTEGRATION_HARD_LIMIT:
            raise ValueError("integration review iteration limit reached")
    else:
        finding = require_finding(state, finding_id)
        required_status = {
            "confirmation": "suspected",
            "plan": "confirmed_bug",
            "fix": "implementing",
        }[stage]
        if finding["status"] != required_status:
            raise ValueError(
                f"{stage} target requires {required_status}, found {finding['status']}"
            )
        if stage == "plan" and not finding.get("spec"):
            raise ValueError("document the confirmed bug before freezing the plan target")
        if stage == "fix" and state["mode"] != "repair":
            raise ValueError("fix target requires repair mode")
        iteration = finding["iterations"][stage] + 1
        if iteration > min(state["max_iterations"], STAGE_HARD_LIMITS[stage]):
            raise ValueError(f"{stage} iteration limit reached")
    key = target_key(stage, finding_id, iteration)
    if key in state["review_targets"]:
        raise ValueError(f"review target already frozen: {key}")
    gate_subject = "RUN" if stage == "integration" else finding_id
    decision_requirements = require_gate_ready(
        state,
        stage,
        gate_subject,
        iteration,
    )
    if not args.artifact_file:
        raise ValueError("freeze-target requires at least one --artifact-file")
    artifacts = []
    seen_paths = set()
    for path_value in args.artifact_file:
        source = Path(path_value).expanduser().resolve()
        if not source.is_file():
            raise ValueError(f"target artifact does not exist: {source}")
        data = source.read_bytes()
        if len(data.strip()) < 32:
            raise ValueError(f"target artifact is too small: {source}")
        source_path = str(source)
        if source_path in seen_paths:
            raise ValueError("target artifact path repeated")
        seen_paths.add(source_path)
        artifacts.append(
            {
                "path": source_path,
                "sha256": hashlib.sha256(data).hexdigest(),
                "content_base64": base64.b64encode(data).decode("ascii"),
            }
        )
    artifact_digests = {item["sha256"] for item in artifacts}
    for decision_id, evidence_values in decision_requirements.items():
        required_digests = {
            value.get("sha256")
            for value in evidence_values
            if isinstance(value, dict)
        }
        if len(required_digests) != len(evidence_values) or not required_digests <= artifact_digests:
            raise ValueError(
                f"target must include decision evidence for {decision_id}"
            )
    payload = {
        "review_stage": stage,
        "finding_id": finding_id,
        "iteration": iteration,
        "artifacts": artifacts,
    }
    bundle = persist_target_bundle(path, payload)
    state["review_targets"][key] = {
        "stage": stage,
        "finding_id": finding_id,
        "iteration": iteration,
        "bundle": bundle,
        "applied_decisions": sorted(decision_requirements),
        "superseded": [],
        "frozen_at": now(),
    }
    errors = validate(state)
    if errors:
        raise ValueError("; ".join(errors))
    save(path, state, "review-target-frozen")


def cmd_supersede_target(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load(path)
    require_active(state)
    if state.get("schema_version") < 3:
        raise ValueError("legacy v2 ledgers are read-only for review gates")
    stage = args.stage
    finding_id = args.id
    if stage == "integration":
        if finding_id != "ALL":
            raise ValueError("integration target requires --id ALL")
        iteration = len(state["integration_reviews"]) + 1
        gate_subject = "RUN"
    else:
        finding = require_finding(state, finding_id)
        iteration = finding["iterations"][stage] + 1
        gate_subject = finding_id
    key = target_key(stage, finding_id, iteration)
    try:
        record = state["review_targets"][key]
    except KeyError as exc:
        raise ValueError(f"no unconsumed frozen target for {key}") from exc
    if args.decision_id in record.get("applied_decisions", []):
        raise ValueError("decision already applied to this target")
    decision = require_finding(state, args.decision_id)
    if decision.get("decision_for") != {
        "stage": stage,
        "subject": gate_subject,
        "iteration": iteration,
    }:
        raise ValueError("decision candidate does not link to this exact gate")
    requirements = require_gate_ready(
        state,
        stage,
        gate_subject,
        iteration,
    )
    evidence_values = requirements.get(args.decision_id)
    if not evidence_values:
        raise ValueError("decision does not require an evidence-bearing supersession")
    old_bundle = record["bundle"]
    problem = target_bundle_error(
        old_bundle,
        stage,
        finding_id,
        iteration,
        f"review target {key}",
    )
    if problem:
        raise ValueError(problem)
    old_payload = json.loads(Path(old_bundle["path"]).read_text(encoding="utf-8"))
    artifacts = [dict(item) for item in old_payload["artifacts"]]
    seen_paths = {item["path"] for item in artifacts}
    for evidence in evidence_values:
        source_path = evidence["path"]
        if source_path in seen_paths:
            raise ValueError("decision evidence already exists in the active target")
        data = Path(source_path).read_bytes()
        if hashlib.sha256(data).hexdigest() != evidence["sha256"]:
            raise ValueError("decision evidence digest changed")
        seen_paths.add(source_path)
        artifacts.append(
            {
                "path": source_path,
                "sha256": evidence["sha256"],
                "content_base64": base64.b64encode(data).decode("ascii"),
            }
        )
    payload = {
        "review_stage": stage,
        "finding_id": finding_id,
        "iteration": iteration,
        "artifacts": artifacts,
        "supersedes": old_bundle["sha256"],
        "decision_id": args.decision_id,
    }
    bundle = persist_target_bundle(path, payload)
    record.setdefault("superseded", []).append(
        {
            "bundle": old_bundle,
            "decision_id": args.decision_id,
            "superseded_at": now(),
        }
    )
    record["bundle"] = bundle
    record.setdefault("applied_decisions", []).append(args.decision_id)
    record["applied_decisions"] = sorted(set(record["applied_decisions"]))
    errors = validate(state)
    if errors:
        raise ValueError("; ".join(errors))
    save(path, state, "review-target-superseded")


def cmd_add(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load(path)
    require_active(state)
    if not state["coverage_frozen"]:
        raise ValueError("freeze coverage before adding candidates")
    if args.item not in state["coverage"]:
        raise ValueError(f"unknown coverage item: {args.item}")
    if args.id in state["findings"]:
        raise ValueError(f"finding already exists: {args.id}")
    decision_stage = getattr(args, "decision_for_stage", None)
    decision_subject = getattr(args, "decision_for_subject", None)
    if bool(decision_stage) != bool(decision_subject):
        raise ValueError("decision relation requires both stage and subject")
    if decision_stage:
        if decision_stage == "integration":
            if decision_subject != "RUN":
                raise ValueError("integration decision subject must be RUN")
            decision_iteration = len(state["integration_reviews"]) + 1
        else:
            subject = require_finding(state, decision_subject)
            if decision_subject == args.id:
                raise ValueError("decision candidate cannot target itself")
            if subject.get("item") != args.item:
                raise ValueError("decision candidate must use the subject inventory item")
            required_status = {
                "plan": "confirmed_bug",
                "fix": "implementing",
            }[decision_stage]
            if subject.get("status") != required_status:
                raise ValueError(
                    f"{decision_stage} decision requires {required_status}"
                )
            decision_iteration = subject["iterations"][decision_stage] + 1
    else:
        decision_iteration = None
    state["findings"][args.id] = {
        "title": args.title,
        "item": args.item,
        "lane": state["coverage"][args.item]["lane"],
        "status": "suspected",
        "iterations": {"confirmation": 0, "plan": 0, "fix": 0},
        "reviews": [],
        "resolution_annotations": [],
        "decision_annotations": [],
        "decision_for": (
            {
                "stage": decision_stage,
                "subject": decision_subject,
                "iteration": decision_iteration,
            }
            if decision_stage
            else None
        ),
        "created_at": now(),
    }
    save(path, state, "candidate-added")


def cmd_review(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load(path)
    require_active(state)
    finding = require_finding(state, args.id)
    allowed = {
        "confirmation": {"confirmed", "inconclusive", "not-a-bug", "needs-decision", "duplicate"},
        "plan": {"accepted", "rejected"},
        "fix": {"accepted", "rejected"},
    }[args.stage]
    if args.verdict not in allowed:
        raise ValueError(f"invalid {args.stage} verdict: {args.verdict}")
    blocker = args.blocker.strip() if args.blocker else None
    if args.verdict in {"rejected", "inconclusive"} and not blocker:
        raise ValueError("rejected or inconclusive review requires --blocker")
    required_status = {
        "confirmation": "suspected",
        "plan": "confirmed_bug",
        "fix": "implementing",
    }[args.stage]
    if finding["status"] != required_status:
        raise ValueError(
            f"{args.stage} review requires {required_status}, found {finding['status']}"
        )
    if args.stage == "plan" and not finding.get("spec"):
        raise ValueError("document the confirmed bug before plan review")
    if args.stage == "fix" and state["mode"] != "repair":
        raise ValueError("fix review requires repair mode")
    reviewer = args.reviewer.strip()
    used_reviews = [
        review
        for value in state["findings"].values()
        for review in value.get("reviews", [])
    ] + state["integration_reviews"]
    used_reviewers = {review.get("reviewer") for review in used_reviews} | {
        failure.get("reviewer")
        for failure in state.get("format_failures", [])
        if isinstance(failure, dict)
    }
    if reviewer in used_reviewers:
        raise ValueError(f"reviewer already used in this run: {reviewer}")
    iteration = finding["iterations"][args.stage] + 1
    target = require_frozen_target(state, args.stage, args.id, iteration)
    evidence = raw_artifact(args.evidence_file)
    label = f"{args.id} {args.stage} review"
    problem = artifact_error(
        evidence,
        label,
        review_markers(args.stage, state["schema_version"]),
    )
    if not problem:
        problem = declaration_error(
            evidence,
            args.stage,
            args.verdict,
            label,
        )
    if not problem:
        problem = control_marker_error(evidence, args.stage, label)
    if not problem:
        try:
            matches_target = (
                declared_text(evidence, "TARGET_ARTIFACT:")
                == target_declaration(target)
            )
        except (KeyError, OSError, TypeError, ValueError) as exc:
            problem = f"{label}: {exc}"
        else:
            if not matches_target:
                problem = "review TARGET_ARTIFACT does not match the frozen target"
    if problem:
        persist_format_failure(
            path,
            state,
            stage=args.stage,
            finding_id=args.id,
            iteration=iteration,
            reviewer=reviewer,
            evidence=evidence,
            target=target,
            reason=problem,
        )
        raise ValueError(problem)
    if evidence["sha256"] in {
        review.get("evidence", {}).get("sha256") for review in used_reviews
    } | {
        failure.get("evidence", {}).get("sha256")
        for failure in state.get("format_failures", [])
        if isinstance(failure, dict)
    }:
        raise ValueError("review evidence artifact already used in this run")
    if evidence["sha256"] in {
        record.get("bundle", {}).get("sha256")
        for record in state["review_targets"].values()
        if isinstance(record, dict)
    }:
        raise ValueError("review evidence cannot reuse a frozen target bundle")
    count, repeated = add_review(
        finding,
        args.stage,
        args.verdict,
        reviewer,
        evidence,
        target,
        blocker,
        state["max_iterations"],
    )
    if args.stage == "confirmation":
        if args.verdict == "inconclusive":
            finding["status"] = (
                "needs_decision"
                if repeated >= 2
                or count
                >= min(
                    state["max_iterations"],
                    STAGE_HARD_LIMITS["confirmation"],
                )
                else "suspected"
            )
        else:
            finding["status"] = {
                "confirmed": "confirmed_bug",
                "not-a-bug": "not_a_bug",
                "needs-decision": "needs_decision",
                "duplicate": "duplicate",
            }[args.verdict]
    elif args.stage == "plan":
        if args.verdict == "accepted":
            finding["status"] = "ready"
        elif repeated >= 2 or count >= min(state["max_iterations"], STAGE_HARD_LIMITS["plan"]):
            finding["status"] = "documented_blocked"
        else:
            finding["status"] = "confirmed_bug"
    else:
        if args.verdict == "accepted":
            finding["status"] = "accepted"
        elif repeated >= 2 or count >= min(state["max_iterations"], STAGE_HARD_LIMITS["fix"]):
            finding["status"] = "documented_blocked"
        else:
            finding["status"] = "implementing"
    save(path, state, f"{args.stage}-review")


def cmd_document(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load(path)
    require_active(state)
    finding = require_finding(state, args.id)
    if finding["status"] not in {
        "confirmed_bug",
        "documented_blocked",
    }:
        raise ValueError("document immediately after confirmation or a blocked plan")
    spec = artifact(args.spec, SPEC_MARKERS)
    if spec["sha256"] in {
        value.get("spec", {}).get("sha256")
        for key, value in state["findings"].items()
        if key != args.id and isinstance(value.get("spec"), dict)
    }:
        raise ValueError("bug spec artifact already used by another finding")
    finding["spec"] = spec
    finding.setdefault("notes", []).append({"at": now(), "note": args.note})
    save(path, state, "bug-documented")


def cmd_mark(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load(path)
    require_active(state)
    finding = require_finding(state, args.id)
    if args.status != "implementing":
        raise ValueError("mark status must be implementing")
    if state["mode"] != "repair":
        raise ValueError("implementation requires repair mode")
    if finding["status"] != "ready":
        raise ValueError("implementing requires ready")
    finding["status"] = args.status
    finding["implementation_started"] = {"at": now(), "note": args.note}
    finding.setdefault("notes", []).append({"at": now(), "note": args.note})
    save(path, state, "implementation-started")


def cmd_annotate_resolution(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load(path)
    require_active(state)
    if state["mode"] != "repair":
        raise ValueError("resolution annotation requires repair mode")
    finding = require_finding(state, args.id)
    resolver = require_finding(state, args.resolved_by)
    if args.id == args.resolved_by:
        raise ValueError("a finding cannot resolve itself")
    if finding["status"] != "needs_decision":
        raise ValueError("resolution annotation requires needs_decision")
    if resolver["status"] != "accepted":
        raise ValueError("resolved-by finding must have an accepted fix")
    annotations = finding.setdefault("resolution_annotations", [])
    if annotations:
        raise ValueError("finding already has a resolution annotation")
    note = args.note.strip()
    if not note:
        raise ValueError("resolution note is required")
    evidence = artifact(args.evidence_file, RESOLUTION_MARKERS)
    if declared_text(evidence, "RESOLUTION:") != "RELATED_ACCEPTED_FIX":
        raise ValueError("resolution evidence must declare RELATED_ACCEPTED_FIX")
    if declared_text(evidence, "RESOLVED_BY:") != args.resolved_by:
        raise ValueError("resolution evidence RESOLVED_BY does not match --resolved-by")
    used_digests = {
        review.get("evidence", {}).get("sha256")
        for value in state["findings"].values()
        for review in value.get("reviews", [])
    } | {
        value.get("spec", {}).get("sha256")
        for value in state["findings"].values()
        if isinstance(value.get("spec"), dict)
    } | {
        annotation.get("evidence", {}).get("sha256")
        for value in state["findings"].values()
        for annotation in value.get("resolution_annotations", [])
    } | {
        value.get("evidence", {}).get("sha256")
        for value in state["coverage"].values()
        if isinstance(value, dict)
        if isinstance(value.get("evidence"), dict)
    }
    if evidence["sha256"] in used_digests:
        raise ValueError("resolution evidence artifact already used in this run")
    annotations.append(
        {
            "resolved_by": args.resolved_by,
            "evidence": evidence,
            "note": note,
            "at": now(),
        }
    )
    errors = validate(state)
    if errors:
        raise ValueError("; ".join(errors))
    save(path, state, "resolution-annotated")


def cmd_annotate_decision(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load(path)
    require_active(state)
    finding = require_finding(state, args.id)
    decision_for = finding.get("decision_for")
    if not isinstance(decision_for, dict):
        raise ValueError("decision annotation requires a linked decision candidate")
    if finding.get("status") != "needs_decision":
        raise ValueError("decision annotation requires needs_decision")
    annotations = finding.setdefault("decision_annotations", [])
    if annotations:
        raise ValueError("finding already has a decision annotation")
    evidence = artifact(args.evidence_file, DECISION_MARKERS)
    expected = (
        f"{args.id} {decision_for['stage']}:"
        f"{decision_for['subject']}:{decision_for['iteration']}"
    )
    if declared_text(evidence, "RESOLVES:") != expected:
        raise ValueError("decision evidence RESOLVES does not match the linked gate")
    used_digests = {
        review.get("evidence", {}).get("sha256")
        for value in state["findings"].values()
        for review in value.get("reviews", [])
    } | {
        value.get("spec", {}).get("sha256")
        for value in state["findings"].values()
        if isinstance(value.get("spec"), dict)
    } | {
        annotation.get("evidence", {}).get("sha256")
        for value in state["findings"].values()
        for annotation in value.get("resolution_annotations", [])
    } | {
        annotation.get("evidence", {}).get("sha256")
        for value in state["findings"].values()
        for annotation in value.get("decision_annotations", [])
    } | {
        value.get("evidence", {}).get("sha256")
        for value in state["coverage"].values()
        if isinstance(value, dict) and isinstance(value.get("evidence"), dict)
    } | {
        record.get("bundle", {}).get("sha256")
        for record in state.get("review_targets", {}).values()
        if isinstance(record, dict)
    }
    if evidence["sha256"] in used_digests:
        raise ValueError("decision evidence artifact already used in this run")
    annotations.append({"evidence": evidence, "at": now()})
    errors = validate(state)
    if errors:
        raise ValueError("; ".join(errors))
    save(path, state, "decision-annotated")


def cmd_integration(args: argparse.Namespace) -> None:
    path = Path(args.state)
    state = load(path)
    require_active(state)
    reviews = state["integration_reviews"]
    if len(reviews) >= INTEGRATION_HARD_LIMIT:
        raise ValueError("integration review iteration limit reached")
    if args.verdict == "rejected" and (
        not args.blocker or not args.blocker.strip()
    ):
        raise ValueError("rejected integration review requires --blocker")
    reviewer = args.reviewer.strip()
    if not re.fullmatch(r"agent:[A-Za-z0-9_./-]{3,}", reviewer):
        raise ValueError("reviewer must be an actual Codex task path prefixed with agent:")
    used_reviewers = {
        review.get("reviewer")
        for finding in state["findings"].values()
        for review in finding.get("reviews", [])
    } | {review.get("reviewer") for review in state["integration_reviews"]} | {
        failure.get("reviewer")
        for failure in state.get("format_failures", [])
        if isinstance(failure, dict)
    }
    if reviewer in used_reviewers:
        raise ValueError("integration reviewer must be fresh")
    iteration = len(reviews) + 1
    target = require_frozen_target(state, "integration", "ALL", iteration)
    evidence = raw_artifact(args.evidence_file)
    problem = artifact_error(
        evidence,
        "integration review",
        review_markers("integration", state["schema_version"]),
    )
    if not problem:
        problem = declaration_error(
            evidence,
            "integration",
            args.verdict,
            "integration review",
        )
    if not problem:
        problem = control_marker_error(evidence, "integration", "integration review")
    if not problem:
        try:
            matches_target = (
                declared_text(evidence, "TARGET_ARTIFACT:")
                == target_declaration(target)
            )
        except (KeyError, OSError, TypeError, ValueError) as exc:
            problem = f"integration review: {exc}"
        else:
            if not matches_target:
                problem = (
                    "integration TARGET_ARTIFACT does not match the frozen target"
                )
    if problem:
        persist_format_failure(
            path,
            state,
            stage="integration",
            finding_id="ALL",
            iteration=iteration,
            reviewer=reviewer,
            evidence=evidence,
            target=target,
            reason=problem,
        )
        raise ValueError(problem)
    used_digests = {
        review.get("evidence", {}).get("sha256")
        for finding in state["findings"].values()
        for review in finding.get("reviews", [])
    } | {
        review.get("evidence", {}).get("sha256")
        for review in reviews
    } | {
        failure.get("evidence", {}).get("sha256")
        for failure in state.get("format_failures", [])
        if isinstance(failure, dict)
    }
    if evidence["sha256"] in used_digests:
        raise ValueError("review evidence artifact already used in this run")
    if evidence["sha256"] in {
        record.get("bundle", {}).get("sha256")
        for record in state["review_targets"].values()
        if isinstance(record, dict)
    }:
        raise ValueError("review evidence cannot reuse a frozen target bundle")
    reviews.append(
        {
            "iteration": iteration,
            "verdict": args.verdict,
            "reviewer": reviewer,
            "evidence": evidence,
            "target": target,
            "blocker": args.blocker.strip() if args.blocker else None,
            "at": now(),
        }
    )
    if args.verdict == "accepted":
        state["status"] = "complete"
        errors = validate(state, require_complete=True)
        if errors:
            raise ValueError("; ".join(errors))
    else:
        repeated = sum(
            1
            for review in reviews
            if review["verdict"] == "rejected"
            and review.get("blocker") == args.blocker.strip()
        )
        state["status"] = (
            "documented_blocked"
            if repeated >= 2 or len(reviews) >= INTEGRATION_HARD_LIMIT
            else "active"
        )
    save(path, state, "integration-review")


def cmd_validate(args: argparse.Namespace) -> None:
    errors = validate(load(Path(args.state)), require_complete=args.complete)
    if errors:
        raise ValueError("; ".join(errors))
    print("OK")


def summary_payload(state: dict) -> dict:
    return {
        "schema_version": state["schema_version"],
        "target_binding": (
            "required" if state["schema_version"] >= 3 else "legacy_unbound"
        ),
        "runtime": state["runtime"],
        "mode": state["mode"],
        "status": state["status"],
        "coverage": {
            key: {
                "status": value["status"],
                "risk": value["risk"],
                "priority": value["priority"],
            }
            for key, value in sorted(state["coverage"].items())
        },
        "findings": {
            key: {
                "status": value["status"],
                "iterations": value["iterations"],
                "decision_for": value.get("decision_for"),
                "decision_annotated": bool(value.get("decision_annotations", [])),
                "resolved_by": [
                    annotation["resolved_by"]
                    for annotations in (value.get("resolution_annotations", []),)
                    if isinstance(annotations, list)
                    for annotation in annotations
                    if isinstance(annotation, dict)
                    and isinstance(annotation.get("resolved_by"), str)
                ],
            }
            for key, value in sorted(state["findings"].items())
        },
        "format_failures": len(state.get("format_failures", [])),
        "integration_iterations": len(state["integration_reviews"]),
    }


def cmd_summary(args: argparse.Namespace) -> None:
    state = load(Path(args.state))
    errors = validate(state, require_complete=False)
    if errors:
        raise ValueError("; ".join(errors))
    print(json.dumps(summary_payload(state), indent=2, sort_keys=True))


def cmd_self_test(_args: argparse.Namespace) -> None:
    assert evidence_names_item(
        evidence_section("COVERED: symbol:alpha\nPROBES: x", "COVERED:"),
        "symbol:alpha",
    )
    assert not evidence_names_item(
        evidence_section(
            "COVERED: symbol:alphabet\nPROBES: symbol:alpha",
            "COVERED:",
        ),
        "symbol:alpha",
    )
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        path = root / "state.json"
        def write(name: str, content: str) -> Path:
            result = root / f"{name}.md"
            result.write_text(content, encoding="utf-8")
            return result

        files = {
            "manifest": write(
                "manifest",
                "REPOSITORY: /tmp/example\nCOMMIT: deadbeef\nINVENTORY:\n"
                "- symbol:core.functions\n- ui:surface\n",
            ),
            "coverage-core": write(
                "coverage-core",
                "COVERED: symbol:core.functions, symbol:limited, symbol:core, "
                "symbol:core.audit, and symbol:integration with their callers\n"
                "PROBES: boundary, lifecycle, and negative-control probes\n"
                "NEGATIVE_FINDINGS: sibling callers preserved their contract\n"
                "COMMANDS: rg plus targeted test command\n"
                "RESOLUTION: RELATED_ACCEPTED_FIX\nRESOLVED_BY: BUG-001\n"
                "PROOF: deliberately shared artifact for the reuse negative control\n"
                "REMAINING_UNCERTAINTY: none\n",
            ),
            "coverage-ui": write(
                "coverage-ui",
                "SKIPPED: no runnable application\n"
                "REASON: ui:surface intentionally has no UI runtime\n",
            ),
            "confirm": write(
                "confirm",
                "CLASSIFICATION: CONFIRMED_BUG\nREPRODUCTION: deterministic command\n"
                "AUTHORITY: accepted current contract\nNEGATIVE_CONTROL: clean fixture\n"
                "ROOT_CAUSE: shared parser seam\nCOUNTEREVIDENCE: none survived\n",
            ),
            "false-positive": write(
                "false-positive",
                "CLASSIFICATION: NOT_A_BUG\nREPRODUCTION: deterministic command\n"
                "AUTHORITY: accepted current contract\nNEGATIVE_CONTROL: clean fixture\n"
                "ROOT_CAUSE: intended configuration\nCOUNTEREVIDENCE: product setting\n",
            ),
            "ambiguous-confirmation": write(
                "ambiguous-confirmation",
                "CLASSIFICATION: NOT_A_BUG CONFIRMED_BUG\n"
                "REPRODUCTION: deterministic command\n"
                "AUTHORITY: accepted current contract\n"
                "NEGATIVE_CONTROL: clean fixture\n"
                "ROOT_CAUSE: ambiguous controlling value\n"
                "COUNTEREVIDENCE: both outcomes are present\n",
            ),
            "tiny-response": write("tiny-response", "x"),
            "empty-response": write("empty-response", ""),
            "decision": write(
                "decision",
                "CLASSIFICATION: NEEDS_DECISION\nREPRODUCTION: deterministic conflict\n"
                "AUTHORITY: two current contracts conflict\nNEGATIVE_CONTROL: clean fixture\n"
                "ROOT_CAUSE: unresolved contract seam\nCOUNTEREVIDENCE: either may win\n",
            ),
            "user-decision-plan": write(
                "user-decision-plan",
                "DECISION: use the current approved business contract\n"
                "AUTHORITY: explicit current user decision\n"
                "RESOLVES: DEC-PLAN-1 plan:BUG-001:1\n",
            ),
            "user-decision-wrong": write(
                "user-decision-wrong",
                "DECISION: use the current approved business contract\n"
                "AUTHORITY: explicit current user decision\n"
                "RESOLVES: OTHER plan:BUG-001:1\n",
            ),
            "user-decision-plan-2": write(
                "user-decision-plan-2",
                "DECISION: preserve the approved retry invariant\n"
                "AUTHORITY: explicit current user decision\n"
                "RESOLVES: DEC-PLAN-2 plan:BUG-001:1\n",
            ),
            "plan": write(
                "plan",
                "VERDICT: ACCEPTED\nPLAN: patch the shared seam and add RED proof\n"
                "COUNTEREVIDENCE: no smaller correct seam found\n",
            ),
            "plan-contradictory": write(
                "plan-contradictory",
                "CLASSIFICATION: NOT_A_BUG\nVERDICT: ACCEPTED\n"
                "PLAN: patch the shared seam and add RED proof\n"
                "COUNTEREVIDENCE: conflicting controlling marker\n",
            ),
            "fix": write(
                "fix",
                "VERDICT: ACCEPTED\nDIFF: one shared guard\nTESTS: RED then GREEN\n"
                "COUNTEREVIDENCE: sibling paths stayed green\n",
            ),
            "integration": write(
                "integration",
                "VERDICT: ACCEPTED\nCOVERAGE: all manifest IDs covered or skipped\n"
                "PRODUCT_CHECKS: targeted suite and smoke\nINTERACTIONS: no regression\n"
                "REMAINING_UNCERTAINTY: explicitly bounded\n",
            ),
            "spec": write(
                "spec",
                "## Classification\nCONFIRMED_BUG\n## Authority and intent\ncurrent contract\n"
                "## Reproduction\ndeterministic\n## Root cause and scope\nshared seam\n"
                "## Failure-first proof\nRED check\n## Minimal plan\none root fix\n",
            ),
            "resolution": write(
                "resolution",
                "RESOLUTION: RELATED_ACCEPTED_FIX\nRESOLVED_BY: BUG-001\n"
                "PROOF: the accepted shared-seam fix removes the earlier ambiguity\n"
                "REMAINING_UNCERTAINTY: original classification remains historical\n",
            ),
            "resolution-kind-mismatch": write(
                "resolution-kind-mismatch",
                "RESOLUTION: UNRELATED_VALUE\nRESOLVED_BY: BUG-001\n"
                "PROOF: invalid declaration negative control\n"
                "REMAINING_UNCERTAINTY: none\n",
            ),
            "resolution-id-mismatch": write(
                "resolution-id-mismatch",
                "RESOLUTION: RELATED_ACCEPTED_FIX\nRESOLVED_BY: bug-001\n"
                "PROOF: case mismatch negative control\n"
                "REMAINING_UNCERTAINTY: none\n",
            ),
        }

        def freeze(
            stage: str,
            finding_id: str,
            *artifact_names: str | Path,
            state_path: Path | None = None,
        ) -> dict[str, str]:
            ledger_path = state_path or path
            cmd_freeze_target(
                argparse.Namespace(
                    state=str(ledger_path),
                    stage=stage,
                    id=finding_id,
                    artifact_file=[
                        str(files[name] if isinstance(name, str) else name)
                        for name in artifact_names
                    ],
                )
            )
            current = load(ledger_path)
            if stage == "integration":
                iteration = len(current["integration_reviews"]) + 1
            else:
                iteration = current["findings"][finding_id]["iterations"][stage] + 1
            return current["review_targets"][
                target_key(stage, finding_id, iteration)
            ]["bundle"]

        def bind(
            name: str,
            source: str | Path,
            target: dict[str, str],
        ) -> Path:
            source_path = files[source] if isinstance(source, str) else source
            return write(
                name,
                f"TARGET_ARTIFACT: {target_declaration(target)}\n"
                + source_path.read_text(encoding="utf-8"),
            )

        cmd_init(
            argparse.Namespace(
                state=str(path),
                runtime="codex",
                mode="repair",
                max_iterations=10,
            )
        )
        try:
            cmd_init(
                argparse.Namespace(
                    state=str(path),
                    runtime="codex",
                    mode="repair",
                    max_iterations=10,
                )
            )
            raise AssertionError("existing ledger was overwritten")
        except ValueError:
            pass
        legacy_coverage = write(
            "legacy-coverage",
            "COVERED: symbol:core.functions\nCOMMANDS: one static search\n",
        )
        try:
            cmd_coverage(
                argparse.Namespace(
                    state=str(path),
                    item="symbol:core.functions",
                    lane="core",
                    status="covered",
                    evidence_file=str(legacy_coverage),
                )
            )
            raise AssertionError("covered evidence without probes was accepted")
        except ValueError:
            pass
        misbound_coverage = write(
            "misbound-coverage",
            "COVERED: symbol:other\n"
            "PROBES: symbol:core.functions boundary probe\n"
            "NEGATIVE_FINDINGS: no other candidate\n"
            "COMMANDS: targeted review\n",
        )
        try:
            cmd_coverage(
                argparse.Namespace(
                    state=str(path),
                    item="symbol:core.functions",
                    lane="core",
                    status="covered",
                    evidence_file=str(misbound_coverage),
                )
            )
            raise AssertionError("item outside COVERED section was accepted")
        except ValueError:
            pass
        cmd_coverage(
            argparse.Namespace(
                state=str(path),
                item="symbol:core.functions",
                lane="core",
                status="covered",
                evidence_file=str(files["coverage-core"]),
            )
        )
        cmd_coverage(
            argparse.Namespace(
                state=str(path),
                item="ui:surface",
                lane="ui",
                status="skipped",
                evidence_file=str(files["coverage-ui"]),
            )
        )
        cmd_freeze_coverage(
            argparse.Namespace(
                state=str(path),
                manifest_file=str(files["manifest"]),
            )
        )
        try:
            cmd_coverage(
                argparse.Namespace(
                    state=str(path),
                    item="symbol:core.functions",
                    lane="core",
                    risk="high",
                    priority=1,
                    status="covered",
                    evidence_file=str(files["coverage-core"]),
                )
            )
            raise AssertionError("frozen coverage accepted risk reassignment")
        except ValueError:
            pass
        try:
            cmd_coverage(
                argparse.Namespace(
                    state=str(path),
                    item="module:late",
                    lane="late",
                    status="pending",
                    evidence_file=None,
                )
            )
            raise AssertionError("frozen coverage accepted a new item")
        except ValueError:
            pass
        for finding_id, title in (
            ("BUG-001", "real"),
            ("BUG-002", "false positive"),
            ("BUG-003", "historical decision"),
        ):
            cmd_add(
                argparse.Namespace(
                    state=str(path),
                    id=finding_id,
                    title=title,
                    item="symbol:core.functions",
                )
            )
        confirmation_target_1 = freeze(
            "confirmation",
            "BUG-001",
            "coverage-core",
            "confirm",
        )
        try:
            freeze(
                "confirmation",
                "BUG-001",
                "coverage-core",
                "confirm",
            )
            raise AssertionError("second target freeze for one gate was accepted")
        except ValueError:
            pass
        bundle_payload = json.loads(
            Path(confirmation_target_1["path"]).read_text(encoding="utf-8")
        )
        assert len(bundle_payload["artifacts"]) == 2
        assert base64.b64decode(
            bundle_payload["artifacts"][1]["content_base64"]
        ) == files["confirm"].read_bytes()
        original_bundle = Path(confirmation_target_1["path"]).read_bytes()
        Path(confirmation_target_1["path"]).write_bytes(original_bundle + b"\n")
        assert any("artifact digest changed" in error for error in validate(load(path)))
        Path(confirmation_target_1["path"]).write_bytes(original_bundle)
        confirmation_1 = bind("confirm-bound-1", "confirm", confirmation_target_1)
        false_positive_1 = bind(
            "false-positive-bound-1",
            "false-positive",
            confirmation_target_1,
        )
        ambiguous_confirmation_1 = bind(
            "ambiguous-confirmation-bound-1",
            "ambiguous-confirmation",
            confirmation_target_1,
        )
        try:
            cmd_review(
                argparse.Namespace(
                    state=str(path),
                    id="BUG-001",
                    stage="confirmation",
                    verdict="confirmed",
                    reviewer="agent:/root/declaration-mismatch",
                    evidence_file=str(false_positive_1),
                    blocker=None,
                )
            )
            raise AssertionError("opposite evidence declaration was accepted")
        except ValueError:
            pass
        for reviewer, evidence_file in (
            ("agent:/root/declaration-mismatch", confirmation_1),
            ("agent:/root/tiny-format", files["tiny-response"]),
            ("agent:/root/empty-format", files["empty-response"]),
            ("agent:/root/ambiguous-format", ambiguous_confirmation_1),
        ):
            try:
                cmd_review(
                    argparse.Namespace(
                        state=str(path),
                        id="BUG-001",
                        stage="confirmation",
                        verdict=(
                            "not-a-bug"
                            if reviewer == "agent:/root/ambiguous-format"
                            else "confirmed"
                        ),
                        reviewer=reviewer,
                        evidence_file=str(evidence_file),
                        blocker=None,
                    )
                )
                raise AssertionError("invalid format reviewer was accepted or reused")
            except ValueError:
                pass
        current = load(path)
        assert current["findings"]["BUG-001"]["iterations"]["confirmation"] == 0
        assert len(current["format_failures"]) == 4
        try:
            cmd_review(
                argparse.Namespace(
                    state=str(path),
                    id="BUG-001",
                    stage="fix",
                    verdict="accepted",
                    reviewer="agent:/root/invalid",
                    evidence_file=str(files["fix"]),
                    blocker=None,
                )
            )
            raise AssertionError("illegal fix transition was accepted")
        except ValueError:
            pass

        cmd_review(
            argparse.Namespace(
                state=str(path),
                id="BUG-001",
                stage="confirmation",
                verdict="confirmed",
                reviewer="agent:/root/blind-1",
                evidence_file=str(confirmation_1),
                blocker=None,
            )
        )
        try:
            cmd_document(
                argparse.Namespace(
                    state=str(path),
                    id="BUG-001",
                    spec=str(root / "missing.md"),
                    note="invalid",
                )
            )
            raise AssertionError("nonexistent spec was accepted")
        except ValueError:
            pass
        cmd_document(
            argparse.Namespace(
                state=str(path),
                id="BUG-001",
                spec=str(files["spec"]),
                note="documented",
            )
        )
        plan_target_1 = freeze("plan", "BUG-001", "spec")
        plan_1 = bind("plan-bound-1", "plan", plan_target_1)
        plan_contradictory_1 = bind(
            "plan-contradictory-bound-1",
            "plan-contradictory",
            plan_target_1,
        )
        cmd_add(
            argparse.Namespace(
                state=str(path),
                id="DEC-PLAN-1",
                title="late plan authority conflict",
                item="symbol:core.functions",
                decision_for_stage="plan",
                decision_for_subject="BUG-001",
            )
        )
        decision_plan_target = freeze(
            "confirmation",
            "DEC-PLAN-1",
            "decision",
        )
        decision_plan_evidence = bind(
            "decision-plan-bound",
            "decision",
            decision_plan_target,
        )
        cmd_review(
            argparse.Namespace(
                state=str(path),
                id="DEC-PLAN-1",
                stage="confirmation",
                verdict="needs-decision",
                reviewer="agent:/root/decision-plan",
                evidence_file=str(decision_plan_evidence),
                blocker=None,
            )
        )
        try:
            cmd_review(
                argparse.Namespace(
                    state=str(path),
                    id="BUG-001",
                    stage="plan",
                    verdict="accepted",
                    reviewer="agent:/root/plan-before-decision",
                    evidence_file=str(plan_1),
                    blocker=None,
                )
            )
            raise AssertionError("plan advanced through an unresolved decision")
        except ValueError:
            pass
        assert load(path)["findings"]["BUG-001"]["iterations"]["plan"] == 0
        try:
            cmd_annotate_decision(
                argparse.Namespace(
                    state=str(path),
                    id="DEC-PLAN-1",
                    evidence_file=str(files["user-decision-wrong"]),
                )
            )
            raise AssertionError("mismatched user decision was accepted")
        except ValueError:
            pass
        cmd_annotate_decision(
            argparse.Namespace(
                state=str(path),
                id="DEC-PLAN-1",
                evidence_file=str(files["user-decision-plan"]),
            )
        )
        original_plan_payload = json.loads(
            Path(plan_target_1["path"]).read_text(encoding="utf-8")
        )
        cmd_supersede_target(
            argparse.Namespace(
                state=str(path),
                stage="plan",
                id="BUG-001",
                decision_id="DEC-PLAN-1",
            )
        )
        try:
            cmd_supersede_target(
                argparse.Namespace(
                    state=str(path),
                    stage="plan",
                    id="BUG-001",
                    decision_id="DEC-PLAN-1",
                )
            )
            raise AssertionError("decision superseded the same target twice")
        except ValueError:
            pass
        current_plan_record = load(path)["review_targets"][
            target_key("plan", "BUG-001", 1)
        ]
        superseded_plan_target = current_plan_record["bundle"]
        superseded_plan_payload = json.loads(
            Path(superseded_plan_target["path"]).read_text(encoding="utf-8")
        )
        assert superseded_plan_payload["artifacts"][
            : len(original_plan_payload["artifacts"])
        ] == original_plan_payload["artifacts"]
        assert current_plan_record["applied_decisions"] == ["DEC-PLAN-1"]
        cmd_add(
            argparse.Namespace(
                state=str(path),
                id="DEC-PLAN-2",
                title="second late plan authority conflict",
                item="symbol:core.functions",
                decision_for_stage="plan",
                decision_for_subject="BUG-001",
            )
        )
        decision_plan_target_2 = freeze(
            "confirmation",
            "DEC-PLAN-2",
            "decision",
        )
        decision_plan_evidence_2 = bind(
            "decision-plan-bound-2",
            "decision",
            decision_plan_target_2,
        )
        cmd_review(
            argparse.Namespace(
                state=str(path),
                id="DEC-PLAN-2",
                stage="confirmation",
                verdict="needs-decision",
                reviewer="agent:/root/decision-plan-2",
                evidence_file=str(decision_plan_evidence_2),
                blocker=None,
            )
        )
        cmd_annotate_decision(
            argparse.Namespace(
                state=str(path),
                id="DEC-PLAN-2",
                evidence_file=str(files["user-decision-plan-2"]),
            )
        )
        cmd_supersede_target(
            argparse.Namespace(
                state=str(path),
                stage="plan",
                id="BUG-001",
                decision_id="DEC-PLAN-2",
            )
        )
        current_plan_record = load(path)["review_targets"][
            target_key("plan", "BUG-001", 1)
        ]
        assert current_plan_record["applied_decisions"] == [
            "DEC-PLAN-1",
            "DEC-PLAN-2",
        ]
        assert len(current_plan_record["superseded"]) == 2
        superseded_plan_target = current_plan_record["bundle"]
        plan_1 = bind("plan-bound-1-resumed", "plan", superseded_plan_target)
        plan_contradictory_1 = bind(
            "plan-contradictory-bound-1-resumed",
            "plan-contradictory",
            superseded_plan_target,
        )
        try:
            cmd_review(
                argparse.Namespace(
                    state=str(path),
                    id="BUG-001",
                    stage="plan",
                    verdict="accepted",
                    reviewer="agent:/root/blind-1",
                    evidence_file=str(plan_1),
                    blocker=None,
                )
            )
            raise AssertionError("reviewer reuse was accepted")
        except ValueError:
            pass
        try:
            cmd_review(
                argparse.Namespace(
                    state=str(path),
                    id="BUG-001",
                    stage="plan",
                    verdict="accepted",
                    reviewer="agent:/root/plan-contradictory",
                    evidence_file=str(plan_contradictory_1),
                    blocker=None,
                )
            )
            raise AssertionError("cross-stage controlling marker was accepted")
        except ValueError:
            pass
        cmd_review(
            argparse.Namespace(
                state=str(path),
                id="BUG-001",
                stage="plan",
                verdict="accepted",
                reviewer="agent:/root/plan-1",
                evidence_file=str(plan_1),
                blocker=None,
            )
        )
        cmd_mark(
            argparse.Namespace(
                state=str(path),
                id="BUG-001",
                status="implementing",
                note="started",
            )
        )
        fix_target_1 = freeze("fix", "BUG-001", "spec", "fix")
        fix_1 = bind("fix-bound-1", "fix", fix_target_1)
        cmd_review(
            argparse.Namespace(
                state=str(path),
                id="BUG-001",
                stage="fix",
                verdict="accepted",
                reviewer="agent:/root/fix-1",
                evidence_file=str(fix_1),
                blocker=None,
            )
        )
        try:
            cmd_review(
                argparse.Namespace(
                    state=str(path),
                    id="BUG-002",
                    stage="confirmation",
                    verdict="not-a-bug",
                    reviewer="agent:/root/blind-1",
                    evidence_file=str(files["false-positive"]),
                    blocker=None,
                )
            )
            raise AssertionError("reviewer reuse across findings was accepted")
        except ValueError:
            pass
        confirmation_target_2 = freeze(
            "confirmation",
            "BUG-002",
            "coverage-core",
            "false-positive",
        )
        false_positive_2 = bind(
            "false-positive-bound-2",
            "false-positive",
            confirmation_target_2,
        )
        try:
            cmd_review(
                argparse.Namespace(
                    state=str(path),
                    id="BUG-002",
                    stage="confirmation",
                    verdict="not-a-bug",
                    reviewer="agent:/root/blind-duplicate",
                    evidence_file=str(confirmation_1),
                    blocker=None,
                )
            )
            raise AssertionError("review evidence reuse across findings was accepted")
        except ValueError:
            pass
        cmd_review(
            argparse.Namespace(
                state=str(path),
                id="BUG-002",
                stage="confirmation",
                verdict="not-a-bug",
                reviewer="agent:/root/blind-2",
                evidence_file=str(false_positive_2),
                blocker=None,
            )
        )
        confirmation_target_3 = freeze(
            "confirmation",
            "BUG-003",
            "coverage-core",
            "decision",
        )
        decision_3 = bind("decision-bound-3", "decision", confirmation_target_3)
        cmd_review(
            argparse.Namespace(
                state=str(path),
                id="BUG-003",
                stage="confirmation",
                verdict="needs-decision",
                reviewer="agent:/root/blind-3",
                evidence_file=str(decision_3),
                blocker=None,
            )
        )
        try:
            cmd_annotate_resolution(
                argparse.Namespace(
                    state=str(path),
                    id="BUG-003",
                    resolved_by="BUG-002",
                    evidence_file=str(files["resolution"]),
                    note="must fail",
                )
            )
            raise AssertionError("non-accepted finding resolved a decision")
        except ValueError:
            pass
        for evidence_key in (
            "resolution-kind-mismatch",
            "resolution-id-mismatch",
            "coverage-core",
        ):
            try:
                cmd_annotate_resolution(
                    argparse.Namespace(
                        state=str(path),
                        id="BUG-003",
                        resolved_by="BUG-001",
                        evidence_file=str(files[evidence_key]),
                        note="must fail",
                    )
                )
                raise AssertionError(
                    f"invalid resolution evidence was accepted: {evidence_key}"
                )
            except ValueError:
                pass
        cmd_annotate_resolution(
            argparse.Namespace(
                state=str(path),
                id="BUG-003",
                resolved_by="BUG-001",
                evidence_file=str(files["resolution"]),
                note="resolved by the accepted related root fix",
            )
        )
        try:
            cmd_annotate_resolution(
                argparse.Namespace(
                    state=str(path),
                    id="BUG-003",
                    resolved_by="BUG-001",
                    evidence_file=str(files["resolution"]),
                    note="duplicate",
                )
            )
            raise AssertionError("second resolution annotation was accepted")
        except ValueError:
            pass
        resolved = load(path)["findings"]["BUG-003"]
        assert resolved["status"] == "needs_decision"
        assert resolved["resolution_annotations"][0]["resolved_by"] == "BUG-001"
        malformed = load(path)
        malformed["findings"]["BUG-001"]["reviews"] = 1
        assert "BUG-001: reviews must be an array" in validate(malformed)
        for annotations in (
            0,
            1,
            None,
            [None, 1],
            [{}],
            [{"resolved_by": None}],
        ):
            malformed = load(path)
            malformed["findings"]["BUG-003"]["resolution_annotations"] = annotations
            assert validate(malformed)
            assert summary_payload(malformed)["findings"]["BUG-003"]["resolved_by"] == []
        errors = validate(load(path), require_complete=True)
        assert "complete review requires a final accepted integration" in errors

        integration_target = freeze(
            "integration",
            "ALL",
            "manifest",
            "integration",
        )
        integration_1 = bind(
            "integration-bound-1",
            "integration",
            integration_target,
        )
        cmd_integration(
            argparse.Namespace(
                state=str(path),
                verdict="accepted",
                reviewer="agent:/root/final-1",
                evidence_file=str(integration_1),
                blocker=None,
            )
        )
        forged = load(path)
        forged["integration_reviews"] = []
        assert "complete run lacks final accepted integration" in validate(forged)
        forged = load(path)
        forged["status"] = "active"
        assert "accepted integration requires complete run status" in validate(forged)
        forged = load(path)
        forged_finding = forged["findings"]["BUG-001"]
        forged_finding["reviews"] = [
            review
            for review in forged_finding["reviews"]
            if review["stage"] != "fix"
        ]
        forged_finding["iterations"]["fix"] = 0
        assert any(
            "status accepted does not match review history" in error
            for error in validate(forged, require_complete=True)
        )
        forged = load(path)
        forged["findings"]["BUG-001"].pop("implementation_started")
        assert "BUG-001: implementation start record missing" in validate(
            forged,
            require_complete=True,
        )
        forged = load(path)
        plan_key = target_key("plan", "BUG-001", 1)
        active_bundle = forged["review_targets"][plan_key]["bundle"]
        active_payload = json.loads(
            Path(active_bundle["path"]).read_text(encoding="utf-8")
        )
        active_payload["artifacts"] = active_payload["artifacts"][:-2]
        forged_bundle_path = root / "forged-plan-bundle.json"
        forged_bundle_path.write_text(
            json.dumps(active_payload, sort_keys=True),
            encoding="utf-8",
        )
        forged["review_targets"][plan_key]["bundle"] = artifact(
            str(forged_bundle_path)
        )
        assert any(
            "decision evidence missing" in error
            or "supersession artifacts mismatch" in error
            for error in validate(forged, require_complete=True)
        )
        non_object_bundle_path = root / "non-object-target-bundle.json"
        non_object_bundle_path.write_text(
            json.dumps([0] * 20),
            encoding="utf-8",
        )
        non_object_bundle = artifact(str(non_object_bundle_path))
        assert target_bundle_error(
            non_object_bundle,
            "plan",
            "BUG-001",
            1,
            "probe",
        ) == "probe: target bundle must be an object"
        forged = load(path)
        forged["review_targets"][plan_key]["bundle"] = non_object_bundle
        assert any(
            "target bundle must be an object" in error
            for error in validate(forged, require_complete=True)
        )
        legacy = load(path)
        legacy["schema_version"] = 2
        legacy.pop("review_targets", None)
        legacy.pop("format_failures", None)
        for finding in legacy["findings"].values():
            for review in finding.get("reviews", []):
                review.pop("target", None)
        for review in legacy["integration_reviews"]:
            review.pop("target", None)
        assert not validate(legacy, require_complete=True)
        assert summary_payload(legacy)["target_binding"] == "legacy_unbound"
        try:
            require_frozen_target(legacy, "confirmation", "BUG-001", 1)
            raise AssertionError("legacy v2 ledger accepted a new review target")
        except ValueError:
            pass
        assert validate([]) == ["state must be an object"]
        malformed_states = []
        for mutator in (
            lambda value: value.update(schema_version=[]),
            lambda value: value.update(mode=[]),
            lambda value: value.update(status=[]),
            lambda value: value["coverage"]["symbol:core.functions"].update(
                status=[]
            ),
            lambda value: value["findings"]["BUG-001"].update(status=[]),
            lambda value: value["findings"]["BUG-001"].update(item=[]),
            lambda value: value["findings"]["BUG-001"]["reviews"][0].update(
                stage=[]
            ),
            lambda value: value["findings"]["BUG-001"]["reviews"][0].update(
                verdict=[]
            ),
            lambda value: value["findings"]["DEC-PLAN-1"]["decision_for"].update(
                subject=[]
            ),
            lambda value: value.update(integration_reviews=None),
        ):
            malformed = json.loads(json.dumps(load(path)))
            mutator(malformed)
            assert validate(malformed)
            malformed_states.append(malformed)
        malformed_summary = root / "malformed-summary.json"
        malformed_summary.write_text(
            json.dumps(malformed_states[-1]),
            encoding="utf-8",
        )
        try:
            cmd_summary(argparse.Namespace(state=str(malformed_summary)))
            raise AssertionError("summary rendered invalid state")
        except ValueError:
            pass
        try:
            cmd_add(
                argparse.Namespace(
                    state=str(path),
                    id="BUG-LATE",
                    title="late",
                    item="symbol:core.functions",
                )
            )
            raise AssertionError("completed ledger accepted mutation")
        except ValueError:
            pass

        blocked = new_state("codex", "audit", 10)
        blocked["coverage_frozen"] = True
        blocked["inventory_manifest"] = artifact(
            str(
                write(
                    "blocked-manifest",
                    "REPOSITORY: /tmp/example\nCOMMIT: deadbeef\nINVENTORY:\n- ui:blocked\n",
                )
            ),
            ("REPOSITORY:", "COMMIT:", "INVENTORY:"),
        )
        blocked["coverage"]["ui:blocked"] = {
            "lane": "ui",
            "risk": "medium",
            "priority": 100,
            "status": "blocked",
            "evidence": artifact(
                str(
                    write(
                        "coverage-blocked",
                        "BLOCKED: application cannot start\n"
                        "MISSING: ui:blocked test credentials and a local fixture\n",
                    )
                ),
                ("BLOCKED:", "MISSING:"),
            ),
            "updated_at": now(),
        }
        assert "incomplete coverage: ui:blocked" in validate(
            blocked,
            require_complete=True,
        )

        limited_path = root / "limited.json"
        cmd_init(
            argparse.Namespace(
                state=str(limited_path),
                runtime="codex",
                mode="audit",
                max_iterations=1,
            )
        )
        limited_manifest = write(
            "limited-manifest",
            "REPOSITORY: /tmp/example\nCOMMIT: deadbeef\nINVENTORY:\n"
            "- symbol:limited\n",
        )
        cmd_coverage(
            argparse.Namespace(
                state=str(limited_path),
                item="symbol:limited",
                lane="core",
                status="covered",
                evidence_file=str(files["coverage-core"]),
            )
        )
        cmd_freeze_coverage(
            argparse.Namespace(
                state=str(limited_path),
                manifest_file=str(limited_manifest),
            )
        )
        cmd_add(
            argparse.Namespace(
                state=str(limited_path),
                id="BUG-LIMIT",
                title="uncertain",
                item="symbol:limited",
            )
        )
        inconclusive = write(
            "inconclusive",
            "CLASSIFICATION: NEEDS_DECISION\nREPRODUCTION: unavailable environment\n"
            "AUTHORITY: conflicting current sources\nNEGATIVE_CONTROL: not executable\n"
            "ROOT_CAUSE: not proven\nCOUNTEREVIDENCE: intent may differ\n",
        )
        limited_target = freeze(
            "confirmation",
            "BUG-LIMIT",
            inconclusive,
            state_path=limited_path,
        )
        limited_evidence = bind(
            "inconclusive-bound",
            inconclusive,
            limited_target,
        )
        cmd_review(
            argparse.Namespace(
                state=str(limited_path),
                id="BUG-LIMIT",
                stage="confirmation",
                verdict="inconclusive",
                reviewer="agent:/root/limited",
                evidence_file=str(limited_evidence),
                blocker="missing-authority",
            )
        )
        assert load(limited_path)["findings"]["BUG-LIMIT"]["status"] == "needs_decision"

        undocumented = new_state("codex", "audit", 10)
        undocumented["coverage_frozen"] = True
        undocumented["inventory_manifest"] = artifact(
            str(
                write(
                    "undocumented-manifest",
                    "REPOSITORY: /tmp/example\nCOMMIT: deadbeef\nINVENTORY:\n"
                    "- symbol:core\n",
                )
            ),
            ("REPOSITORY:", "COMMIT:", "INVENTORY:"),
        )
        undocumented["coverage"]["symbol:core"] = {
            "lane": "core",
            "risk": "medium",
            "priority": 100,
            "status": "covered",
            "evidence": artifact(
                str(files["coverage-core"]),
                COVERED_MARKERS,
            ),
            "updated_at": now(),
        }
        undocumented["findings"]["BUG-004"] = {
            "title": "undocumented",
            "lane": "core",
            "item": "symbol:core",
            "status": "confirmed_bug",
            "iterations": {"confirmation": 1, "plan": 0, "fix": 0},
            "reviews": [],
            "created_at": now(),
        }
        assert any(
            error.startswith("BUG-004 spec:")
            for error in validate(undocumented, require_complete=True)
        )

        repair_blocked = new_state("codex", "repair", 10)
        repair_blocked["coverage_frozen"] = True
        repair_blocked["inventory_manifest"] = undocumented["inventory_manifest"]
        repair_blocked["coverage"]["symbol:core"] = {
            "lane": "core",
            "risk": "medium",
            "priority": 100,
            "status": "covered",
            "evidence": artifact(
                str(files["coverage-core"]),
                COVERED_MARKERS,
            ),
            "updated_at": now(),
        }
        repair_blocked["findings"]["BUG-005"] = {
            "title": "blocked",
            "lane": "core",
            "item": "symbol:core",
            "status": "documented_blocked",
            "spec": artifact(str(files["spec"]), SPEC_MARKERS),
            "iterations": {"confirmation": 1, "plan": 1, "fix": 10},
            "reviews": [],
            "created_at": now(),
        }
        assert "BUG-005: non-terminal status documented_blocked" in validate(
            repair_blocked, require_complete=True
        )

        audit_path = root / "audit.json"
        cmd_init(
            argparse.Namespace(
                state=str(audit_path),
                runtime="codex",
                mode="audit",
                max_iterations=10,
            )
        )
        cmd_coverage(
            argparse.Namespace(
                state=str(audit_path),
                item="symbol:core.audit",
                lane="core",
                status="covered",
                evidence_file=str(files["coverage-core"]),
            )
        )
        audit_manifest = write(
            "audit-manifest",
            "REPOSITORY: /tmp/example\nCOMMIT: deadbeef\nINVENTORY:\n"
            "- symbol:core.audit\n",
        )
        cmd_freeze_coverage(
            argparse.Namespace(
                state=str(audit_path),
                manifest_file=str(audit_manifest),
            )
        )
        cmd_add(
            argparse.Namespace(
                state=str(audit_path),
                id="BUG-006",
                title="audit only",
                item="symbol:core.audit",
            )
        )
        audit_confirmation_target = freeze(
            "confirmation",
            "BUG-006",
            "confirm",
            state_path=audit_path,
        )
        audit_confirmation = bind(
            "audit-confirm-bound",
            "confirm",
            audit_confirmation_target,
        )
        cmd_review(
            argparse.Namespace(
                state=str(audit_path),
                id="BUG-006",
                stage="confirmation",
                verdict="confirmed",
                reviewer="agent:/root/audit-blind",
                evidence_file=str(audit_confirmation),
                blocker=None,
            )
        )
        cmd_document(
            argparse.Namespace(
                state=str(audit_path),
                id="BUG-006",
                spec=str(files["spec"]),
                note="documented",
            )
        )
        audit_plan_target = freeze(
            "plan",
            "BUG-006",
            "spec",
            state_path=audit_path,
        )
        audit_plan = bind("audit-plan-bound", "plan", audit_plan_target)
        cmd_review(
            argparse.Namespace(
                state=str(audit_path),
                id="BUG-006",
                stage="plan",
                verdict="accepted",
                reviewer="agent:/root/audit-plan",
                evidence_file=str(audit_plan),
                blocker=None,
            )
        )
        try:
            cmd_mark(
                argparse.Namespace(
                    state=str(audit_path),
                    id="BUG-006",
                    status="implementing",
                    note="must fail",
                )
            )
            raise AssertionError("audit mode accepted implementation")
        except ValueError:
            pass
        audit_integration_target = freeze(
            "integration",
            "ALL",
            "integration",
            state_path=audit_path,
        )
        audit_integration = bind(
            "audit-integration-bound",
            "integration",
            audit_integration_target,
        )
        cmd_integration(
            argparse.Namespace(
                state=str(audit_path),
                verdict="accepted",
                reviewer="agent:/root/audit-final",
                evidence_file=str(audit_integration),
                blocker=None,
            )
        )
        assert load(audit_path)["status"] == "complete"

        integration_path = root / "integration-blocked.json"
        cmd_init(
            argparse.Namespace(
                state=str(integration_path),
                runtime="codex",
                mode="audit",
                max_iterations=10,
            )
        )
        cmd_coverage(
            argparse.Namespace(
                state=str(integration_path),
                item="symbol:integration",
                lane="core",
                status="covered",
                evidence_file=str(files["coverage-core"]),
            )
        )
        integration_manifest = write(
            "integration-manifest",
            "REPOSITORY: /tmp/example\nCOMMIT: deadbeef\nINVENTORY:\n"
            "- symbol:integration\n",
        )
        cmd_freeze_coverage(
            argparse.Namespace(
                state=str(integration_path),
                manifest_file=str(integration_manifest),
            )
        )
        cmd_add(
            argparse.Namespace(
                state=str(integration_path),
                id="DEC-RUN-1",
                title="integration authority hypothesis",
                item="symbol:integration",
                decision_for_stage="integration",
                decision_for_subject="RUN",
            )
        )
        run_decision_target = freeze(
            "confirmation",
            "DEC-RUN-1",
            "false-positive",
            state_path=integration_path,
        )
        run_decision_evidence = bind(
            "run-decision-not-bug",
            "false-positive",
            run_decision_target,
        )
        cmd_review(
            argparse.Namespace(
                state=str(integration_path),
                id="DEC-RUN-1",
                stage="confirmation",
                verdict="not-a-bug",
                reviewer="agent:/root/run-decision",
                evidence_file=str(run_decision_evidence),
                blocker=None,
            )
        )
        for index in range(1, 4):
            evidence = write(
                f"integration-reject-{index}",
                f"VERDICT: REJECTED\nCOVERAGE: manifest mismatch {index}\n"
                "PRODUCT_CHECKS: smoke failed\nINTERACTIONS: unresolved\n"
                "REMAINING_UNCERTAINTY: blocker persists\n",
            )
            rejected_target = freeze(
                "integration",
                "ALL",
                integration_manifest,
                evidence,
                state_path=integration_path,
            )
            rejected_evidence = bind(
                f"integration-reject-bound-{index}",
                evidence,
                rejected_target,
            )
            cmd_integration(
                argparse.Namespace(
                    state=str(integration_path),
                    verdict="rejected",
                    reviewer=f"agent:/root/final-reject-{index}",
                    evidence_file=str(rejected_evidence),
                    blocker=f"blocker-{index}",
                )
            )
        assert load(integration_path)["status"] == "documented_blocked"
        forged_blocked = load(integration_path)
        forged_blocked["integration_reviews"][-1]["blocker"] = None
        assert any(
            "blocker missing" in error for error in validate(forged_blocked)
        )
        trajectory = Path(f"{path}.events.jsonl")
        assert trajectory.is_file()
        events = [json.loads(line) for line in trajectory.read_text().splitlines()]
        assert events[0]["event"] == "init"
        assert events[-1]["status"] == "complete"
        assert all(event["run_id"] == events[0]["run_id"] for event in events)
        stale_path = root / "stale.json"
        Path(f"{stale_path}.events.jsonl").write_text("{}\n", encoding="utf-8")
        try:
            cmd_init(
                argparse.Namespace(
                    state=str(stale_path),
                    runtime="codex",
                    mode="audit",
                    max_iterations=10,
                )
            )
            raise AssertionError("stale trajectory was appended to a new run")
        except ValueError:
            pass
    print("OK")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    sub = result.add_subparsers(dest="command", required=True)

    command = sub.add_parser("init")
    command.add_argument("state")
    command.add_argument("--runtime", choices=["codex"], default="codex")
    command.add_argument("--mode", choices=["audit", "repair"], required=True)
    command.add_argument("--max-iterations", type=int, default=10)
    command.set_defaults(func=cmd_init)

    command = sub.add_parser("coverage")
    command.add_argument("state")
    command.add_argument("--item", required=True)
    command.add_argument("--lane", required=True)
    command.add_argument("--risk", choices=sorted(RISKS))
    command.add_argument("--priority", type=int)
    command.add_argument("--status", choices=sorted(COVERAGE_STATUSES), required=True)
    command.add_argument("--evidence-file")
    command.set_defaults(func=cmd_coverage)

    command = sub.add_parser("freeze-coverage")
    command.add_argument("state")
    command.add_argument("--manifest-file", required=True)
    command.set_defaults(func=cmd_freeze_coverage)

    command = sub.add_parser("freeze-target")
    command.add_argument("state")
    command.add_argument(
        "--stage",
        choices=["confirmation", "plan", "fix", "integration"],
        required=True,
    )
    command.add_argument("--id", required=True)
    command.add_argument("--artifact-file", action="append", required=True)
    command.set_defaults(func=cmd_freeze_target)

    command = sub.add_parser("supersede-target")
    command.add_argument("state")
    command.add_argument(
        "--stage",
        choices=["plan", "fix", "integration"],
        required=True,
    )
    command.add_argument("--id", required=True)
    command.add_argument("--decision-id", required=True)
    command.set_defaults(func=cmd_supersede_target)

    command = sub.add_parser("add")
    command.add_argument("state")
    command.add_argument("--id", required=True)
    command.add_argument("--title", required=True)
    command.add_argument("--item", required=True)
    command.add_argument(
        "--decision-for-stage",
        choices=["plan", "fix", "integration"],
    )
    command.add_argument("--decision-for-subject")
    command.set_defaults(func=cmd_add)

    command = sub.add_parser("review")
    command.add_argument("state")
    command.add_argument("--id", required=True)
    command.add_argument("--stage", choices=["confirmation", "plan", "fix"], required=True)
    command.add_argument("--verdict", required=True)
    command.add_argument("--reviewer", required=True)
    command.add_argument("--evidence-file", required=True)
    command.add_argument("--blocker")
    command.set_defaults(func=cmd_review)

    command = sub.add_parser("mark")
    command.add_argument("state")
    command.add_argument("--id", required=True)
    command.add_argument("--status", required=True)
    command.add_argument("--note", required=True)
    command.set_defaults(func=cmd_mark)

    command = sub.add_parser("document")
    command.add_argument("state")
    command.add_argument("--id", required=True)
    command.add_argument("--spec", required=True)
    command.add_argument("--note", default="documented")
    command.set_defaults(func=cmd_document)

    command = sub.add_parser("annotate-resolution")
    command.add_argument("state")
    command.add_argument("--id", required=True)
    command.add_argument("--resolved-by", required=True)
    command.add_argument("--evidence-file", required=True)
    command.add_argument("--note", required=True)
    command.set_defaults(func=cmd_annotate_resolution)

    command = sub.add_parser("annotate-decision")
    command.add_argument("state")
    command.add_argument("--id", required=True)
    command.add_argument("--evidence-file", required=True)
    command.set_defaults(func=cmd_annotate_decision)

    command = sub.add_parser("integration")
    command.add_argument("state")
    command.add_argument("--verdict", choices=["accepted", "rejected"], required=True)
    command.add_argument("--reviewer", required=True)
    command.add_argument("--evidence-file", required=True)
    command.add_argument("--blocker")
    command.set_defaults(func=cmd_integration)

    command = sub.add_parser("validate")
    command.add_argument("state")
    command.add_argument("--complete", action="store_true")
    command.set_defaults(func=cmd_validate)

    command = sub.add_parser("summary")
    command.add_argument("state")
    command.set_defaults(func=cmd_summary)

    command = sub.add_parser("self-test")
    command.set_defaults(func=cmd_self_test)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        args.func(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
