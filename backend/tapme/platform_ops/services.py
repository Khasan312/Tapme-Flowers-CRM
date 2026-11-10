import secrets

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count, Prefetch, Q
from rest_framework.exceptions import NotFound
from rest_framework.exceptions import ValidationError as ApiValidationError

from tapme.accounts.models import User
from tapme.accounts.permissions import is_platform_admin
from tapme.businesses.models import Business, Membership, Shop
from tapme.platform_ops.models import PlatformEvent


def companies():
    return (
        Business.objects.annotate(
            point_count=Count("points", distinct=True),
            member_count=Count(
                "memberships",
                distinct=True,
                filter=Q(memberships__is_active=True, memberships__user__is_active=True),
            ),
        )
        .prefetch_related(
            Prefetch(
                "memberships",
                queryset=Membership.objects.filter(role="owner", is_active=True).select_related(
                    "user"
                ),
                to_attr="platform_owners",
            )
        )
        .order_by("name", "id")
    )


def company_data(business):
    return {
        "id": business.id,
        "name": business.name,
        "currency": business.currency,
        "timezone": business.timezone,
        "point_count": business.point_count,
        "member_count": business.member_count,
        "owners": [
            {
                "id": m.user_id,
                "username": m.user.username,
                "name": m.user.get_full_name(),
                "is_active": m.user.is_active,
                "last_login": m.user.last_login,
                "must_change_password": m.user.must_change_password,
            }
            for m in business.platform_owners
        ],
    }


def provision_company(actor, name, owner_username, owner_name):
    # All records, including the audit event, commit together. Never reuse an existing user.
    password = secrets.token_urlsafe(18)
    user = User(username=owner_username, first_name=owner_name, must_change_password=True)
    try:
        user.full_clean(exclude=["password"])
        validate_password(password, user)
    except ValidationError as exc:
        raise ApiValidationError(exc.messages) from None
    try:
        with transaction.atomic():
            user.set_password(password)
            user.save()
            business = Business.objects.create(name=name)
            Shop.objects.create(business=business, name=name)
            Membership.objects.create(business=business, user=user, role="owner")
            PlatformEvent.objects.create(
                actor=actor, business=business, owner=user, action="business_created"
            )
    except IntegrityError:
        if User.objects.filter(username=owner_username).exists():
            raise ApiValidationError("Этот логин уже занят. Выберите другой.") from None
        raise
    return {
        "business": company_data(companies().get(id=business.id)),
        "credentials": {"username": user.username, "temporary_password": password},
    }


@transaction.atomic
def reset_owner_password(actor, business_id, owner_id):
    user = User.objects.select_for_update().filter(id=owner_id).first()
    if (
        not user
        or not Membership.objects.filter(
            business_id=business_id, user=user, role="owner", is_active=True
        ).exists()
    ):
        raise NotFound("Владелец магазина не найден.")
    if not user.is_active or is_platform_admin(user):
        raise ApiValidationError("Эту учётную запись нельзя восстановить через карточку магазина.")
    password = secrets.token_urlsafe(18)
    user.set_password(password)
    user.must_change_password = True
    user.save(update_fields=["password", "must_change_password"])
    PlatformEvent.objects.create(
        actor=actor, business_id=business_id, owner=user, action="owner_password_reset"
    )
    return {"username": user.username, "temporary_password": password}
