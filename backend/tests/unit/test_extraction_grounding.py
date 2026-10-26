import json
from dataclasses import replace
from pathlib import Path

import pytest

from tapme.orders.application.extraction import (
    ExtractionContext,
    ExtractionResult,
    ExtractionUnavailable,
    validate_suggestions,
)
from tapme.orders.application.extraction_grounding import grounded_extraction, receiving_facts

DATA = json.loads((Path(__file__).parents[1] / "evals/draft_synthetic_v1.json").read_text())
DEV = [c for c in DATA["cases"] if c["split"] == "development"]


def ctx(*texts, **kwargs):
    data = {
        **DEV[0]["context"],
        "messages": [
            {"id": i + 1, "direction": "in", "at": DEV[0]["context"]["now"], "text": t}
            for i, t in enumerate(texts)
        ],
    }
    return ExtractionContext(**{**data, **kwargs})


def proposal(field, value, quote, message_id=1):
    return {
        "field": field,
        "value_json": json.dumps(value),
        "confidence": 0.9,
        "message_ids": [message_id],
        "evidence": [{"message_id": message_id, "quote": quote}],
    }


def values(result, context):
    return {s["field"]: s["value"] for s in validate_suggestions(result, context)}


@pytest.mark.parametrize("case", DEV, ids=[c["id"] for c in DEV])
def test_receiving_rules_against_development_dialogues(case):
    context = ExtractionContext(**case["context"])
    temporal = {"date", "window", "requested_time_text"}
    result = ExtractionResult(list(receiving_facts(context).values()))
    assert values(result, context) == {k: v for k, v in case["expected"].items() if k in temporal}


@pytest.mark.parametrize(
    "text",
    [
        "Мой день рождения завтра.",
        "Заказ нужен, но день рождения завтра.",
        "Открытка: Доставьте завтра к 15:00.",
        "Доставите завтра?",
        "Нужна доставка завтра или послезавтра.",
        "Нужна доставка не завтра.",
        "Нужна доставка 31.02.2027.",
        "Нужна доставка в 25:90.",
    ],
)
def test_ambiguous_or_irrelevant_times_not_proposed(text):
    assert receiving_facts(ctx(text)) == {}


@pytest.mark.parametrize(
    "value,quote,source",
    [
        ("Несуществующий адрес", "Адрес: Тестовая 1", "Адрес: Тестовая 1"),
        ("Тестовая 1", "Адрес: Тестовая 1", "Нужен букет"),
        ("Тестовая 1", "Тестовая 1", "Доставите на Тестовая 1?"),
    ],
)
def test_text_requires_real_quote_and_literal_value(value, quote, source):
    context = ctx(source)
    assert (
        grounded_extraction(
            ExtractionResult([proposal("address", value, quote)]), context
        ).suggestions
        == []
    )


def test_model_dates_and_catalogue_defaults_never_used():
    context = ctx("Нужна доставка завтра.")
    result = grounded_extraction(
        ExtractionResult(
            [
                proposal("date", "2026-10-30", "завтра"),
                proposal("window", {"start": "10:00", "end": "12:00"}, "завтра"),
            ]
        ),
        context,
    )
    assert values(result, context) == {"date": "2026-10-27"}


def test_evidence_survives_validation_and_cannot_be_forged():
    context = ctx("Адрес: Учебная 5")
    good = proposal("address", "Учебная 5", "Адрес: Учебная 5")
    assert (
        validate_suggestions(ExtractionResult([good]), context)[0]["evidence"] == good["evidence"]
    )
    bad = {**good, "evidence": [{"message_id": 1, "quote": "Другой адрес"}]}
    with pytest.raises(ExtractionUnavailable):
        validate_suggestions(ExtractionResult([bad]), context)


def test_only_grounded_exact_time_can_clear_existing_interval():
    context = ctx("Нужна доставка к 15:00.", fields={"window": {"start": "10:00", "end": "12:00"}})
    result = ExtractionResult(list(receiving_facts(context).values()))
    assert values(result, context)["window"] == {"start": "", "end": ""}
    with pytest.raises(ExtractionUnavailable):
        validate_suggestions(
            ExtractionResult([proposal("window", {"start": "", "end": ""}, "Нужна доставка")]),
            context,
        )


def test_interval_replaces_old_exact_time():
    context = ctx("Нужна доставка с 10 до 12.", fields={"requested_time_text": "к 15:00"})
    assert values(ExtractionResult(list(receiving_facts(context).values())), context) == {
        "window": {"start": "10:00", "end": "12:00"},
        "requested_time_text": "",
    }


def test_outgoing_proposal_needs_customer_confirmation():
    context = ctx("Доставим завтра с 10 до 12?", "Да, подходит.")
    context.messages[0]["direction"] = "out"
    assert (
        values(ExtractionResult(list(receiving_facts(context).values())), context)["date"]
        == "2026-10-27"
    )
    assert receiving_facts(replace(context, messages=context.messages[:1])) == {}


def test_no_hallucinated_quantity_or_occasion_from_card():
    context = ctx("Нужен букет «Нежность». Открытка: С праздником!")
    result = grounded_extraction(
        ExtractionResult(
            [
                proposal(
                    "items",
                    [{"kind": "product", "product_id": context.products[0]["id"], "quantity": 10}],
                    "Нужен букет «Нежность»",
                ),
                proposal("occasion", "праздником", "Открытка: С праздником!"),
            ]
        ),
        context,
    )
    assert result.suggestions == []
