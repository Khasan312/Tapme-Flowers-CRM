"""Opt-in, reproducible synthetic evaluation; never reads the CRM database."""

import argparse
import hashlib
import json
import math
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from tapme.orders.application.extraction import (
    ExtractionContext,
    ExtractionUnavailable,
    validate_suggestions,
)
from tapme.orders.infrastructure.extractors import SYSTEM_PROMPT, MistralChatExtractor

# Uncached USD / million tokens; official inference pricing checked 2026-10-26.
PRICES = {"ministral-3b-2512": (0.10, 0.10), "ministral-8b-2512": (0.15, 0.15)}


def match(actual, expected):
    if isinstance(expected, str) and isinstance(actual, str):
        return actual.casefold().strip(" .") == expected.casefold().strip(" .")
    if isinstance(expected, list) and isinstance(actual, list):
        return len(actual) == len(expected) and all(
            any(match(a, e) for a in actual) for e in expected
        )
    if isinstance(expected, dict) and isinstance(actual, dict):
        # Budget descriptions are grounded by the application; only amount/kind are scored.
        return all(k in actual and match(actual[k], v) for k, v in expected.items())
    return actual == expected


def evaluate(model, case, key):
    started = time.monotonic()
    row = {"model": model, "case": case["id"], "split": case["split"], "tokens": {}}
    expected = case["expected"]
    fields = {}
    try:
        context = ExtractionContext(**case["context"])
        result = MistralChatExtractor(key, model).extract(context)
        row["tokens"] = result.usage
        fields = {s["field"]: s["value"] for s in validate_suggestions(result, context)}
    except ExtractionUnavailable as exc:
        row["error"] = str(exc)  # Safe application code, never SDK body or credentials.
    correct = [k for k, v in expected.items() if k in fields and match(fields[k], v)]
    missing = sorted(set(expected) - fields.keys())
    incorrect = sorted(set(expected) & fields.keys() - set(correct))
    extra = sorted(fields.keys() - expected.keys())
    row.update(
        fields=fields,
        expected_fields=len(expected),
        correct_fields=len(correct),
        missing=missing,
        incorrect=incorrect,
        extra=extra,
        passed=not (missing or incorrect or extra or row.get("error")),
        seconds=round(time.monotonic() - started, 3),
    )
    rate = PRICES[model]
    row["estimated_usd"] = round(
        (
            row["tokens"].get("prompt_tokens", 0) * rate[0]
            + row["tokens"].get("completion_tokens", 0) * rate[1]
        )
        / 1_000_000,
        8,
    )
    return row


def aggregate(rows):
    n = sum(r["expected_fields"] for r in rows)
    correct = sum(r["correct_fields"] for r in rows)
    emitted = sum(len(r["fields"]) for r in rows)
    latencies = sorted(r["seconds"] for r in rows)
    return {
        "cases": len(rows),
        "passed": sum(r["passed"] for r in rows),
        "expected_fields": n,
        "correct_fields": correct,
        "field_recall_percent": round(100 * correct / n, 2) if n else None,
        "field_precision_percent": round(100 * correct / emitted, 2)
        if emitted
        else None,
        "incorrect_values": sum(len(r["incorrect"]) for r in rows),
        "unsupported_extra_fields": sum(len(r["extra"]) for r in rows),
        "failed_requests": sum(bool(r.get("error")) for r in rows),
        "errors_by_code": {
            code: sum(r.get("error") == code for r in rows)
            for code in sorted({r["error"] for r in rows if "error" in r})
        },
        "p50_seconds": latencies[len(rows) // 2],
        "p95_seconds": latencies[math.ceil(len(rows) * 0.95) - 1],
        "prompt_tokens": sum(r["tokens"].get("prompt_tokens", 0) for r in rows),
        "completion_tokens": sum(r["tokens"].get("completion_tokens", 0) for r in rows),
        "estimated_usd": round(sum(r["estimated_usd"] for r in rows), 6),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live",
        action="store_true",
        help="Allow real API calls using synthetic data (may use paid quota).",
    )
    parser.add_argument(
        "--models", nargs="+", choices=list(PRICES), default=list(PRICES)
    )
    parser.add_argument(
        "--split", choices=["all", "development", "holdout"], default="all"
    )
    parser.add_argument("--output", default="/tmp/tapme-mistral-quality-v1.json")
    args = parser.parse_args()
    if not args.live:
        parser.error(
            "Pass --live to explicitly allow the selected synthetic API calls."
        )
    key = dotenv_values(ROOT / ".env").get("MISTRAL_API_KEY")
    if not key:
        parser.error("MISTRAL_API_KEY is missing from local .env.")
    source = ROOT / "backend/tests/evals/draft_synthetic_v1.json"
    data = json.loads(source.read_text())
    cases = [
        c for c in data["cases"] if args.split == "all" or c["split"] == args.split
    ]
    report = {
        "kind": "synthetic pipeline evaluation, not S-04 approval",
        "dataset_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "prompt_sha256": hashlib.sha256(SYSTEM_PROMPT.encode()).hexdigest(),
        "parallel_requests": 2,
        "pricing_source": "https://docs.mistral.ai/inference/pricing",
        "pricing_checked": "2026-10-26",
        "unit_prices_usd_per_million": PRICES,
        "results": [],
    }
    tasks = [(model, case) for case in cases for model in dict.fromkeys(args.models)]
    with ThreadPoolExecutor(max_workers=2) as pool:
        for row in pool.map(lambda task: evaluate(*task, key), tasks):
            report["results"].append(row)
            Path(args.output).write_text(
                json.dumps(report, ensure_ascii=False, indent=2) + "\n"
            )
            print(
                json.dumps(
                    {k: v for k, v in row.items() if k != "fields"}, ensure_ascii=False
                ),
                flush=True,
            )
    report["summary"] = {
        model: {
            split: aggregate(
                [
                    r
                    for r in report["results"]
                    if r["model"] == model and (split == "all" or r["split"] == split)
                ]
            )
            for split in ["all", *sorted({c["split"] for c in cases})]
        }
        for model in dict.fromkeys(args.models)
    }
    Path(args.output).write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    )
    print(json.dumps(report["summary"], ensure_ascii=False, indent=2), flush=True)
    return 0 if all(r["passed"] for r in report["results"]) else 1


if __name__ == "__main__":
    sys.exit(main())
