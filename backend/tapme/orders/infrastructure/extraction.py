"""Durable debouncing, short DB locks and optimistic application of AI results."""

import logging
import time
from datetime import datetime, timedelta
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from tapme.businesses.application.contracts import OFFICE_ROLES, Scope, authorize
from tapme.businesses.infrastructure.access import DjangoMembershipReader
from tapme.businesses.models import Shop
from tapme.catalog.models import ProductRecord
from tapme.messaging.models import Conversation, Message
from tapme.orders.application.draft_rules import recipient_phone_is_empty
from tapme.orders.application.extraction import (
    ExtractionContext,
    ExtractionUnavailable,
    validate_suggestions,
)
from tapme.orders.models import OrderDraft
from tapme.shared.domain import Conflict, Forbidden, InvalidInput, NotFound

logger = logging.getLogger(__name__)


def availability(channel, chat_id=None):
    if not settings.TAPME_AI_ENABLED:
        return "disabled"
    if settings.TAPME_AI_MODE == "demo":
        return (
            "demo"
            if settings.DEBUG
            and settings.TAPME_META_MODE == "fake"
            and channel.provider_mode == "fake"
            else "disabled"
        )
    if settings.TAPME_AI_MODE == "mistral" and settings.MISTRAL_API_KEY:
        if settings.TAPME_AI_TEST_CHAT_ID and not (
            settings.DEBUG
            and settings.TAPME_META_MODE == "fake"
            and channel.provider_mode == "fake"
            and str(chat_id) == settings.TAPME_AI_TEST_CHAT_ID
        ):
            return "disabled"
        return "mistral"
    return "unconfigured"


def public_state(row):
    mode = availability(row.conversation.channel, row.conversation_id)
    state = row.extraction_state
    return {
        "mode": mode,
        "status": state.get("status", "idle"),
        "error": state.get("error", ""),
        "updated_at": state.get("at"),
        "changed_fields": state.get("changed_fields", []),
    }


def messages(row):
    # Never reuse the previous order's negotiation when starting a new draft.
    previous = (
        OrderDraft.objects.filter(conversation_id=row.conversation_id, status="converted")
        .order_by("-updated_at")
        .first()
    )
    cutoff = timezone.now() - timedelta(days=7)
    if previous:
        cutoff = max(cutoff, previous.updated_at)
    return (
        Message.objects.filter(
            conversation_id=row.conversation_id,
            direction__in=["in", "out"],
            automated=False,
            created_at__gte=cutoff,
        )
        .exclude(status__in=["failed", "unknown"])
        .order_by("-id")
    )


def request_extraction(repository, scope, chat_id, draft_id, version):
    reader = DjangoMembershipReader()
    authorize(reader, scope, OFFICE_ROLES)
    with transaction.atomic():
        chat = repository._chat(scope, chat_id, True)
        repository._editable(chat)
        row = repository._draft(scope, chat_id, draft_id, version)
        if row.status != "active" or row.customer_id != chat.customer_id:
            raise Conflict("Откройте актуальный черновик.")
        if availability(chat.channel, chat.id) not in {"demo", "mistral"}:
            raise InvalidInput("Автозаполнение не подключено для этого диалога.")
        point = row.fields.get("point_id")
        if not point:
            raise InvalidInput("Сначала выберите точку и сохраните черновик.")
        reader.order_point(scope, UUID(point))
        latest = messages(row).first()
        if not latest:
            raise InvalidInput("Нет свежих сообщений для разбора.")
        state = row.extraction_state
        if (
            state.get("status") in {"pending", "running"}
            and state.get("at")
            and datetime.fromisoformat(state["at"]) > timezone.now() - timedelta(seconds=90)
        ):
            return repository._data(scope, row)
        if state.get("at") and datetime.fromisoformat(state["at"]) > timezone.now() - timedelta(
            seconds=10
        ):
            raise InvalidInput("Подождите несколько секунд перед повторным разбором.")
        row.extraction_actor_id = scope.user_id
        row.extraction_state = {
            "status": "pending",
            "refill_empty": True,
            "at": timezone.now().isoformat(),
        }
        row.save(update_fields=["extraction_actor", "extraction_state"])
        return repository._data(scope, row)


def _context(row, shop):
    zone = ZoneInfo(row.business.timezone)
    recent = list(messages(row)[:40])
    # A bounded payload; overlong conversations stay manual instead of silently truncating facts.
    if sum(len(m.text) for m in recent) > 80000:
        raise ExtractionUnavailable("context_too_large")
    context = ExtractionContext(
        messages=[
            {
                "id": m.id,
                "direction": m.direction,
                "text": m.text,
                "at": m.happened_at.astimezone(zone).isoformat(),
            }
            for m in reversed(recent)
        ],
        fields=row.fields,
        now=timezone.now().astimezone(zone).isoformat(),
        timezone=str(zone),
        products=list(
            ProductRecord.objects.filter(business_id=row.business_id, active=True, system_kind="")
            .order_by("name", "id")
            .values("id", "name", "price")[:500]
        ),
        windows=shop.delivery_windows,
    )
    for product in context.products:
        product["id"], product["price"] = str(product["id"]), str(product["price"])
    return context


def process_draft(draft_id, extractor=None):
    from config import composition

    reference = OrderDraft.objects.filter(id=draft_id).values("conversation_id").first()
    if not reference:
        return
    token = str(uuid4())
    with transaction.atomic():
        chat = (
            Conversation.objects.select_for_update()
            .select_related("channel")
            .filter(id=reference["conversation_id"])
            .first()
        )
        if chat is None:
            return
        row = (
            OrderDraft.objects.select_for_update()
            .select_related("business")
            .filter(id=draft_id)
            .first()
        )
        if (
            not row
            or row.status != "active"
            or chat.mode != "human"
            or chat.needs_customer_link
            or row.customer_id != chat.customer_id
            or not row.extraction_actor_id
        ):
            return
        mode = availability(chat.channel, chat.id)
        if mode not in {"demo", "mistral"}:
            return
        point = row.fields.get("point_id")
        if not point:
            return
        scope = Scope(row.extraction_actor_id, row.business_id, UUID(point))
        reader = DjangoMembershipReader()
        try:
            authorize(reader, scope, OFFICE_ROLES)
            reader.order_point(scope, scope.point_id)
        except (Forbidden, NotFound, InvalidInput):
            return
        latest = messages(row).first()
        if not latest:
            return
        state = row.extraction_state
        if state.get("status") == "running":
            if datetime.fromisoformat(state["at"]) > timezone.now() - timedelta(seconds=90):
                return
            # An interrupted request may have been billed; do not silently repeat it.
            row.extraction_state = {**state, "status": "failed", "error": "interrupted"}
            row.save(update_fields=["extraction_state"])
            return
        if state.get("status") != "pending" and state.get("last_message_id") == latest.id:
            return
        if latest.created_at > timezone.now() - timedelta(seconds=4):
            return
        shop = Shop.objects.get(id=point, business_id=row.business_id, active=True)
        try:
            context = _context(row, shop)
        except ExtractionUnavailable as exc:
            row.extraction_state = {
                "status": "failed",
                "error": str(exc),
                "last_message_id": latest.id,
                "at": timezone.now().isoformat(),
            }
            row.save(update_fields=["extraction_state"])
            return
        version, cursor, customer_id = row.version, latest.id, row.customer_id
        refill_empty = state.get("status") == "pending" and state.get("refill_empty") is True
        windows = shop.delivery_windows
        actor_id = row.extraction_actor_id
        row.extraction_state = {
            "status": "running",
            "token": token,
            "mode": mode,
            "last_message_id": cursor,
            "at": timezone.now().isoformat(),
        }
        row.save(update_fields=["extraction_state"])
    started = time.monotonic()
    error, suggestions, usage = "", [], {}
    try:
        result = (extractor or composition.chat_extractor()).extract(context)
        suggestions = validate_suggestions(result, context)
        usage = result.usage
    except ExtractionUnavailable as exc:
        error = str(exc)
    except Exception:
        error = "unexpected_error"
    with transaction.atomic():
        chat = (
            Conversation.objects.select_for_update()
            .select_related("channel")
            .filter(id=reference["conversation_id"])
            .first()
        )
        if chat is None:
            return
        row = OrderDraft.objects.select_for_update().filter(id=draft_id).first()
        if (
            not row
            or row.extraction_state.get("token") != token
            or row.extraction_state.get("status") != "running"
        ):
            return
        latest = messages(row).first()
        valid = (
            row.status == "active"
            and row.version == version
            and latest
            and latest.id == cursor
            and chat.mode == "human"
            and not chat.needs_customer_link
            and chat.customer_id == customer_id
            and row.fields.get("point_id") == point
            and row.extraction_actor_id == actor_id
            and availability(chat.channel, chat.id) == mode
            and row.business.timezone == context.timezone
        )
        current_shop = Shop.objects.filter(
            id=point, active=True, business_id=row.business_id
        ).first()
        valid = valid and current_shop and current_shop.delivery_windows == windows
        try:
            authorize(reader, scope, OFFICE_ROLES)
            reader.order_point(scope, scope.point_id)
        except (Forbidden, NotFound, InvalidInput):
            valid = False
        if valid and not error:
            # Catalogue changes during the request invalidate proposed items as well.
            current_products = {
                str(p)
                for p in ProductRecord.objects.filter(
                    business_id=row.business_id, active=True, system_kind=""
                ).values_list("id", flat=True)
            }
            valid = all(
                item["product_id"] in current_products
                for s in suggestions
                if s["field"] == "items"
                for item in s["value"]
                if item["kind"] == "product"
            )
        changed = []
        if valid and not error:
            for suggestion in suggestions:
                key = suggestion["field"]
                if (
                    row.field_meta.get(key, {}).get("locked")
                    and not (refill_empty and _empty_field(key, row.fields.get(key)))
                ) or row.fields.get(key) == suggestion["value"]:
                    continue
                row.fields[key] = suggestion["value"]
                row.field_meta[key] = {
                    "source": mode,
                    "locked": False,
                    "needs_check": True,
                    "confidence": suggestion["confidence"],
                    "message_ids": suggestion["message_ids"],
                    **({"evidence": suggestion["evidence"]} if "evidence" in suggestion else {}),
                }
                changed.append(key)
            if changed:
                row.version += 1
        status = "stale" if not valid else "failed" if error else "applied"
        row.extraction_state = {
            "status": status,
            "mode": mode,
            "last_message_id": cursor,
            "error": error,
            "changed_fields": changed,
            "at": timezone.now().isoformat(),
            "usage": usage,
        }
        row.save(
            update_fields=["fields", "field_meta", "version", "extraction_state", "updated_at"]
        )
    logger.info(
        "draft_extraction status=%s mode=%s duration_ms=%s",
        status,
        mode,
        round((time.monotonic() - started) * 1000),
    )


def _empty_field(key, value):
    # A manual refresh may refill cleared fields, never partially entered values.
    if key == "window":
        return value == {"start": "", "end": ""}
    if key == "items":
        return value == []
    if key == "recipient_phone" and isinstance(value, str):
        return recipient_phone_is_empty(value)
    return value is None or (isinstance(value, str) and not value.strip())
