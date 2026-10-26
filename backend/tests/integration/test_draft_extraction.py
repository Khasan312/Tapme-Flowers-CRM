import json
from datetime import timedelta
from unittest.mock import Mock

import pytest
from django.utils import timezone

from config import composition
from tapme.businesses.application.contracts import Scope
from tapme.businesses.models import Membership, Shop
from tapme.messaging.models import ChannelAccount, Conversation, Message
from tapme.orders.application.extraction import ExtractionResult, ExtractionUnavailable
from tapme.orders.infrastructure.extraction import process_draft
from tapme.orders.infrastructure.extractors import DemoChatExtractor, FakeChatExtractor
from tapme.orders.models import OrderDraft, OrderRecord


def suggestion(key, value, message_id):
    return {
        "field": key,
        "value_json": json.dumps(value),
        "confidence": 0.93,
        "message_ids": [message_id],
    }


@pytest.fixture
def extraction(setup, base, settings):
    settings.TAPME_AI_ENABLED = True
    settings.TAPME_AI_MODE = "demo"
    settings.TAPME_META_MODE = "fake"
    settings.DEBUG = True
    channel = ChannelAccount.objects.create(
        business=setup["business"],
        phone_number_id="ai-test",
        provider_mode="fake",
        display_phone="+996700000011",
        token_encrypted="",
    )
    chat = Conversation.objects.create(
        channel=channel, customer=setup["customer"], phone=setup["customer"].phone
    )
    point = Shop.objects.get(business=setup["business"])
    scope = Scope(setup["owner"].id, setup["business"].id, point.id)
    data = composition.drafts().start(scope, chat.id)["draft"]
    row = OrderDraft.objects.get(id=data["id"])
    message = Message.objects.create(
        conversation=chat, direction="in", status="received", text="Завтра. Адрес: Чуй 120"
    )
    Message.objects.filter(id=message.id).update(created_at=timezone.now() - timedelta(seconds=8))
    return row, chat, message, scope, f"{base}/chats/{chat.id}/order-draft/"


def test_extract_apply_review_and_keep_staff_fields(setup, extraction):
    row, chat, message, scope, url = extraction
    service = composition.drafts()
    service.save(scope, chat.id, row.id, row.version, {**row.fields, "address": "Адрес менеджера"})
    row.refresh_from_db()
    process_draft(
        row.id,
        FakeChatExtractor(
            ExtractionResult(
                [
                    suggestion("address", "Нельзя заменить", message.id),
                    suggestion("card_text", "С праздником!", message.id),
                    suggestion(
                        "items",
                        [
                            {
                                "kind": "product",
                                "product_id": str(setup["product"].id),
                                "quantity": 2,
                            }
                        ],
                        message.id,
                    ),
                ]
            )
        ),
    )
    row.refresh_from_db()
    assert row.fields["address"] == "Адрес менеджера"
    assert row.fields["card_text"] == "С праздником!"
    assert row.field_meta["card_text"]["needs_check"]
    assert row.extraction_state["status"] == "applied"
    assert OrderRecord.objects.count() == 0
    assert Message.objects.filter(direction="out").count() == 0
    response = setup["client"].post(
        url + "convert/", {"draft_id": str(row.id), "version": row.version}, format="json"
    )
    assert response.status_code == 400
    assert "Проверьте автозаполнение" in str(response.data)
    result = service.save(scope, chat.id, row.id, row.version, row.fields, ["card_text", "items"])[
        "draft"
    ]
    assert result["field_meta"]["card_text"]["locked"]
    assert not result["field_meta"]["card_text"]["needs_check"]
    assert result["lines"][0]["price"] == str(setup["product"].price)


@pytest.mark.parametrize("manual", [False, True])
@pytest.mark.parametrize(
    "key,empty,value",
    [
        ("address", "", "Чуй 120"),
        ("recipient_name", "", "Айдана"),
        ("recipient_phone", "", "+996700123456"),
        ("recipient_phone", "+", "+996700123456"),
        ("recipient_phone", "+996", "+996700123456"),
        ("window", {"start": "", "end": ""}, {"start": "10:00", "end": "12:00"}),
        ("items", [], [{"kind": "budget", "amount": "2500.00", "description": "Букет"}]),
    ],
)
def test_only_manual_refresh_refills_cleared_fields(extraction, manual, key, empty, value):
    row, chat, message, scope, url = extraction
    service = composition.drafts()
    saved = service.save(scope, chat.id, row.id, row.version, {**row.fields, key: value})["draft"]
    saved = service.save(scope, chat.id, row.id, saved["version"], {**saved["fields"], key: empty})[
        "draft"
    ]
    assert saved["field_meta"][key]["locked"]
    if manual:
        service.extract(scope, chat.id, row.id, saved["version"])
    process_draft(row.id, FakeChatExtractor(ExtractionResult([suggestion(key, value, message.id)])))
    row.refresh_from_db()
    assert row.fields[key] == (value if manual else saved["fields"][key])
    assert row.field_meta[key]["locked"] is not manual
    assert row.field_meta[key]["needs_check"] is manual
    assert row.version == saved["version"] + int(manual)
    assert OrderRecord.objects.count() == 0
    assert Message.objects.filter(direction="out").count() == 0


def test_manual_refill_keeps_filled_and_partial_staff_fields(extraction):
    row, chat, message, scope, url = extraction
    service = composition.drafts()
    fields = {
        **row.fields,
        "address": "Мой адрес",
        "recipient_phone": "+996700",
        "window": {"start": "11:00", "end": ""},
        "recipient_name": "",
    }
    saved = service.save(scope, chat.id, row.id, row.version, fields, ["recipient_name"])["draft"]
    service.extract(scope, chat.id, row.id, saved["version"])
    process_draft(
        row.id,
        FakeChatExtractor(
            ExtractionResult(
                [
                    suggestion("address", "Другой адрес", message.id),
                    suggestion("recipient_phone", "+996700123456", message.id),
                    suggestion("window", {"start": "10:00", "end": "12:00"}, message.id),
                    suggestion("recipient_name", "Айдана", message.id),
                ]
            )
        ),
    )
    row.refresh_from_db()
    for key in ("address", "recipient_phone", "window"):
        assert row.fields[key] == fields[key]
        assert row.field_meta[key]["locked"]
    assert row.fields["recipient_name"] == "Айдана"
    assert row.extraction_state["changed_fields"] == ["recipient_name"]


@pytest.mark.parametrize("manual", [False, True])
def test_refill_previously_saved_plus_only_phone(extraction, manual):
    row, chat, message, scope, url = extraction
    # Existing drafts may contain a plus saved before empty-phone normalization.
    row.fields["recipient_phone"] = "+"
    row.field_meta["recipient_phone"] = {"source": "staff", "locked": True, "needs_check": False}
    row.save(update_fields=["fields", "field_meta"])
    if manual:
        composition.drafts().extract(scope, chat.id, row.id, row.version)
    process_draft(
        row.id,
        FakeChatExtractor(
            ExtractionResult(
                [
                    suggestion("recipient_phone", "+996700123456", message.id),
                ]
            )
        ),
    )
    row.refresh_from_db()
    assert row.fields["recipient_phone"] == ("+996700123456" if manual else "+")
    assert row.field_meta["recipient_phone"]["locked"] is not manual
    assert row.field_meta["recipient_phone"]["needs_check"] is manual


@pytest.mark.parametrize("outcome", ["failure", "staff_edit"])
def test_manual_refill_failure_or_concurrent_edit_keeps_protection(extraction, outcome):
    row, chat, message, scope, url = extraction
    service = composition.drafts()
    saved = service.save(scope, chat.id, row.id, row.version, row.fields, ["address"])["draft"]
    service.extract(scope, chat.id, row.id, saved["version"])

    def extract(context):
        if outcome == "failure":
            raise ExtractionUnavailable("timeout")
        service.save(scope, chat.id, row.id, saved["version"], {**row.fields, "address": "Вручную"})
        return ExtractionResult([suggestion("address", "Чуй 120", message.id)])

    process_draft(row.id, Mock(extract=extract))
    row.refresh_from_db()
    assert row.fields["address"] == ("" if outcome == "failure" else "Вручную")
    assert row.field_meta["address"]["locked"]
    assert row.extraction_state["status"] == ("failed" if outcome == "failure" else "stale")


@pytest.mark.parametrize(
    "change",
    [
        "staff",
        "new_message",
        "point",
        "converted",
        "archived",
        "revoked",
        "customer",
        "window",
        "product",
        "timezone",
        "inactive_point",
    ],
)
def test_stale_response_cannot_overwrite(setup, extraction, change):
    row, chat, message, scope, url = extraction
    if change == "inactive_point":
        point = Shop.objects.create(
            business=setup["business"], name="Второй филиал", is_primary=False
        )
        row.fields["point_id"] = str(point.id)
        row.save(update_fields=["fields"])
        scope = Scope(scope.user_id, scope.business_id, point.id)
    before = dict(row.fields)

    def extract(context):
        if change == "staff":
            composition.drafts().save(
                scope, chat.id, row.id, row.version, {**row.fields, "address": "Ручная правка"}
            )
        elif change == "new_message":
            Message.objects.create(
                conversation=chat, direction="in", text="Изменение", status="received"
            )
        elif change == "point":
            OrderDraft.objects.filter(id=row.id).update(fields={**row.fields, "point_id": ""})
        elif change == "converted":
            OrderDraft.objects.filter(id=row.id).update(status="converted")
        elif change == "archived":
            Conversation.objects.filter(id=chat.id).update(mode="closed")
        elif change == "revoked":
            Membership.objects.filter(user=setup["owner"], business=setup["business"]).update(
                is_active=False
            )
        elif change == "customer":
            Conversation.objects.filter(id=chat.id).update(customer=setup["other_customer"])
        elif change == "window":
            Shop.objects.filter(id=scope.point_id).update(delivery_windows=[])
        elif change == "timezone":
            setup["business"].timezone = "UTC"
            setup["business"].save()
        elif change == "inactive_point":
            Shop.objects.filter(id=scope.point_id).update(active=False)
        elif change == "product":
            setup["product"].active = False
            setup["product"].save()
        return ExtractionResult(
            [
                suggestion("address", "Ответ ИИ", message.id),
                suggestion(
                    "items",
                    [{"kind": "product", "product_id": str(setup["product"].id), "quantity": 1}],
                    message.id,
                ),
            ]
        )

    process_draft(row.id, Mock(extract=extract))
    row.refresh_from_db()
    assert row.extraction_state["status"] == "stale"
    assert row.fields["address"] != "Ответ ИИ"
    assert row.fields["items"] == before["items"]


@pytest.mark.parametrize(
    "bad", ["source", "price", "foreign_product", "field", "nan", "date", "shape", "window"]
)
def test_reject_entire_invalid_response(setup, extraction, bad):
    row, chat, message, scope, url = extraction
    candidate = suggestion("address", "Не применять", message.id)
    if bad == "source":
        candidate["message_ids"] = [999999]
    if bad == "price":
        candidate = suggestion(
            "items",
            [
                {
                    "kind": "product",
                    "product_id": str(setup["product"].id),
                    "quantity": 1,
                    "price": "1",
                }
            ],
            message.id,
        )
    if bad == "foreign_product":
        candidate = suggestion(
            "items",
            [{"kind": "product", "product_id": str(setup["other_product"].id), "quantity": 1}],
            message.id,
        )
    if bad == "field":
        candidate["field"] = "paid_amount"
    if bad == "nan":
        candidate["confidence"] = float("nan")
    if bad == "date":
        candidate = suggestion("date", "2000-01-01", message.id)
    if bad == "shape":
        candidate["value_json"] = "{broken"
    if bad == "window":
        candidate = suggestion("window", {"start": "01:00", "end": "02:00"}, message.id)
    process_draft(
        row.id,
        FakeChatExtractor(
            ExtractionResult([suggestion("notes", "Не сохранять частично", message.id), candidate])
        ),
    )
    row.refresh_from_db()
    assert row.extraction_state["status"] == "failed"
    assert row.fields["notes"] == ""
    assert row.fields["address"] == ""
    assert row.version == 1


def test_debounce_and_no_duplicate_calls(extraction):
    row, chat, message, scope, url = extraction
    Message.objects.filter(id=message.id).update(created_at=timezone.now())
    extractor = Mock(extract=Mock(return_value=ExtractionResult([])))
    process_draft(row.id, extractor)
    extractor.extract.assert_not_called()
    Message.objects.filter(id=message.id).update(created_at=timezone.now() - timedelta(seconds=6))
    process_draft(row.id, extractor)
    process_draft(row.id, extractor)
    assert extractor.extract.call_count == 1


def test_parallel_claim_and_timeout_recovery(extraction):
    row, chat, message, scope, url = extraction
    other = Mock()

    def extract(context):
        process_draft(row.id, other)
        other.extract.assert_not_called()
        raise ExtractionUnavailable("provider_unavailable")

    process_draft(row.id, Mock(extract=extract))
    row.refresh_from_db()
    assert row.extraction_state["status"] == "failed"
    row.extraction_state = {
        "status": "running",
        "at": (timezone.now() - timedelta(minutes=2)).isoformat(),
        "last_message_id": message.id,
    }
    row.save()
    process_draft(row.id, other)
    other.extract.assert_not_called()
    row.refresh_from_db()
    assert row.extraction_state["error"] == "interrupted"


@pytest.mark.parametrize("who", ["florist", "other_owner"])
def test_api_permissions(setup, extraction, who):
    row, chat, message, scope, url = extraction
    setup["client"].force_login(setup[who])
    response = setup["client"].post(
        url + "extract/", {"draft_id": str(row.id), "version": row.version}, format="json"
    )
    assert response.status_code == 403


def test_manual_request_version_and_retry(setup, extraction):
    row, chat, message, scope, url = extraction
    response = setup["client"].post(
        url + "extract/", {"draft_id": str(row.id), "version": 999}, format="json"
    )
    assert response.status_code == 409
    response = setup["client"].post(
        url + "extract/", {"draft_id": str(row.id), "version": row.version}, format="json"
    )
    assert response.status_code == 200
    assert response.data["draft"]["extraction"]["status"] == "pending"
    process_draft(row.id, FakeChatExtractor(ExtractionResult([])))
    response = setup["client"].post(
        url + "extract/", {"draft_id": str(row.id), "version": row.version}, format="json"
    )
    assert response.status_code == 400


@pytest.mark.parametrize(
    "disabled", ["off", "production_demo", "live_channel", "missing_key", "invalid_mode"]
)
def test_disabled_never_calls_provider(extraction, settings, disabled):
    row, chat, message, scope, url = extraction
    if disabled == "off":
        settings.TAPME_AI_ENABLED = False
    if disabled == "production_demo":
        settings.DEBUG = False
    if disabled == "live_channel":
        ChannelAccount.objects.filter(id=chat.channel_id).update(provider_mode="live")
    if disabled == "missing_key":
        settings.TAPME_AI_MODE = "mistral"
        settings.MISTRAL_API_KEY = ""
    if disabled == "invalid_mode":
        settings.TAPME_AI_MODE = "other"
    extractor = Mock()
    process_draft(row.id, extractor)
    extractor.extract.assert_not_called()


def test_context_scoped_bounded_and_demo(extraction, setup):
    row, chat, message, scope, url = extraction
    Message.objects.filter(id=message.id).update(
        text=f"{setup['product'].name}; завтра; доставка; 10:00–12:00; Адрес: Чуй 120; Получатель: Айдана; Телефон получателя: +996700123456; Открытка: С праздником!"
    )
    old = Message.objects.create(
        conversation=chat, direction="in", text="OLD PRIVATE", status="received"
    )
    Message.objects.filter(id=old.id).update(created_at=timezone.now() - timedelta(days=8))
    Message.objects.create(
        conversation=chat, direction="out", text="AUTO", status="sent", automated=True
    )

    def extract(context):
        assert [m["id"] for m in context.messages] == [message.id]
        assert str(setup["other_product"].id) not in str(context.products)
        assert context.timezone == setup["business"].timezone
        return DemoChatExtractor().extract(context)

    process_draft(row.id, Mock(extract=extract))
    row.refresh_from_db()
    assert row.extraction_state["status"] == "applied"
    assert row.fields["address"] == "Чуй 120"
    assert row.fields["recipient_name"] == "Айдана"
    assert row.fields["date"] > timezone.now().date().isoformat()
    assert row.fields["items"][0]["product_id"] == str(setup["product"].id)


@pytest.mark.parametrize(
    "restriction", ["allowed", "other_chat", "live_channel", "live_meta", "production"]
)
def test_mistral_trial_only_calls_one_local_fake_chat(extraction, settings, setup, restriction):
    row, chat, message, scope, url = extraction
    settings.TAPME_AI_MODE = "mistral"
    settings.MISTRAL_API_KEY = "TEST-KEY"
    settings.TAPME_AI_TEST_CHAT_ID = str(chat.id)
    if restriction == "other_chat":
        settings.TAPME_AI_TEST_CHAT_ID = "00000000-0000-4000-8000-000000000001"
    elif restriction == "live_channel":
        ChannelAccount.objects.filter(id=chat.channel_id).update(provider_mode="live")
    elif restriction == "live_meta":
        settings.TAPME_META_MODE = "live"
    elif restriction == "production":
        settings.DEBUG = False
    extractor = Mock(extract=Mock(return_value=ExtractionResult([])))
    before = (row.fields.copy(), row.version)
    process_draft(row.id, extractor)
    row.refresh_from_db()
    if restriction == "allowed":
        extractor.extract.assert_called_once()
        assert row.extraction_state["mode"] == "mistral"
    else:
        extractor.extract.assert_not_called()
        assert (row.fields, row.version) == before
        response = setup["client"].post(
            url + "extract/", {"draft_id": str(row.id), "version": row.version}, format="json"
        )
        assert response.status_code == 400
        assert "для этого диалога" in str(response.data)


def test_unchanged_staff_field_can_be_locked(extraction):
    row, chat, message, scope, url = extraction
    composition.drafts().save(scope, chat.id, row.id, row.version, row.fields, ["recipient_name"])
    process_draft(
        row.id,
        FakeChatExtractor(
            ExtractionResult([suggestion("recipient_name", "Новый получатель", message.id)])
        ),
    )
    row.refresh_from_db()
    assert row.fields["recipient_name"] != "Новый получатель"
    assert row.field_meta["recipient_name"]["locked"]


def test_expired_request_cannot_apply_late_result(extraction):
    row, chat, message, scope, url = extraction

    def extract(context):
        current = OrderDraft.objects.get(id=row.id)
        current.extraction_state["status"] = "failed"
        current.extraction_state["error"] = "interrupted"
        current.save(update_fields=["extraction_state"])
        return ExtractionResult([suggestion("address", "Late result", message.id)])

    process_draft(row.id, Mock(extract=extract))
    row.refresh_from_db()
    assert row.fields["address"] == ""
    assert row.extraction_state["status"] == "failed"


def test_context_only_last_40_messages(extraction):
    row, chat, message, scope, url = extraction
    rows = [
        Message(conversation=chat, direction="in", status="received", text=str(i))
        for i in range(45)
    ]
    Message.objects.bulk_create(rows)
    Message.objects.filter(conversation=chat).update(
        created_at=timezone.now() - timedelta(seconds=8)
    )

    def extract(context):
        assert len(context.messages) == 40
        assert context.messages[0]["text"] == "5"
        assert context.messages[-1]["text"] == "44"
        return ExtractionResult([])

    process_draft(row.id, Mock(extract=extract))
    row.refresh_from_db()
    assert row.extraction_state["status"] == "applied"


@pytest.mark.parametrize("locked", [False, True])
def test_grounded_exact_time_keeps_review_and_staff_window_lock(extraction, locked):
    from tapme.orders.application.extraction_grounding import grounded_extraction

    row, chat, message, scope, url = extraction
    Message.objects.filter(id=message.id).update(text="Нужна доставка завтра к 15:00.")
    row.fields["window"] = {"start": "10:00", "end": "12:00"}
    row.field_meta["window"] = {"source": "staff" if locked else "mistral", "locked": locked}
    row.save(update_fields=["fields", "field_meta"])
    process_draft(
        row.id, Mock(extract=lambda context: grounded_extraction(ExtractionResult([]), context))
    )
    row.refresh_from_db()
    assert row.extraction_state["status"] == "applied"
    assert row.fields["requested_time_text"] == "к 15:00"
    assert row.field_meta["requested_time_text"]["needs_check"]
    assert row.field_meta["requested_time_text"]["evidence"] == [
        {"message_id": message.id, "quote": "к 15:00"}
    ]
    assert row.fields["window"] == (
        {"start": "10:00", "end": "12:00"} if locked else {"start": "", "end": ""}
    )
    assert OrderRecord.objects.count() == 0
    assert Message.objects.filter(direction="out").count() == 0


def test_unverified_quote_cannot_be_applied_to_draft(extraction):
    row, chat, message, scope, url = extraction
    before = dict(row.fields)
    fake = suggestion("address", "Выдуманный адрес", message.id)
    fake["evidence"] = [{"message_id": message.id, "quote": "Этого текста нет в переписке"}]
    process_draft(row.id, FakeChatExtractor(ExtractionResult([fake])))
    row.refresh_from_db()
    assert row.extraction_state["status"] == "failed"
    assert row.extraction_state["error"] == "invalid_result"
    assert row.fields == before
