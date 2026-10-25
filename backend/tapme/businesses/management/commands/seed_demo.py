"""Add a repeatable, clearly labelled demo dataset without replacing store records."""

import json
from collections import Counter
from datetime import datetime, time, timedelta
from decimal import Decimal
from uuid import uuid5
from zoneinfo import ZoneInfo

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from config import composition
from tapme.accounts.models import User
from tapme.businesses.application.contracts import Scope
from tapme.businesses.models import Business, Membership
from tapme.catalog.domain import Product
from tapme.catalog.infrastructure.repository import DjangoProductRepository
from tapme.catalog.models import ProductRecord
from tapme.customers.domain import Customer
from tapme.customers.infrastructure.repository import DjangoCustomerRepository
from tapme.customers.models import CustomerRecord, ImportantDateRecord, RecipientRecord
from tapme.feedback.models import FeedbackRecord
from tapme.orders.application.services import CreateOrder, ItemInput
from tapme.orders.domain import Fulfillment
from tapme.orders.models import OfficeTask, OrderRecord
from tapme.reminders.domain import candidates_for_customer
from tapme.reminders.models import ReminderRecord
from tapme.shared.domain import BusinessError, InvalidInput

LABEL = "[ДЕМО]"
NAMES = (
    "Алина Садыкова",
    "Тимур Осмонов",
    "Айдана Каримова",
    "Данияр Исаев",
    "Мария Ким",
    "Руслан Абдраев",
    "Нурия Султанова",
    "Алексей Петров",
    "Элина Токтогулова",
    "Бакыт Асанов",
    "Анна Иванова",
    "Самат Жумаев",
    "Айпери Тилекова",
    "Михаил Орлов",
    "Бермет Усенова",
    "Азамат Нуров",
    "Ксения Белова",
    "Эрмек Алиев",
    "Сезим Токтосунова",
    "Виктор Смирнов",
    "Мээрим Арстанова",
    "Илья Соколов",
    "Айсулуу Омурова",
    "Адилет Кубатов",
)
PRODUCTS = (
    ("Роза красная 60 см", "250.00"),
    ("Роза белая 60 см", "270.00"),
    ("Роза кустовая", "350.00"),
    ("Тюльпан", "150.00"),
    ("Пион", "550.00"),
    ("Гортензия", "650.00"),
    ("Эустома", "320.00"),
    ("Хризантема", "220.00"),
    ("Букет «Нежность»", "3500.00"),
    ("Букет «Яркий день»", "4200.00"),
    ("Композиция в коробке", "5800.00"),
    ("Корзина с цветами", "7500.00"),
    ("Упаковка и лента", "200.00"),
    ("Открытка", "100.00"),
)
STAFF = (
    ("manager", "Айгуль", "Садыкова"),
    ("manager", "Тимур", "Нуров"),
    ("florist", "Алина", "Каримова"),
    ("florist", "Нурия", "Исаева"),
    ("courier", "Бакыт", "Асанов"),
    ("courier", "Данияр", "Осмонов"),
)


class DemoSeed:
    def __init__(self, membership, now):
        self.business = membership.business
        self.scope = Scope(membership.user_id, membership.business_id)
        self.now = now
        self.zone = ZoneInfo(self.business.timezone)
        self.today = now.astimezone(self.zone).date()
        self.created = Counter()
        self.reminders = composition.reminders()
        self.rules = self.reminders.rules(self.scope)

    def key(self, name):
        return uuid5(self.business.id, "tapme-demo-v1:" + name)

    def staff(self):
        result = {"manager": [], "florist": [], "courier": []}
        for i, (role, first, last) in enumerate(STAFF):
            user_id = self.key(f"staff:{i}")
            user = User.objects.filter(id=user_id).first()
            if user is None:
                # Display/assignment accounts only. The owner can set a password in Settings.
                user = User.objects.create_user(
                    id=user_id,
                    username=f"demo_{self.business.id.hex}_{role}_{i + 1}",
                    password=None,
                    first_name=f"{first} (демо)",
                    last_name=last,
                )
                self.created["staff"] += 1
            membership, _ = Membership.objects.get_or_create(
                business=self.business, user=user, defaults={"role": role}
            )
            if membership.role != role or not membership.is_active:
                raise CommandError(
                    "Роль демосотрудника изменена; существующие настройки сохранены."
                )
            result[role].append(user)
        return result

    def customers(self):
        rows = []
        sources = ("Instagram", "WhatsApp", "Сайт", "Рекомендация", "В магазине")
        for i, name in enumerate(NAMES):
            customer_id = self.key(f"customer:{i}")
            if not CustomerRecord.objects.filter(id=customer_id).exists():
                customer = Customer(
                    customer_id,
                    self.business.id,
                    f"{name} (демо)",
                    # NANP's reserved fictional 555-0100..0199 range; no real contacts.
                    f"+120255501{i:02d}",
                    f"{LABEL} Вымышленный клиент для проверки CRM. "
                    "Согласие и история используются только в демонстрации.",
                    True,
                    sources[i % len(sources)],
                    ("Демо", "VIP")
                    if i % 5 == 0
                    else ("Демо", "Корпоративный")
                    if i % 7 == 0
                    else ("Демо",),
                )
                DjangoCustomerRepository().add(customer)
                CustomerRecord.objects.filter(id=customer_id).update(
                    created_at=self.now - timedelta(days=180 if i >= 16 else i * 4)
                )
                self.created["customers"] += 1
            row = CustomerRecord.objects.get(id=customer_id, business=self.business)
            for j in range(2):
                recipient, created = RecipientRecord.objects.get_or_create(
                    id=self.key(f"recipient:{i}:{j}"),
                    defaults=dict(
                        customer=row,
                        name=f"{('Айжан', 'Елена', 'Нурзат', 'Анастасия')[(i + j) % 4]} (демо)",
                        relation="Мама" if j == 0 else "Коллега",
                        phone="",
                        address=f"Демо-адрес, Бишкек, ул. Цветочная, {i + 1}, кв. {j + 1}",
                        notes=f"{LABEL} Адрес вымышленный. Позвонить перед вручением.",
                    ),
                )
                self.created["recipients"] += int(created)
                if j == 0 or i < 12:
                    offset = self.rules.offsets[(i + j) % len(self.rules.offsets)]
                    event_day = self.today + timedelta(days=offset)
                    _, created = ImportantDateRecord.objects.get_or_create(
                        id=self.key(f"date:{i}:{j}"),
                        defaults=dict(
                            customer=row,
                            label="День рождения" if j == 0 else "Годовщина",
                            person=recipient.name,
                            month=event_day.month,
                            day=event_day.day,
                        ),
                    )
                    self.created["dates"] += int(created)
            rows.append(row)
        return rows

    def products(self):
        rows = []
        for i, (name, price) in enumerate(PRODUCTS):
            product_id = self.key(f"product:{i}")
            if not ProductRecord.objects.filter(id=product_id).exists():
                DjangoProductRepository().add(
                    Product(product_id, self.business.id, f"{name} (демо)", Decimal(price))
                )
                self.created["products"] += 1
            rows.append(ProductRecord.objects.get(id=product_id, business=self.business))
        return rows

    def orders(self, customers, products, staff):
        plan = [
            (0, s)
            for s in ["new"] * 6
            + ["work"] * 6
            + ["ready"] * 6
            + ["route"] * 6
            + ["done"] * 4
            + ["cancelled"] * 2
        ]
        plan += [(1, "new" if i < 8 else "work") for i in range(12)]
        plan += [(2 + i // 2, "new") for i in range(8)]
        plan += [(-1, s) for s in ("new", "work", "route", "done")]
        historic = max(120, self.rules.inactive_days + 14)
        plan += [(-historic - i * 4, "done") for i in range(8)]
        windows = self.business.shop.delivery_windows
        if not windows:
            raise CommandError("В магазине нет окон доставки.")
        rows = []
        for i, (offset, target) in enumerate(plan):
            request_key = self.key(f"order:{i}")
            existing = OrderRecord.objects.filter(
                business=self.business, request_key=request_key
            ).first()
            if existing:
                rows.append(existing)
                continue
            customer = customers[16 + i - 54] if i >= 54 else customers[i % 16]
            recipient = RecipientRecord.objects.get(
                id=self.key(f"recipient:{customers.index(customer)}:{i % 2}")
            )
            window = windows[i % len(windows)]
            day = self.today + timedelta(days=offset)
            start, end = time.fromisoformat(window["start"]), time.fromisoformat(window["end"])
            slot_start = datetime.combine(day, start, self.zone)
            happened = min(self.now - timedelta(minutes=15), slot_start - timedelta(minutes=30))
            clock = [happened - timedelta(hours=2)]
            service, workflow = composition.orders(), composition.workflow()
            service.clock = workflow.clock = lambda: clock[0]
            fulfillment = (
                Fulfillment.PICKUP if i % 4 == 0 and target != "route" else Fulfillment.COURIER
            )
            items = (
                ItemInput(products[i % 12].id, 1 if i % 12 >= 8 else (7, 11, 15)[i % 3]),
                ItemInput(products[12].id, 1),
                ItemInput(products[13].id, 1),
            )
            order = service.create(
                self.scope,
                CreateOrder(
                    customer.id,
                    items,
                    recipient.name,
                    "",
                    fulfillment,
                    day,
                    start,
                    end,
                    recipient.address if fulfillment == Fulfillment.COURIER else "",
                    f"{LABEL} Демонстрационный заказ. "
                    + (
                        "Нежные оттенки, без лилий."
                        if i % 2
                        else "Яркие цветы, подарочная упаковка."
                    ),
                    ("С днём рождения!", "Спасибо за заботу!", "С любовью!", "Прекрасного дня!")[
                        i % 4
                    ],
                    ("День рождения", "Благодарность", "Годовщина", "Без повода")[i % 4],
                    customer.source,
                    recipient.relation,
                ),
                request_key,
            )
            if target != "new" or i % 2:
                order = workflow.assign(
                    self.scope,
                    order.id,
                    order.version,
                    staff["florist"][i % 2].id,
                    staff["courier"][i % 2].id if fulfillment == Fulfillment.COURIER else None,
                )
            if target in {"done", "cancelled"} or i % 3:
                amount = (
                    order.total
                    if target in {"done", "cancelled"} or i % 3 == 2
                    else (order.total / 2).quantize(Decimal("0.01"))
                )
                workflow.payment(
                    self.scope,
                    order.id,
                    amount,
                    "payment",
                    ("cash", "card", "transfer")[i % 3],
                    f"{LABEL} Учебная запись, деньги не списывались.",
                    self.key(f"payment:{i}"),
                )
                self.created["payments"] += 1
                order = service.get(self.scope, order.id)
            path = {
                "new": [],
                "work": ["work"],
                "ready": ["work", "ready"],
                "route": ["work", "ready", "route"],
                "done": ["work", "ready"]
                + (["route"] if fulfillment == Fulfillment.COURIER else [])
                + ["done"],
                "cancelled": ["cancelled"],
            }[target]
            for status in path:
                clock[0] += timedelta(minutes=15)
                order = workflow.transition(
                    self.scope,
                    order.id,
                    order.version,
                    status,
                    f"{LABEL} Клиент изменил планы." if status == "cancelled" else "",
                )
            if target == "cancelled":
                workflow.payment(
                    self.scope,
                    order.id,
                    order.total,
                    "refund",
                    ("cash", "card", "transfer")[i % 3],
                    f"{LABEL} Учебный возврат после отмены.",
                    self.key(f"refund:{i}"),
                )
                self.created["refunds"] += 1
            if target == "route" and i % 3 == 0:
                workflow.issue(
                    self.scope,
                    order.id,
                    order.version,
                    f"{LABEL} Получатель пока не отвечает; курьер ожидает у входа.",
                )
            rows.append(OrderRecord.objects.get(id=order.id))
            self.created["orders"] += 1
        return rows

    def reminder_rows(self, customers):
        index = 0
        for customer in customers:
            last = (
                OrderRecord.objects.filter(customer=customer, status="done")
                .order_by("-completed_at")
                .first()
            )
            completed = last.completed_at if last else None
            events = [(str(d.id), d.label, d.person, d.month, d.day) for d in customer.dates.all()]
            candidates = candidates_for_customer(
                str(customer.id),
                customer.name,
                events,
                completed.isoformat() if completed else None,
                completed.astimezone(self.zone).date() if completed else None,
                self.today,
                self.rules,
            )
            for key, event, person in candidates:
                # Match the scheduler keys so future Celery runs do not duplicate demo reminders.
                row, created = ReminderRecord.objects.get_or_create(
                    business=self.business,
                    key=key,
                    defaults=dict(
                        customer=customer, event=event, person=person, due_date=self.today
                    ),
                )
                if created:
                    self.created["reminders"] += 1
                    action = index % 11
                    if action in {6, 7, 8}:
                        try:
                            self.reminders.prepare(self.scope, row.id, self.now)
                        except InvalidInput:
                            # Demo messages obey the same quiet hours and frequency as real ones.
                            index += 1
                            continue
                        self.reminders.act(self.scope, row.id, "sent", self.now)
                        if action >= 7:
                            self.reminders.act(self.scope, row.id, "answered", self.now)
                        if action == 8:
                            self.reminders.act(self.scope, row.id, "ordered", self.now)
                    elif action in {9, 10}:
                        self.reminders.act(
                            self.scope, row.id, "skipped" if action == 9 else "tomorrow", self.now
                        )
                index += 1

    def feedback_and_tasks(self, orders):
        for i, order in enumerate([o for o in orders if o.status == "done"][:8]):
            kind = "complaint" if i in {1, 3} else "review"
            if not FeedbackRecord.objects.filter(order=order, message__startswith=LABEL).exists():
                result = composition.feedback().create(
                    self.scope,
                    order.id,
                    kind,
                    f"{LABEL} "
                    + (
                        "Доставка задержалась, нужна обратная связь."
                        if kind == "complaint"
                        else "Красивый букет, получатель доволен. Спасибо!"
                    ),
                    2 if kind == "complaint" else 5,
                )
                if i == 3:
                    composition.feedback().resolve(
                        self.scope,
                        result["id"],
                        f"{LABEL} Обращение разобрано; согласовали замену открытки.",
                    )
                self.created["feedback"] += 1
        for i, content in enumerate(
            (
                "Проверить поставку роз",
                "Подготовить упаковку для завтрашних заказов",
                "Уточнить адрес у получателя",
                "Согласовать корпоративный букет",
                "Проверить маршрут курьеров",
            )
        ):
            _, created = OfficeTask.objects.get_or_create(
                id=self.key(f"task:{i}"),
                defaults=dict(
                    business=self.business,
                    created_by_id=self.scope.user_id,
                    content=f"{LABEL} {content}",
                ),
            )
            self.created["tasks"] += int(created)

    def run(self):
        staff, customers, products = self.staff(), self.customers(), self.products()
        orders = self.orders(customers, products, staff)
        self.reminder_rows(customers)
        self.feedback_and_tasks(orders)
        return {
            "created": dict(self.created),
            "demo_orders": len(orders),
            "statuses": dict(Counter(o.status for o in orders)),
            "anchor_date": str(self.today),
        }


class Command(BaseCommand):
    help = "Добавить помеченные демоданные в один магазин; повторный запуск не заменяет записи."

    def add_arguments(self, parser):
        parser.add_argument("--owner", required=True, help="Логин владельца магазина")
        parser.add_argument("--business", help="UUID магазина, если у владельца их несколько")

    def handle(self, *args, **options):
        query = Membership.objects.filter(
            user__username=options["owner"], user__is_active=True, role="owner", is_active=True
        ).select_related("business", "business")
        if options["business"]:
            query = query.filter(business_id=options["business"])
        memberships = list(query)
        if len(memberships) != 1:
            raise CommandError("Укажите владельца ровно одного магазина или уточните --business.")
        try:
            with transaction.atomic():
                Business.objects.select_for_update().get(id=memberships[0].business_id)
                result = DemoSeed(memberships[0], timezone.now()).run()
        except BusinessError as exc:
            raise CommandError(f"Демоданные не добавлены; изменения отменены: {exc}") from exc
        self.stdout.write(json.dumps(result, ensure_ascii=False))
