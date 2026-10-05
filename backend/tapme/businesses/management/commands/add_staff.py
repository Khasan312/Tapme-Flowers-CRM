import getpass
import os

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from tapme.businesses.application.contracts import Role
from tapme.businesses.models import Business, Membership


class Command(BaseCommand):
    help = "Создать сотрудника. Пароль: TAPME_STAFF_PASSWORD либо скрытый ввод."

    def add_arguments(self, parser):
        parser.add_argument("--business", required=True)
        parser.add_argument("--username", required=True)
        parser.add_argument("--role", choices=[r.value for r in Role], required=True)

    @transaction.atomic
    def handle(self, *args, **options):
        try:
            business = Business.objects.get(id=options["business"])
        except (Business.DoesNotExist, ValidationError) as exc:
            raise CommandError("Бизнес не найден.") from exc
        User = get_user_model()
        if User.objects.filter(username=options["username"]).exists():
            raise CommandError("Такой логин уже существует. Пароль не изменён.")
        user = User(username=options["username"])
        password = os.getenv("TAPME_STAFF_PASSWORD") or getpass.getpass("Пароль сотрудника: ")
        try:
            validate_password(password, user)
            user.full_clean(exclude=["password"])
        except ValidationError as exc:
            raise CommandError("; ".join(exc.messages)) from exc
        user.set_password(password)
        user.save()
        Membership.objects.create(user=user, business=business, role=options["role"])
        self.stdout.write(
            self.style.SUCCESS(f"Сотрудник {user.username} добавлен: {options['role']}")
        )
