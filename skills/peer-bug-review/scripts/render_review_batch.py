#!/usr/bin/env python3
"""Validate structured reviewer output and render one ledger artifact per target."""

from __future__ import annotations

import argparse
import json
import re
import tempfile
from pathlib import Path


STAGE_FIELDS = {
    "confirmation": (
        ("REPRODUCTION", "reproduction"),
        ("AUTHORITY", "authority"),
        ("NEGATIVE_CONTROL", "negative_control"),
        ("ROOT_CAUSE", "root_cause"),
        ("COUNTEREVIDENCE", "counterevidence"),
    ),
    "plan": (("PLAN", "plan"), ("COUNTEREVIDENCE", "counterevidence")),
    "fix": (
        ("DIFF", "diff"),
        ("TESTS", "tests"),
        ("COUNTEREVIDENCE", "counterevidence"),
    ),
    "integration": (
        ("COVERAGE", "coverage"),
        ("PRODUCT_CHECKS", "product_checks"),
        ("INTERACTIONS", "interactions"),
        ("REMAINING_UNCERTAINTY", "remaining_uncertainty"),
        ("OMISSIONS", "omissions"),
    ),
}
CONFIRMATION_OUTCOMES = {
    "CONFIRMED_BUG": "confirmed",
    "NOT_A_BUG": "not-a-bug",
    "NEEDS_DECISION": "needs-decision",
    "DUPLICATE": "duplicate",
}
GATE_OUTCOMES = {"ACCEPTED": "accepted", "REJECTED": "rejected"}


def one_line(value: object, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string")
    result = " ".join(value.split())
    if not result:
        raise ValueError(f"{label} must be non-empty")
    return result


def render_batch(payload: object, out_dir: Path) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("batch result must be an object")
    stage = payload.get("stage")
    if stage not in STAGE_FIELDS:
        raise ValueError(f"invalid stage: {stage}")
    reviews = payload.get("reviews")
    if not isinstance(reviews, list) or not 1 <= len(reviews) <= 4:
        raise ValueError("reviews must contain 1-4 items")
    if stage == "integration" and len(reviews) != 1:
        raise ValueError("integration batches must contain exactly one item")

    out_dir.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    manifest = {"stage": stage, "reviews": []}
    for index, review in enumerate(reviews, start=1):
        if not isinstance(review, dict):
            raise ValueError(f"review {index} must be an object")
        finding_id = one_line(review.get("id"), f"review {index} id")
        if not re.fullmatch(r"[A-Za-z0-9_.:-]+", finding_id):
            raise ValueError(f"review {index} id is not ledger-safe")
        if finding_id in seen:
            raise ValueError(f"duplicate review id: {finding_id}")
        seen.add(finding_id)

        target = one_line(
            review.get("target_artifact"),
            f"{finding_id} target_artifact",
        )
        if not re.fullmatch(r"[0-9a-f]{64} .+", target):
            raise ValueError(f"{finding_id} target_artifact must be '<sha256> <path>'")
        outcome = one_line(review.get("outcome"), f"{finding_id} outcome")
        allowed = CONFIRMATION_OUTCOMES if stage == "confirmation" else GATE_OUTCOMES
        if outcome not in allowed:
            raise ValueError(f"{finding_id} outcome {outcome} is invalid for {stage}")
        blocker = " ".join(str(review.get("blocker", "")).split())
        if outcome == "REJECTED" and not blocker:
            raise ValueError(f"{finding_id} rejected review requires blocker")

        controlling = (
            f"CLASSIFICATION: {outcome}"
            if stage == "confirmation"
            else f"VERDICT: {outcome}"
        )
        lines = [f"TARGET_ARTIFACT: {target}", controlling]
        for marker, field in STAGE_FIELDS[stage]:
            lines.append(
                f"{marker}: {one_line(review.get(field), f'{finding_id} {field}')}"
            )
        evidence_path = out_dir / f"{finding_id}-{stage}.txt"
        if evidence_path.exists():
            raise ValueError(f"refusing to overwrite evidence: {evidence_path}")
        evidence_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        manifest["reviews"].append(
            {
                "id": finding_id,
                "verdict": allowed[outcome],
                "blocker": blocker or None,
                "evidence_file": str(evidence_path.resolve()),
                "reviewer_suffix": f"{finding_id}/{stage}",
            }
        )
    return manifest


def self_test() -> None:
    fields = {
        "reproduction": "deterministic command",
        "authority": "current contract",
        "negative_control": "clean fixture",
        "root_cause": "shared seam",
        "plan": "",
        "diff": "",
        "tests": "",
        "coverage": "",
        "product_checks": "",
        "interactions": "",
        "counterevidence": "none survived",
        "remaining_uncertainty": "",
        "omissions": "",
        "blocker": "",
    }
    payload = {
        "stage": "confirmation",
        "reviews": [
            {
                "id": "PBR-001",
                "target_artifact": f"{'a' * 64} /tmp/target.json",
                "outcome": "CONFIRMED_BUG",
                **fields,
            }
        ],
    }
    with tempfile.TemporaryDirectory() as directory:
        manifest = render_batch(payload, Path(directory))
        evidence = Path(manifest["reviews"][0]["evidence_file"]).read_text()
        assert "CLASSIFICATION: CONFIRMED_BUG" in evidence
        assert "ROOT_CAUSE: shared seam" in evidence
        try:
            render_batch(payload, Path(directory))
        except ValueError as exc:
            assert "refusing to overwrite" in str(exc)
        else:
            raise AssertionError("renderer overwrote evidence")
    print("OK")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", nargs="?")
    parser.add_argument("out_dir", nargs="?")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not args.input or not args.out_dir:
        parser.error("input and out_dir are required")
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    manifest = render_batch(payload, Path(args.out_dir))
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
