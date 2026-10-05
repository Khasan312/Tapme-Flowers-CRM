from getpass import getpass

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from tapme.accounts.models import User
from tapme.businesses.models import Membership


class Command(BaseCommand):
    help = (
        "Restore an owner's access from the trusted server console using a hidden password prompt."
    )

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)

    def handle(self, *args, **options):
        with transaction.atomic():
            user = User.objects.select_for_update().filter(username=options["username"]).first()
            if (
                user is None
                or not Membership.objects.filter(user=user, role="owner", is_active=True).exists()
            ):
                raise CommandError("Активный владелец не найден.")
            password = getpass("Новый пароль владельца: ")
            if password != getpass("Повторите пароль: "):
                raise CommandError("Пароли не совпадают.")
            try:
                validate_password(password, user=user)
            except ValidationError as exc:
                raise CommandError(" ".join(exc.messages)) from None
            user.set_password(password)
            user.save(update_fields=["password"])
        self.stdout.write("Доступ восстановлен. Старые сессии будут недействительны.")
