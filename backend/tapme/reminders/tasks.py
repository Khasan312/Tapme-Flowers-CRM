from celery import shared_task
from django.utils import timezone

from config import composition


@shared_task(autoretry_for=(OSError,), retry_backoff=True, max_retries=3)
def generate_reminders():
    return composition.reminder_generation().run(timezone.now())
