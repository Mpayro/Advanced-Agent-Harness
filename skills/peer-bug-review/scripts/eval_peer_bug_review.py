#!/usr/bin/env python3
"""Generate and grade a small private benchmark for peer-bug-review."""

from __future__ import annotations

import argparse
import json
import random
import tempfile
from pathlib import Path


CLASSIFICATIONS = {"CONFIRMED_BUG", "NOT_A_BUG", "NEEDS_DECISION", "DUPLICATE"}


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def generate(out: Path, seed: int) -> dict:
    if out.exists() and any(out.iterdir()):
        raise ValueError(f"output directory is not empty: {out}")
    rng = random.Random(seed)
    token = "".join(rng.choice("abcdefghjkmnpqrstuvwxyz23456789") for _ in range(8))
    workspace = out / "workspace"
    grader = out / "grader"
    workspace.mkdir(parents=True, exist_ok=True)
    grader.mkdir(parents=True, exist_ok=True)

    cases = [
        {
            "case_id": f"case:{token}-threshold",
            "path": "shipping.py",
            "classification": "CONFIRMED_BUG",
            "content": (
                "FREE_SHIPPING_MINIMUM = 100\n\n"
                "def shipping_fee(total):\n"
                "    \"\"\"Return 0 when the accepted contract grants free shipping.\"\"\"\n"
                "    return 0 if total > FREE_SHIPPING_MINIMUM else 12\n"
            ),
        },
        {
            "case_id": f"case:{token}-restart",
            "path": "drafts.py",
            "classification": "CONFIRMED_BUG",
            "content": (
                "def reset_session(state):\n"
                "    \"\"\"Reset the session and discard all uncommitted draft rows.\"\"\"\n"
                "    state['status'] = 'reset'\n"
                "    return state\n"
            ),
        },
        {
            "case_id": f"case:{token}-archive",
            "path": "accounts.py",
            "classification": "NOT_A_BUG",
            "content": (
                "def visible_accounts(accounts):\n"
                "    \"\"\"Archived accounts stay hidden from normal lists by contract.\"\"\"\n"
                "    return [row for row in accounts if not row.get('archived')]\n"
            ),
        },
        {
            "case_id": f"case:{token}-rounding",
            "path": "rounding.py",
            "classification": "NEEDS_DECISION",
            "content": (
                "def display_units(value):\n"
                "    return round(value)\n"
            ),
        },
    ]
    rng.shuffle(cases)

    write(
        workspace / "PRODUCT_CONTRACT.md",
        "# Current product contract\n\n"
        "- Shipping is free when the order total is **at least 100**.\n"
        "- Reset discards every uncommitted draft row.\n"
        "- Archived accounts are intentionally hidden from normal account lists.\n"
        "- Display rounding is disputed: product says half-up; finance says banker's "
        "rounding. Neither source is approved as stronger.\n",
    )
    for case in cases:
        write(workspace / case["path"], case["content"])
    write(
        workspace / "AUDIT_TASK.md",
        "# Audit task\n\n"
        "Audit every case below. Return JSON with `findings`, one object per case, using "
        "`case_id` and one of `CONFIRMED_BUG`, `NOT_A_BUG`, `NEEDS_DECISION`, or "
        "`DUPLICATE` as `classification`. Include optional `metadata.elapsed_seconds` "
        "and `metadata.estimated_tokens`.\n\n"
        + "\n".join(f"- {case['case_id']}: `{case['path']}`" for case in cases)
        + "\n",
    )
    oracle = {
        "schema_version": 1,
        "seed": seed,
        "cases": [
            {
                "case_id": case["case_id"],
                "classification": case["classification"],
            }
            for case in cases
        ],
    }
    write(grader / "oracle.json", json.dumps(oracle, indent=2, sort_keys=True) + "\n")
    return oracle


def score(oracle: dict, report: dict) -> dict:
    expected = {
        case["case_id"]: case["classification"] for case in oracle.get("cases", [])
    }
    submitted = report.get("findings")
    if not isinstance(submitted, list):
        raise ValueError("report findings must be an array")
    predicted: dict[str, str] = {}
    for finding in submitted:
        if not isinstance(finding, dict):
            raise ValueError("each report finding must be an object")
        case_id = finding.get("case_id")
        classification = finding.get("classification")
        if case_id not in expected:
            raise ValueError(f"unknown case_id: {case_id}")
        if case_id in predicted:
            raise ValueError(f"duplicate case_id: {case_id}")
        if classification not in CLASSIFICATIONS:
            raise ValueError(f"invalid classification for {case_id}: {classification}")
        predicted[case_id] = classification

    positives = {key for key, value in expected.items() if value == "CONFIRMED_BUG"}
    predicted_positives = {
        key for key, value in predicted.items() if value == "CONFIRMED_BUG"
    }
    true_positives = positives & predicted_positives
    precision = (
        len(true_positives) / len(predicted_positives) if predicted_positives else 0.0
    )
    recall = len(true_positives) / len(positives) if positives else 1.0
    correct = sum(predicted.get(key) == value for key, value in expected.items())
    metadata = report.get("metadata") if isinstance(report.get("metadata"), dict) else {}
    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "classification_accuracy": round(correct / len(expected), 4),
        "inventory_coverage": round(len(predicted) / len(expected), 4),
        "correct": correct,
        "total": len(expected),
        "elapsed_seconds": metadata.get("elapsed_seconds"),
        "estimated_tokens": metadata.get("estimated_tokens"),
    }


def read_json(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def self_test() -> None:
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / "benchmark"
        oracle = generate(root, 17)
        perfect = {
            "findings": [
                {
                    "case_id": case["case_id"],
                    "classification": case["classification"],
                }
                for case in oracle["cases"]
            ]
        }
        result = score(oracle, perfect)
        assert result["precision"] == 1.0
        assert result["recall"] == 1.0
        assert result["classification_accuracy"] == 1.0
        assert result["inventory_coverage"] == 1.0
        incomplete = score(oracle, {"findings": perfect["findings"][:1]})
        assert incomplete["inventory_coverage"] == 0.25
    print("OK")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    commands = result.add_subparsers(dest="command", required=True)

    command = commands.add_parser("generate")
    command.add_argument("--out", type=Path, required=True)
    command.add_argument("--seed", type=int, default=17)

    command = commands.add_parser("grade")
    command.add_argument("--oracle", type=Path, required=True)
    command.add_argument("--report", type=Path, required=True)

    commands.add_parser("self-test")
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "generate":
            oracle = generate(args.out.expanduser().resolve(), args.seed)
            print(json.dumps({"cases": len(oracle["cases"]), "workspace": str(args.out / "workspace")}))
        elif args.command == "grade":
            print(json.dumps(score(read_json(args.oracle), read_json(args.report)), indent=2))
        else:
            self_test()
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
