from datetime import date, time, timedelta
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from django.db import transaction
from django.utils import timezone

from tapme.businesses.models import Shop
from tapme.catalog.models import ProductRecord
from tapme.messaging.models import Conversation, Message
from tapme.orders.application.draft_rules import (
    missing_fields,
    normalize_fields,
    payment_deadline,
    receiving_at,
)
from tapme.orders.application.services import CreateOrder, ItemInput
from tapme.orders.application.workflow import ensure_version
from tapme.orders.domain import Fulfillment, OrderLine
from tapme.orders.infrastructure.repository import DjangoOrderRepository
from tapme.orders.models import OrderDraft
from tapme.shared.domain import Conflict, InvalidInput, NotFound, text


class DjangoDraftRepository:
    def __init__(self, order_service):
        self.orders = order_service

    def extract(self, scope, chat_id, draft_id, version):
        from tapme.orders.infrastructure.extraction import request_extraction

        return request_extraction(self, scope, chat_id, draft_id, version)

    def _chat(self, scope, chat_id, lock=False):
        query = Conversation.objects.filter(id=chat_id, channel__business_id=scope.business_id)
        if lock:
            query = query.select_for_update(of=("self",))
        chat = query.select_related("customer", "channel__business").first()
        if not chat:
            raise NotFound("Диалог не найден.")
        return chat

    def _editable(self, chat):
        if not chat.customer_id or chat.needs_customer_link:
            raise InvalidInput("Сначала выберите клиента для этого диалога.")
        if chat.mode != "human":
            raise InvalidInput("Сначала откройте диалог.")

    def _draft(self, scope, chat_id, draft_id, version):
        row = (
            OrderDraft.objects.select_for_update()
            .filter(id=draft_id, business_id=scope.business_id, conversation_id=chat_id)
            .first()
        )
        if not row:
            raise NotFound("Черновик не найден.")
        if row.status != "converted" and row.version != version:
            raise Conflict(
                "Черновик изменён в другой вкладке. Ваши правки сохранены в форме; загрузите актуальный черновик перед повторным сохранением."
            )
        return row

    def _products(self, scope, fields):
        ids = [i["product_id"] for i in fields["items"] if i["kind"] == "product"]
        products = {
            str(p.id): p
            for p in ProductRecord.objects.filter(
                business_id=scope.business_id, id__in=ids, system_kind=""
            )
        }
        if len(products) != len(ids):
            raise InvalidInput("Позиция не найдена в прайсе этого магазина.")
        return products

    def _data(self, scope, row):
        if row is None:
            return {"draft": None}
        from tapme.orders.infrastructure.extraction import public_state

        fields = normalize_fields(row.fields)
        products = self._products(scope, fields)
        missing = missing_fields(fields)
        lines = []
        for item in fields["items"]:
            if item["kind"] == "product":
                p = products[item["product_id"]]
                if not p.active:
                    missing.append(f"Замените скрытую позицию: {p.name}")
                name, price, quantity = p.name, p.price, item["quantity"]
            else:
                name, price, quantity = "Букет по бюджету", Decimal(item["amount"]), 1
            lines.append(
                {
                    "name": name,
                    "price": str(price),
                    "quantity": quantity,
                    "total": str(price * quantity),
                }
            )
        from tapme.businesses.infrastructure.access import DjangoMembershipReader

        available = DjangoMembershipReader().points(scope).filter(active=True)
        selected = fields.get("point_id")
        shop = available.filter(id=selected).first() if selected else None
        if (
            not selected
            and Shop.objects.filter(business_id=scope.business_id, active=True).count() == 1
        ):
            shop = available.first()
        if shop is None:
            missing.append("Выберите доступную точку заказа")
        elif not selected:
            fields["point_id"] = str(shop.id)
        window = next(
            (
                w
                for w in (shop.delivery_windows if shop else [])
                if w["start"] == fields["window"]["start"] and w["end"] == fields["window"]["end"]
            ),
            None,
        )
        if fields["fulfillment"] == "courier" and all(fields["window"].values()) and not window:
            missing.append("Выберите действующее окно доставки")
        fee = (
            Decimal(window.get("price", "0"))
            if window and fields["fulfillment"] == "courier"
            else Decimal("0")
        )
        total = sum((Decimal(i["total"]) for i in lines), fee)
        return {
            "draft": {
                "id": str(row.id),
                "version": row.version,
                "status": row.status,
                "fields": fields,
                "field_meta": row.field_meta,
                "extraction": public_state(row),
                "updated_at": row.updated_at,
                "order_id": str(row.order_id) if row.order_id else None,
                "missing": missing,
                "lines": lines,
                "delivery_fee": str(fee),
                "total": str(total),
                "prepayment_percent": 100 if fields["fulfillment"] == "courier" else 0,
            }
        }

    def read(self, scope, chat_id):
        self._chat(scope, chat_id)
        row = OrderDraft.objects.filter(
            business_id=scope.business_id, conversation_id=chat_id, status="active"
        ).first()
        if row is None:
            row = (
                OrderDraft.objects.filter(business_id=scope.business_id, conversation_id=chat_id)
                .order_by("-updated_at", "-id")
                .first()
            )
        return self._data(scope, row)

    def start(self, scope, chat_id):
        with transaction.atomic():
            chat = self._chat(scope, chat_id, True)
            self._editable(chat)
            row = OrderDraft.objects.filter(conversation=chat, status="active").first()
            if row is None:
                from tapme.businesses.infrastructure.access import DjangoMembershipReader

                selected = scope.point_id
                if (
                    not selected
                    and Shop.objects.filter(business_id=scope.business_id, active=True).count() == 1
                ):
                    selected = DjangoMembershipReader().order_point(scope, None)
                fields = normalize_fields(
                    {
                        "recipient_name": chat.customer.name,
                        "recipient_phone": chat.customer.phone,
                        "point_id": str(selected) if selected else "",
                    }
                )
                row = OrderDraft.objects.create(
                    business_id=scope.business_id,
                    extraction_actor_id=scope.user_id,
                    conversation=chat,
                    customer=chat.customer,
                    fields=fields,
                )
            return self._data(scope, row)

    def abandon(self, scope, chat_id, draft_id, version):
        with transaction.atomic():
            self._chat(scope, chat_id, True)
            row = self._draft(scope, chat_id, draft_id, version)
            if row.status != "active":
                raise Conflict("Черновик уже закрыт.")
            row.status, row.version = "abandoned", row.version + 1
            row.save(update_fields=["status", "version", "updated_at"])
            return self._data(scope, row)

    def save(self, scope, chat_id, draft_id, version, fields, reviewed_fields=None):
        with transaction.atomic():
            chat = self._chat(scope, chat_id, True)
            self._editable(chat)
            row = self._draft(scope, chat_id, draft_id, version)
            if row.status != "active":
                raise Conflict("Этот черновик уже закрыт. Откройте актуальный черновик.")
            if row.customer_id != chat.customer_id:
                raise Conflict("Клиент диалога изменился. Создайте новый черновик.")
            if fields.get("point_id"):
                from tapme.businesses.infrastructure.access import DjangoMembershipReader

                DjangoMembershipReader().order_point(scope, UUID(fields["point_id"]))
            self._products(scope, fields)
            if set(reviewed_fields or []) - set(fields):
                raise InvalidInput("Неизвестное поле проверки.")
            for key in reviewed_fields or []:
                row.field_meta[key] = {
                    **row.field_meta.get(key, {}),
                    "locked": True,
                    "needs_check": False,
                }
            for key, value in fields.items():
                if value != row.fields.get(key):
                    row.field_meta[key] = {"source": "staff", "locked": True, "needs_check": False}
            row.fields = fields
            row.version += 1
            row.save(update_fields=["fields", "field_meta", "version", "updated_at"])
            return self._data(scope, row)

    def restore(self, scope, chat_id, draft_id, version):
        with transaction.atomic():
            chat = self._chat(scope, chat_id, True)
            self._editable(chat)
            row = self._draft(scope, chat_id, draft_id, version)
            if row.status != "abandoned" or row.customer_id != chat.customer_id:
                raise InvalidInput("Этот черновик нельзя восстановить.")
            if OrderDraft.objects.filter(conversation=chat, status="active").exists():
                raise Conflict("В диалоге уже есть активный черновик.")
            row.status, row.version = "active", row.version + 1
            row.save(update_fields=["status", "version", "updated_at"])
            return self._data(scope, row)

    def convert(
        self, scope, chat_id, draft_id, version, payment_due_at, without_prepayment, reason
    ):
        with transaction.atomic():
            chat = self._chat(scope, chat_id, True)
            row = self._draft(scope, chat_id, draft_id, version)
            if row.status == "converted":
                if not row.order_id:
                    raise Conflict("Созданный заказ был удалён.")
                return self.orders.get(scope, row.order_id)
            self._editable(chat)
            if row.status != "active" or row.customer_id != chat.customer_id:
                raise Conflict("Черновик уже закрыт или клиент изменился.")
            if any(meta.get("needs_check") for meta in row.field_meta.values()):
                raise InvalidInput("Проверьте автозаполнение перед созданием заказа.")
            data = self._data(scope, row)["draft"]
            if data["missing"]:
                raise InvalidInput("Заполните: " + ", ".join(data["missing"]))
            fields = normalize_fields(row.fields)
            now = timezone.now()
            day, start, end = (
                date.fromisoformat(fields["date"]),
                time.fromisoformat(fields["window"]["start"]),
                time.fromisoformat(fields["window"]["end"]),
            )
            receiving = receiving_at(day, start, ZoneInfo(chat.channel.business.timezone))
            if receiving <= now:
                raise InvalidInput("Выберите будущее время получения.")
            percent = data["prepayment_percent"]
            due = (
                payment_deadline(now, receiving, payment_due_at)
                if percent and Decimal(data["total"]) > 0 and not without_prepayment
                else None
            )
            if without_prepayment:
                reason = text(reason, "Причина подтверждения без предоплаты", 1000)
                percent = 0
            products = tuple(
                ItemInput(UUID(i["product_id"]), i["quantity"])
                for i in fields["items"]
                if i["kind"] == "product"
            )
            custom = []
            for item in fields["items"]:
                if item["kind"] == "budget":
                    product, _ = ProductRecord.objects.get_or_create(
                        business_id=scope.business_id,
                        system_kind="budget",
                        defaults={"name": "Букет по бюджету", "price": 0, "active": False},
                    )
                    name = f"Букет на {item['amount']}: {item['description']}".rstrip(": ")
                    custom.append(OrderLine(product.id, name, Decimal(item["amount"]), 1))
            notes = fields["notes"]
            if fields["requested_time_text"]:
                notes += "\nПожелание по времени: " + fields["requested_time_text"]
            command = CreateOrder(
                point_id=UUID(fields["point_id"]) if fields.get("point_id") else None,
                customer_id=chat.customer_id,
                items=products,
                recipient_name=fields["recipient_name"],
                recipient_phone=fields["recipient_phone"],
                fulfillment=Fulfillment(fields["fulfillment"]),
                delivery_date=day,
                window_start=start,
                window_end=end,
                address=", ".join(v for v in [fields["address"], fields["address_details"]] if v),
                notes=notes.strip(),
                card=fields["card_text"],
                occasion=fields["occasion"],
                source="whatsapp",
            )
            order = self.orders.create(
                scope,
                command,
                row.id,
                prepayment_percent=percent,
                payment_due_at=due,
                custom_lines=tuple(custom),
                origin="chat-draft",
            )
            if without_prepayment:
                DjangoOrderRepository().event(
                    order, scope.user_id, "confirmed_without_prepayment", reason, now
                )
            row.status, row.order_id, row.version = "converted", order.id, row.version + 1
            row.save(update_fields=["status", "order", "version", "updated_at"])
            Message.objects.create(
                conversation=chat,
                direction="system",
                kind="order",
                status="received",
                sender_id=scope.user_id,
                text=f"Заказ №{order.number} создан"
                + (" · ждёт подтверждения" if order.status == "pending" else ""),
                payload={"order_id": str(order.id)},
            )
            return order

    def extend(self, scope, order_id, version):
        from dataclasses import replace

        with transaction.atomic():
            repository = DjangoOrderRepository()
            self.orders.get(scope, order_id)
            order = repository.lock(scope.business_id, order_id)
            ensure_version(order, version)
            if order.status != "pending" or order.payment_due_at is None:
                raise InvalidInput("Продление доступно ожидающему подтверждения заказу.")
            business = (
                Shop.objects.select_related("business")
                .get(business_id=scope.business_id, is_primary=True)
                .business
            )
            receiving = receiving_at(
                order.delivery_date, order.window_start, ZoneInfo(business.timezone)
            )
            now = timezone.now()
            assembly_limit = receiving - timedelta(hours=2)
            if (
                order.payment_due_at <= assembly_limit
                and max(now, order.payment_due_at) + timedelta(minutes=30) > assembly_limit
            ):
                raise InvalidInput(
                    "Продление оставит меньше двух часов на сборку. Подтвердите заказ или согласуйте другое окно."
                )
            due = payment_deadline(
                now, receiving, max(now, order.payment_due_at) + timedelta(minutes=30)
            )
            changed = replace(order, payment_due_at=due, version=order.version + 1)
            repository.save(
                changed, scope.user_id, "payment_extended", "Срок оплаты продлён на 30 минут", now
            )
            return changed
