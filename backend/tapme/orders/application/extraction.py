"""Provider-independent contract and validation for untrusted draft suggestions."""

import json
import math
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from tapme.orders.application.draft_rules import TEXT_FIELDS, normalize_fields
from tapme.shared.domain import InvalidInput


class ExtractionUnavailable(Exception):
    """Safe error code only; provider responses must not enter logs."""


@dataclass(frozen=True)
class ExtractionContext:
    messages: list[dict[str, Any]]
    fields: dict[str, Any]
    now: str
    timezone: str
    products: list[dict[str, Any]]
    windows: list[dict[str, Any]]


@dataclass(frozen=True)
class ExtractionResult:
    suggestions: list[dict[str, Any]]
    usage: dict[str, int] = field(default_factory=dict)


def validate_suggestions(
    result: ExtractionResult, context: ExtractionContext
) -> list[dict[str, Any]]:
    allowed = set(TEXT_FIELDS) | {"date", "window", "fulfillment", "items"}
    sources = {m["id"] for m in context.messages}
    products = {p["id"] for p in context.products}
    seen: set[str] = set()
    validated = []
    try:
        if not isinstance(result.suggestions, list) or len(result.suggestions) > len(allowed):
            raise ValueError
        for suggestion in result.suggestions:
            if not isinstance(suggestion, dict) or set(suggestion) - {"evidence"} != {
                "field",
                "value_json",
                "confidence",
                "message_ids",
            }:
                raise ValueError
            key = suggestion["field"]
            if not isinstance(key, str) or key not in allowed or key in seen:
                raise ValueError
            seen.add(key)
            confidence = suggestion["confidence"]
            ids = suggestion["message_ids"]
            if (
                type(confidence) not in (int, float)
                or not math.isfinite(confidence)
                or not 0 <= confidence <= 1
                or not isinstance(ids, list)
                or not ids
                or len(ids) > 40
                or any(type(i) is not int or i not in sources for i in ids)
                or not isinstance(suggestion["value_json"], str)
                or len(suggestion["value_json"]) > 15000
            ):
                raise ValueError
            evidence = suggestion.get("evidence")
            if evidence is not None:
                from tapme.orders.application.extraction_grounding import valid_evidence

                if not valid_evidence(evidence, context) or set(ids) != {
                    e["message_id"] for e in evidence
                }:
                    raise ValueError
            raw = json.loads(suggestion["value_json"])
            value = normalize_fields({**context.fields, key: raw})[key]
            if key == "date" and value:
                if date.fromisoformat(value) < date.fromisoformat(context.now[:10]):
                    raise ValueError
            if key == "items":
                for item in value:
                    if item["kind"] == "product" and item["product_id"] not in products:
                        raise ValueError
                # Prices for catalogue items never come from the model.
                for item in raw:
                    expected = (
                        {"kind", "product_id", "quantity"}
                        if item.get("kind") == "product"
                        else {"kind", "amount", "description"}
                    )
                    if set(item) != expected:
                        raise ValueError
            if key == "window" and value not in [
                {"start": w["start"], "end": w["end"]} for w in context.windows
            ]:
                # Only the deterministic exact-time rule may clear a previous interval.
                from tapme.orders.application.extraction_grounding import receiving_facts

                clearing = receiving_facts(context).get("window")
                if (
                    not clearing
                    or json.loads(clearing["value_json"]) != value
                    or evidence != clearing.get("evidence")
                ):
                    raise ValueError
            validated.append(
                {
                    "field": key,
                    "value": value,
                    "confidence": confidence,
                    "message_ids": ids,
                    **({"evidence": evidence} if evidence is not None else {}),
                }
            )
    except (ValueError, TypeError, KeyError, InvalidInput):
        raise ExtractionUnavailable("invalid_result") from None
    return validated
