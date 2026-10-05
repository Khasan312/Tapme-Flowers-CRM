"""Create and remove only this browser test's isolated business in the local dev DB."""

import json
import os
import secrets
import subprocess
import sys
from pathlib import Path
from uuid import UUID, uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django  # noqa: E402

django.setup()

from django.db import transaction  # noqa: E402

from tapme.accounts.models import User  # noqa: E402
from tapme.businesses.models import Business, Membership, Shop  # noqa: E402
from tapme.catalog.models import ProductRecord  # noqa: E402
from tapme.customers.models import CustomerRecord  # noqa: E402
from tapme.feedback.models import FeedbackRecord  # noqa: E402
from tapme.media.models import PhotoRecord  # noqa: E402
from tapme.orders.models import OrderCounter, OrderRecord  # noqa: E402
from tapme.payments.models import PaymentRecord  # noqa: E402
from tapme.reminders.models import ReminderRecord, ReminderSettings  # noqa: E402

with transaction.atomic():
    if sys.argv[1] == "create":
        suffix = uuid4().hex[:12]
        username, password = f"e2e_{suffix}", secrets.token_urlsafe(24)
        user = User.objects.create_user(username=username, password=password)
        business = Business.objects.create(name=f"E2E Цветочная мастерская {suffix}")
        Shop.objects.create(business=business, name="Цветочная мастерская")
        Membership.objects.create(business=business, user=user, role="owner")
        print(
            json.dumps(
                {"username": username, "password": password, "business_id": str(business.id)}
            )
        )
    elif sys.argv[1] == "delete":
        data = json.load(sys.stdin)
        business = Business.objects.get(id=UUID(data["business_id"]), name__startswith="E2E ")
        user = User.objects.get(username=data["username"], username__startswith="e2e_")
        assert Membership.objects.filter(business=business, user=user, role="owner").exists()
        staff_ids = list(
            Membership.objects.filter(business=business).values_list("user_id", flat=True)
        )
        PaymentRecord.objects.filter(business=business).delete()
        if PhotoRecord.objects.filter(business=business).exists():
            # Uploads live in the API container's configured storage, not on the test host.
            subprocess.run(
                [
                    "docker",
                    "compose",
                    "exec",
                    "-T",
                    "api",
                    "python",
                    "-c",
                    """
import json, os, sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
import django
django.setup()
from django.core.files.storage import storages
from tapme.businesses.models import Business
from tapme.media.models import PhotoRecord
business = Business.objects.get(id=json.load(sys.stdin)['business_id'], name__startswith='E2E ')
for key in PhotoRecord.objects.filter(business=business).values_list('key', flat=True):
    assert key.startswith(f'{business.id}/')
    storages['photos'].delete(key)
""",
                ],
                cwd=Path(__file__).resolve().parents[2],
                input=json.dumps({"business_id": str(business.id)}),
                text=True,
                check=True,
            )
        PhotoRecord.objects.filter(business=business).delete()
        FeedbackRecord.objects.filter(business=business).delete()
        ReminderRecord.objects.filter(business=business).delete()
        ReminderSettings.objects.filter(business=business).delete()
        OrderRecord.objects.filter(business=business).delete()
        OrderCounter.objects.filter(business=business).delete()
        CustomerRecord.objects.filter(business=business).delete()
        ProductRecord.objects.filter(business=business).delete()
        Membership.objects.filter(business=business).delete()
        Shop.objects.filter(business=business).delete()
        business.delete()
        User.objects.filter(id__in=staff_ids, memberships__isnull=True).delete()
    else:
        raise ValueError("Unknown action")
