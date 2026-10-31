import getpass
import os

from django.contrib.auth.models import Permission
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from tapme.accounts.models import User


class Command(BaseCommand):
    help = "Создать отдельного администратора платформы TapMe (не владельца магазина)."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)

    @transaction.atomic
    def handle(self, *args, **options):
        username = options["username"].strip()
        # Never silently promote a store user, or change an existing admin's password.
        if User.objects.filter(username=username).exists():
            raise CommandError("Логин уже занят. Для администратора TapMe нужен отдельный логин.")
        user = User(username=username)
        password = os.getenv("TAPME_PLATFORM_ADMIN_PASSWORD") or getpass.getpass(
            "Пароль администратора TapMe: "
        )
        try:
            user.full_clean(exclude=["password"])
            validate_password(password, user)
        except ValidationError as exc:
            raise CommandError("; ".join(exc.messages)) from None
        permission = Permission.objects.filter(
            content_type__app_label="businesses",
            content_type__model="business",
            codename="manage_platform",
        ).first()
        if not permission:
            raise CommandError("Сначала выполните migrate, чтобы создать право manage_platform.")
        user.set_password(password)
        user.save()
        user.user_permissions.add(permission)
        self.stdout.write(self.style.SUCCESS(f"Администратор TapMe создан: {username}"))
