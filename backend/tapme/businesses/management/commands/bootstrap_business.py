import getpass
import os

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from tapme.businesses.models import Business, Membership, Shop


class Command(BaseCommand):
    help = "Создать бизнес и владельца. Пароль: TAPME_BOOTSTRAP_PASSWORD либо скрытый ввод."

    def add_arguments(self, parser):
        parser.add_argument("--name", required=True)
        parser.add_argument("--username", required=True)

    @transaction.atomic
    def handle(self, *args, **options):
        username = options["username"].strip()
        name = options["name"].strip()
        if not username or len(username) > 150 or not name or len(name) > 150:
            raise CommandError("Название и логин обязательны, максимум 150 символов.")
        User = get_user_model()
        existing = User.objects.filter(username=username).first()
        if existing:
            member = Membership.objects.filter(
                user=existing, role="owner", business__name=name, is_active=True
            ).first()
            if member:
                self.stdout.write(f"Бизнес уже создан: {member.business_id}. Пароль не изменён.")
                return
            raise CommandError("Такой логин уже существует. Выберите другой.")
        password = os.getenv("TAPME_BOOTSTRAP_PASSWORD") or getpass.getpass("Пароль владельца: ")
        user = User(username=username)
        try:
            validate_password(password, user)
            user.full_clean(exclude=["password"])
        except ValidationError as exc:
            raise CommandError("; ".join(exc.messages)) from exc
        user.set_password(password)
        user.save()
        business = Business.objects.create(name=name)
        Shop.objects.create(business=business, name=name)
        Membership.objects.create(business=business, user=user, role="owner")
        self.stdout.write(self.style.SUCCESS(f"Бизнес: {business.id}; владелец: {username}"))
