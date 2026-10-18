"""Messages in an isolated E2E business only. Never contacts Meta or real clients."""

import json
import os
import sys
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django  # noqa: E402

django.setup()

from django.db import transaction  # noqa: E402
from django.utils import timezone  # noqa: E402

from tapme.businesses.models import Business  # noqa: E402
from tapme.customers.models import CustomerRecord, ImportantDateRecord  # noqa: E402
from tapme.messaging.infrastructure.processing import delivery_status, incoming  # noqa: E402
from tapme.messaging.models import ChannelAccount, Conversation, Message  # noqa: E402

data = json.load(sys.stdin)
with transaction.atomic():
    business = Business.objects.get(id=data["business_id"], name__startswith="E2E ")
    assert business.memberships.filter(user__username=data["username"], role="owner").exists()
    if sys.argv[1] == "seed":
        channel = ChannelAccount.objects.create(
            business=business,
            phone_number_id=str(uuid4().int)[:18],
            display_phone="+996555000000",
            display_name="Тестовый магазин",
            token_encrypted="",
        )
        customer = CustomerRecord.objects.create(
            business=business,
            name="Алина Садыкова",
            phone="+996555120400",
            tags=["VIP"],
            notes="Любит светлые букеты. Без лилий.",
        )
        ImportantDateRecord.objects.create(
            customer=customer, label="День рождения мамы", person="Айжан", month=10, day=18
        )
        chat = Conversation.objects.create(
            channel=channel,
            customer=customer,
            phone=customer.phone,
            last_inbound_at=timezone.now(),
            waiting_since=timezone.now(),
            last_message_preview="Хочу первый букет. Можно добавить открытку?",
        )
        for i in range(65):
            Message.objects.create(
                conversation=chat,
                direction="out" if i % 3 == 1 else "in",
                status="read" if i % 3 == 1 else "received",
                text=f"Сообщение {i + 1}. "
                + (
                    "Конечно, подберём нежный букет и доставим в удобное время."
                    if i % 3 == 1
                    else "Здравствуйте! Нужен букет из пионов для мамы."
                ),
                happened_at=timezone.now() - timedelta(minutes=65 - i),
            )
        other = CustomerRecord.objects.create(
            business=business, name="Мария Ким", phone="+996555120401"
        )
        second = Conversation.objects.create(
            channel=channel,
            customer=other,
            phone=other.phone,
            last_message_preview="Спасибо!",
            last_inbound_at=timezone.now() - timedelta(days=2),
        )
        Message.objects.create(
            conversation=second, direction="in", status="received", text="Спасибо!"
        )
        print(
            json.dumps(
                {
                    "chat_id": str(chat.id),
                    "other_chat_id": str(second.id),
                    "customer_id": str(customer.id),
                }
            )
        )
    elif sys.argv[1] == "inbound":
        chat = Conversation.objects.get(id=data["chat_id"], channel__business=business)
        incoming(
            chat.channel,
            {
                "id": str(uuid4()),
                "from": chat.phone.lstrip("+"),
                "type": "text",
                "text": {"body": data["text"]},
                "timestamp": str(int(timezone.now().timestamp())),
            },
            {},
        )
        print("{}")
    elif sys.argv[1] == "ack":
        row = Message.objects.filter(
            conversation_id=data["chat_id"],
            conversation__channel__business=business,
            direction="out",
            sender__isnull=False,
        ).latest("id")
        delivery_status(
            row.conversation.channel,
            {
                "id": "e2e-" + str(uuid4()),
                "status": "read",
                "biz_opaque_callback_data": str(row.delivery_key),
                "recipient_id": row.conversation.phone.lstrip("+"),
            },
        )
        print(
            json.dumps(
                {
                    "count": Message.objects.filter(
                        conversation=row.conversation, text=row.text
                    ).count()
                }
            )
        )
