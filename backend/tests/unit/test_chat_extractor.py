import json

import httpx
import pytest
from mistralai.client import Mistral

from tapme.orders.application.extraction import (
    ExtractionContext,
    ExtractionUnavailable,
    validate_suggestions,
)
from tapme.orders.infrastructure.extractors import MistralChatExtractor


def context():
    return ExtractionContext(
        messages=[
            {"id": 3, "text": "Завтра", "direction": "in", "at": "2026-10-26T20:00:00+06:00"}
        ],
        fields={},
        now="2026-10-26T20:00:00+06:00",
        timezone="Asia/Bishkek",
        products=[],
        windows=[],
    )


def response(content=None, finish="stop"):
    return {
        "id": "test",
        "object": "chat.completion",
        "model": "ministral-3b-2512",
        "created": 1,
        "usage": {"prompt_tokens": 23, "completion_tokens": 10, "total_tokens": 33},
        "choices": [
            {
                "index": 0,
                "finish_reason": finish,
                "message": {
                    "role": "assistant",
                    "content": json.dumps({"suggestions": []}) if content is None else content,
                },
            }
        ],
    }


def adapter(handler):
    return MistralChatExtractor(
        "SECRET-TEST",
        "ministral-3b-2512",
        client_factory=lambda **kwargs: Mistral(
            **kwargs, client=httpx.Client(transport=httpx.MockTransport(handler))
        ),
    )


def test_official_sdk_payload_and_usage():
    requests = []

    def handle(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json=response())

    result = adapter(handle).extract(context())
    assert result.suggestions == []
    assert result.usage == {"prompt_tokens": 23, "completion_tokens": 10}
    payload = requests[0]
    assert payload["model"] == "ministral-3b-2512"
    assert payload["response_format"]["json_schema"]["schema"]["required"] == ["suggestions"]
    assert payload["messages"][0]["role"] == "system"
    assert json.loads(payload["messages"][1]["content"])["messages"][0]["id"] == 3
    assert "windows" not in json.loads(payload["messages"][1]["content"])
    assert not payload.get("tools")


def test_typed_provider_values_pass_application_validation():
    ctx = context()
    ctx.windows.append({"start": "10:00", "end": "12:00"})
    ctx.messages[0]["text"] = "Нужен букет, бюджет 2500 сом, завтра с 10 до 12."
    values = {"items": [{"kind": "budget", "amount": "2500", "description": ""}]}
    payload = {
        "suggestions": [
            {
                "field": key,
                "value": value,
                "confidence": 0.9,
                "evidence": [{"message_id": 3, "quote": ctx.messages[0]["text"]}],
            }
            for key, value in values.items()
        ]
    }
    result = adapter(lambda _: httpx.Response(200, json=response(json.dumps(payload)))).extract(ctx)
    validated = {s["field"]: s["value"] for s in validate_suggestions(result, ctx)}
    assert validated["date"] == "2026-10-27"
    assert validated["window"] == {"start": "10:00", "end": "12:00"}
    assert validated["items"][0]["amount"] == "2500.00"


@pytest.mark.parametrize(
    "suggestions",
    [
        None,
        [None],
        [{"field": "date", "value_json": "2026-10-27", "confidence": 1, "message_ids": [3]}],
        [{"field": "date", "value": "2026-10-27", "confidence": 1}],
    ],
)
def test_invalid_typed_envelope_is_rejected(suggestions):
    payload = json.dumps({"suggestions": suggestions})
    with pytest.raises(ExtractionUnavailable, match="invalid_result"):
        adapter(lambda _: httpx.Response(200, json=response(payload))).extract(context())


@pytest.mark.parametrize(
    "evidence",
    [None, [], [{"message_id": "3", "quote": "Завтра"}], [{"message_id": 3, "quote": ""}]],
)
def test_invalid_evidence_envelope_is_rejected(evidence):
    payload = json.dumps(
        {
            "suggestions": [
                {"field": "address", "value": "Тестовая 1", "confidence": 1, "evidence": evidence}
            ]
        }
    )
    with pytest.raises(ExtractionUnavailable, match="invalid_result"):
        adapter(lambda _: httpx.Response(200, json=response(payload))).extract(context())


@pytest.mark.parametrize("quote,message_id", [("Адрес: Тестовая 1", 3), ("Завтра", 999)])
def test_unsubstantiated_suggestion_is_dropped(quote, message_id):
    payload = json.dumps(
        {
            "suggestions": [
                {
                    "field": "address",
                    "value": "Тестовая 1",
                    "confidence": 1,
                    "evidence": [{"message_id": message_id, "quote": quote}],
                }
            ]
        }
    )
    result = adapter(lambda _: httpx.Response(200, json=response(payload))).extract(context())
    assert result.suggestions == []


@pytest.mark.parametrize("status", [429, 500, 503, 401, 403, 400])
def test_only_retry_rate_limit_and_server_errors(status, monkeypatch):
    monkeypatch.setattr("tapme.orders.infrastructure.extractors.time.sleep", lambda _: None)
    calls = []

    def handle(request):
        calls.append(request)
        return httpx.Response(status, json={"message": "SECRET-TEST customer phone private text"})

    with pytest.raises(ExtractionUnavailable) as error:
        adapter(handle).extract(context())
    assert str(error.value) == "provider_error"
    assert len(calls) == (2 if status == 429 or status >= 500 else 1)


@pytest.mark.parametrize("bad", ["length", "malformed", "refusal", "timeout", "empty"])
def test_invalid_output_and_timeouts_are_safe(bad):
    calls = []

    def handle(request):
        calls.append(request)
        if bad == "timeout":
            raise httpx.ReadTimeout("private text", request=request)
        data = response()
        if bad == "length":
            data = response(finish="length")
        if bad == "malformed":
            data = response("oops")
        if bad == "refusal":
            data = response("I refuse")
        if bad == "empty":
            data["choices"] = []
        return httpx.Response(200, json=data)

    with pytest.raises(ExtractionUnavailable) as error:
        adapter(handle).extract(context())
    assert "private" not in str(error.value)
    assert len(calls) == 1
