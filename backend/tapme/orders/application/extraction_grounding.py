"""Conservative Russian receiving-time rules and quote grounding; no provider dependencies."""

import json
import re
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from tapme.orders.application.extraction import ExtractionContext, ExtractionResult

TEMPORAL_FIELDS = {"date", "window", "requested_time_text"}
EMPTY_WINDOW = {"start": "", "end": ""}
CANCEL = re.compile(
    r"не\s+(?:оформля\w*|заказыва\w*|нужен|нужна|надо)|отмен\w*\s+заказ|заказ\w*\s+отмен|пока\s+(?:только|узнаю|смотрю|не)|передумал",
    re.I,
)
INTENT = re.compile(
    r"заказ\w*|нуж(?:ен|на|но)|хочу|забер\w*|самовывоз|достав\w*|привез\w*|получ(?:у|ить)|перенес\w*|поправка",
    re.I,
)
AMBIGUOUS = re.compile(r"\bили\b|наверное|возможно|не\s+знаю|не\s+решил", re.I)
CONFIRM = re.compile(
    r"^(?:да|подходит|согласен|согласна|подтверждаю|всё верно|все верно)(?:\W|$)", re.I
)
WEEKDAYS = {
    "понедельник": 0,
    "вторник": 1,
    "среду": 2,
    "четверг": 3,
    "пятницу": 4,
    "субботу": 5,
    "воскресенье": 6,
}
NUMBERS = {
    "один": 1,
    "одну": 1,
    "одна": 1,
    "два": 2,
    "две": 2,
    "три": 3,
    "четыре": 4,
    "пять": 5,
    "шесть": 6,
    "семь": 7,
    "восемь": 8,
    "девять": 9,
    "десять": 10,
}


def folded(value: str) -> str:
    return " ".join(value.casefold().replace("ё", "е").split())


def valid_evidence(evidence: Any, context: ExtractionContext) -> bool:
    sources = {m["id"]: m for m in context.messages}
    return (
        isinstance(evidence, list)
        and 1 <= len(evidence) <= 8
        and all(
            isinstance(e, dict)
            and set(e) == {"message_id", "quote"}
            and type(e["message_id"]) is int
            and e["message_id"] in sources
            and isinstance(e["quote"], str)
            and 1 <= len(e["quote"]) <= 4000
            and bool(e["quote"].strip())
            and folded(e["quote"]) in folded(sources[e["message_id"]]["text"])
            for e in evidence
        )
    )


def _proposal(
    key: str,
    value: Any,
    message: dict[str, Any],
    quote: str,
    confirmations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    evidence = [{"message_id": message["id"], "quote": quote}]
    evidence.extend(confirmations or [])
    return {
        "field": key,
        "value_json": json.dumps(value, ensure_ascii=False),
        "confidence": 1.0,
        "message_ids": [e["message_id"] for e in evidence],
        "evidence": evidence,
    }


def _dates(text: str, anchor: datetime) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    for match in re.finditer(r"\b(сегодня|завтра|послезавтра)\b", text, re.I):
        offset = {"сегодня": 0, "завтра": 1, "послезавтра": 2}[match[0].lower()]
        found.append(((anchor.date() + timedelta(days=offset)).isoformat(), match[0]))
    for match in re.finditer(r"(?<!\d)(\d{4}-\d{2}-\d{2}|\d{1,2}\.\d{1,2}\.\d{4})(?!\d)", text):
        try:
            day = (
                date.fromisoformat(match[0])
                if "-" in match[0]
                else datetime.strptime(match[0], "%d.%m.%Y").date()
            )
            found.append((day.isoformat(), match[0]))
        except ValueError:
            return [("", match[0])]
    for match in re.finditer(
        r"\bв\s+(?:(следующий|следующую|следующее)\s+)?(" + "|".join(WEEKDAYS) + r")\b", text, re.I
    ):
        offset = (WEEKDAYS[match[2].lower()] - anchor.weekday()) % 7
        if match[1]:
            offset = 7 - anchor.weekday() + WEEKDAYS[match[2].lower()]
        found.append(((anchor.date() + timedelta(days=offset)).isoformat(), match[0]))
    return found


def receiving_facts(context: ExtractionContext) -> dict[str, dict[str, Any]]:
    """Only explicit, unambiguous receiving statements; no catalogue defaults."""
    facts: dict[str, dict[str, Any]] = {}
    intent = bool(context.fields.get("items"))
    previous: dict[str, Any] | None = None
    for incoming in context.messages:
        if incoming["direction"] != "in":
            previous = incoming
            continue
        text = incoming["text"]
        if CANCEL.search(text):
            facts.clear()
            intent = False
            previous = incoming
            continue
        message = incoming
        confirmations: list[dict[str, Any]] = []
        if CONFIRM.search(text) and previous and previous["direction"] == "out":
            message = previous
            text = message["text"].rstrip(" ?")
            confirmations = [{"message_id": incoming["id"], "quote": incoming["text"]}]
        preceding = previous
        previous = incoming
        if "?" in text:
            continue
        # Open-card text is literal content, not a receiving instruction.
        receiving = re.split(
            r"(?:на\s+)?открытк\w*\s*[:—-]?|пожелания\s*:", text, maxsplit=1, flags=re.I
        )[0]
        explicit = bool(INTENT.search(receiving))
        if re.search(r"день\s+рождения|родил\w*|годовщин", receiving, re.I) and not re.search(
            r"достав|привез|забер|самовывоз|получ", receiving, re.I
        ):
            continue
        reply = bool(preceding and len(receiving.strip().split()) <= 8)
        time_question = bool(
            preceding
            and preceding["direction"] == "out"
            and re.search(r"когда|какую дату|какое время|во сколько", preceding["text"], re.I)
        )
        if not (explicit or intent and reply or time_question and reply):
            continue
        intent = intent or explicit
        correction = re.search(r"\bне\b.+?[,;]?\s+а\s+(.+)", receiving, re.I)
        if correction:
            receiving = correction[1]
        if AMBIGUOUS.search(receiving) or re.search(
            r"\bне\s+(?:завтра|сегодня|послезавтра|в\s+\d|к\s+\d)", receiving, re.I
        ):
            for key in TEMPORAL_FIELDS:
                facts.pop(key, None)
            continue
        anchor = datetime.fromisoformat(message["at"]).astimezone(ZoneInfo(context.timezone))
        relative = re.search(r"через\s+(?:(\d{1,3})\s+)?(час\w*|минут\w*)", receiving, re.I)
        if relative:
            amount = int(relative[1] or 1)
            if 0 < amount <= (48 if relative[2].lower().startswith("час") else 2880):
                target = anchor + timedelta(
                    minutes=amount * (60 if relative[2].lower().startswith("час") else 1)
                )
                facts["date"] = _proposal(
                    "date", target.date().isoformat(), message, relative[0], confirmations
                )
                facts["requested_time_text"] = _proposal(
                    "requested_time_text",
                    "к " + target.strftime("%H:%M"),
                    message,
                    relative[0],
                    confirmations,
                )
                facts.pop("window", None)
        dates = _dates(receiving, anchor)
        if dates:
            facts.pop("date", None)
            if len({day for day, _ in dates}) == 1 and dates[0][0] >= context.now[:10]:
                facts["date"] = _proposal("date", dates[0][0], message, dates[-1][1], confirmations)
        interval = re.search(
            r"(?<![\d.-])(?:с\s+)?(\d{1,2})(?::(\d{2}))?\s*(?:до|[-–—])\s*(\d{1,2})(?::(\d{2}))?(?!\d|[.-]\d)",
            receiving,
            re.I,
        )
        if interval:
            facts.pop("window", None)
            facts.pop("requested_time_text", None)
            start, end = int(interval[1]), int(interval[3])
            sm, em = int(interval[2] or 0), int(interval[4] or 0)
            window = {"start": f"{start:02}:{sm:02}", "end": f"{end:02}:{em:02}"}
            if (
                start < 24
                and end < 24
                and sm < 60
                and em < 60
                and window in [{"start": w["start"], "end": w["end"]} for w in context.windows]
            ):
                facts["window"] = _proposal("window", window, message, interval[0], confirmations)
        else:
            exact = re.search(
                r"\b(?:к|в|ровно(?:\s+в)?)\s+(\d{1,2})(?::(\d{2}))?(?:\s*(утра|дня|вечера|ночи))?\b(?![\d:]|\.\d)",
                receiving,
                re.I,
            )
            if exact and not re.match(r"\s*(?:квартир|дом|числ)", receiving[exact.end() :], re.I):
                hour, minute = int(exact[1]), int(exact[2] or 0)
                if exact[3] and exact[3].lower() in {"дня", "вечера"} and hour < 12:
                    hour += 12
                if exact[3] and exact[3].lower() == "ночи" and hour == 12:
                    hour = 0
                if hour < 24 and minute < 60:
                    facts["requested_time_text"] = _proposal(
                        "requested_time_text",
                        f"к {hour:02}:{minute:02}",
                        message,
                        exact[0],
                        confirmations,
                    )
                    facts.pop("window", None)
    # An AI-filled old interval must not survive a later exact-time instruction.
    if (
        "requested_time_text" in facts
        and context.fields.get("window", EMPTY_WINDOW) != EMPTY_WINDOW
    ):
        facts["window"] = {
            **facts["requested_time_text"],
            "field": "window",
            "value_json": json.dumps(EMPTY_WINDOW),
        }
    if (
        "window" in facts
        and json.loads(facts["window"]["value_json"]) != EMPTY_WINDOW
        and context.fields.get("requested_time_text")
    ):
        facts["requested_time_text"] = {
            **facts["window"],
            "field": "requested_time_text",
            "value_json": json.dumps(""),
        }
    return facts


def grounded_extraction(result: ExtractionResult, context: ExtractionContext) -> ExtractionResult:
    sources = {m["id"]: m for m in context.messages}
    proposals = []
    latest_in = next((m for m in reversed(context.messages) if m["direction"] == "in"), None)
    if latest_in and CANCEL.search(latest_in["text"]):
        return ExtractionResult([], result.usage)
    for suggestion in result.suggestions:
        key = suggestion["field"]
        if key in TEMPORAL_FIELDS:
            continue  # Model-generated receiving dates/times are never applied.
        evidence = suggestion.get("evidence", [])
        if not valid_evidence(evidence, context):
            continue
        incoming = [
            sources[e["message_id"]]
            for e in evidence
            if sources[e["message_id"]]["direction"] == "in"
        ]
        if not incoming or all("?" in m["text"] or CANCEL.search(m["text"]) for m in incoming):
            continue
        quote = " ".join(e["quote"] for e in evidence)
        source_text = " ".join(sources[e["message_id"]]["text"] for e in evidence)
        value = json.loads(suggestion["value_json"])
        if key == "fulfillment":
            if value == "pickup" and not re.search(r"самовывоз|забер", quote, re.I):
                continue
            if value == "courier" and not re.search(r"достав|привез", quote, re.I):
                continue
        elif key == "items":
            products = {p["id"]: p for p in context.products}
            valid = isinstance(value, list) and bool(value)
            for item in value if isinstance(value, list) else []:
                if not isinstance(item, dict):
                    valid = False
                    continue
                if item.get("kind") == "product":
                    name = products.get(item.get("product_id"), {}).get("name", "")
                    if not name or folded(name) not in folded(quote):
                        valid = False
                    # Multiple units require an explicit count, not a model guess.
                    quantity = item.get("quantity")
                    counts = {int(n) for n in re.findall(r"(?<!\d)\d{1,3}(?!\d)", quote)}
                    counts.update(
                        n
                        for word, n in NUMBERS.items()
                        if re.search(r"\b" + word + r"\b", quote, re.I)
                    )
                    if quantity != 1 and quantity not in counts:
                        valid = False
                elif item.get("kind") == "budget":
                    amount = str(item.get("amount", "")).removesuffix(".00")
                    if amount not in re.sub(r"\s", "", quote) or not re.search(
                        r"бюджет|на\s+\d|до\s+\d", quote, re.I
                    ):
                        valid = False
                    if item.get("description") and folded(item["description"]) not in folded(quote):
                        valid = False
                else:
                    valid = False
            if not valid:
                continue
        elif isinstance(value, str):
            if key == "recipient_phone":
                if re.sub(r"\D", "", value) not in re.sub(r"\D", "", quote):
                    continue
            elif not value.strip() or folded(value) not in folded(quote):
                continue
            if (
                key == "notes"
                and re.search(r"открытк", source_text, re.I)
                and not re.search(r"пожелан|без\s+лилий|упаков", quote, re.I)
            ):
                continue
            if (
                key == "occasion"
                and re.search(r"открытк", source_text, re.I)
                and not re.search(r"повод|день\s+рождения|годовщин|свадьб", source_text, re.I)
            ):
                continue
        else:
            continue
        proposals.append(
            {**suggestion, "message_ids": list(dict.fromkeys(e["message_id"] for e in evidence))}
        )
    proposals.extend(receiving_facts(context).values())
    return ExtractionResult(proposals, result.usage)
