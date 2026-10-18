from django.core.management.base import BaseCommand, CommandError

from config import composition
from tapme.businesses.application.contracts import Scope
from tapme.businesses.models import Membership
from tapme.shared.domain import InvalidInput, NotFound


class Command(BaseCommand):
    help = "Create a signed incoming text event in DEBUG + TAPME_META_MODE=fake only."

    def add_arguments(self, parser):
        parser.add_argument("--business", required=True)
        parser.add_argument("--phone", required=True)
        parser.add_argument("--name", default="Тестовый клиент")
        parser.add_argument("--text", default="Здравствуйте! Нужен букет.")

    def handle(self, *args, **options):
        from tapme.messaging.api import SimulationInput

        data = SimulationInput(data={key: options[key] for key in ["phone", "name", "text"]})
        data.is_valid(raise_exception=True)
        owner = Membership.objects.filter(
            business_id=options["business"], role="owner", is_active=True, user__is_active=True
        ).first()
        if not owner:
            raise CommandError("Active business owner not found.")
        try:
            composition.chats().run(
                "simulate", Scope(owner.user_id, owner.business_id), **data.validated_data
            )
        except (InvalidInput, NotFound) as exc:
            raise CommandError(str(exc)) from None
        self.stdout.write("Тестовое событие принято. Worker обработает его на следующем цикле.")
