import json
from io import StringIO

import pytest
from django.contrib.auth import authenticate
from django.contrib.auth.models import Permission
from django.core.management import call_command
from django.core.management.base import CommandError
from rest_framework.test import APIClient

from tapme.accounts.models import User
from tapme.businesses.models import Business, Membership
from tapme.platform_ops.models import PlatformEvent
from tapme.platform_ops.services import provision_company

BASE = "/api/v1/platform"
PAYLOAD = {"name": "Dion Flowers", "owner_name": "Айгуль", "owner_username": "dion.aigul"}


@pytest.fixture
def platform(setup):
    user = User.objects.create_user(username="tapme.arsen", password="platform-private-password")
    user.user_permissions.add(
        Permission.objects.get(content_type__app_label="businesses", codename="manage_platform")
    )
    client = APIClient()
    client.force_login(user)
    return client, user


@pytest.mark.parametrize("identity", [None, "owner", "manager", "florist", "staff"])
def test_platform_is_separate_from_store_and_django_staff(setup, identity):
    client = APIClient()
    if identity:
        user = setup["owner" if identity == "staff" else identity]
        if identity == "staff":
            user.is_staff = True
            user.save(update_fields=["is_staff"])
        client.force_login(user)
    before = Business.objects.count()
    for route in ("businesses", "events"):
        assert client.get(f"{BASE}/{route}/").status_code == 403
    assert client.post(f"{BASE}/businesses/", PAYLOAD, format="json").status_code == 403
    assert (
        client.post(
            f"{BASE}/businesses/{setup['business'].id}/owners/{setup['owner'].id}/reset-password/"
        ).status_code
        == 403
    )
    assert Business.objects.count() == before


def test_platform_lists_all_companies_without_store_membership(platform, setup):
    client, user = platform
    assert not user.is_staff and not user.is_superuser
    assert not user.memberships.exists()
    response = client.get(f"{BASE}/businesses/")
    assert response.status_code == 200
    assert response["Cache-Control"] == "no-store"
    rows = {row["id"]: row for row in response.json()}
    assert len(rows) == 2
    row = rows[str(setup["business"].id)]
    assert row["point_count"] == 1
    assert row["member_count"] == 3
    assert row["owners"][0]["username"] == "owner"
    serialized = json.dumps(rows)
    assert '"password"' not in serialized and '"temporary_password"' not in serialized
    assert setup["owner"].password not in serialized
    assert client.get(f"/api/v1/businesses/{setup['business'].id}/customers/").status_code == 403


def test_platform_provision_requires_session_csrf(platform):
    _, admin = platform
    client = APIClient(enforce_csrf_checks=True)
    client.force_login(admin)
    assert client.post(f"{BASE}/businesses/", PAYLOAD, format="json").status_code == 403
    assert not User.objects.filter(username=PAYLOAD["owner_username"]).exists()
    token = client.get("/api/v1/auth/csrf/").json()["csrf_token"]
    assert (
        client.post(
            f"{BASE}/businesses/", PAYLOAD, format="json", HTTP_X_CSRFTOKEN=token
        ).status_code
        == 201
    )


def test_provision_creates_only_owner_and_audits_without_secrets(platform):
    client, admin = platform
    response = client.post(f"{BASE}/businesses/", PAYLOAD, format="json")
    assert response.status_code == 201
    assert response["Cache-Control"] == "no-store"
    data = response.json()
    user = authenticate(username="dion.aigul", password=data["credentials"]["temporary_password"])
    assert user and user.must_change_password
    assert not user.is_staff and not user.is_superuser and not user.user_permissions.exists()
    membership = Membership.objects.get(user=user)
    assert membership.role == "owner"
    assert membership.business.points.count() == 1
    assert membership.business.memberships.count() == 1
    assert membership.business.name == "Dion Flowers"
    event = PlatformEvent.objects.get()
    assert event.actor == admin and event.owner == user and event.action == "business_created"
    listing = client.get(f"{BASE}/businesses/").content + client.get(f"{BASE}/events/").content
    assert data["credentials"]["temporary_password"].encode() not in listing
    assert data["credentials"]["temporary_password"] not in user.password


@pytest.mark.parametrize(
    "extra",
    [
        {"role": "owner"},
        {"is_superuser": True},
        {"is_staff": True},
        {"password": "chosen-password"},
    ],
)
def test_provision_rejects_privilege_fields(platform, extra):
    client, _ = platform
    assert (
        client.post(f"{BASE}/businesses/", {**PAYLOAD, **extra}, format="json").status_code == 400
    )
    assert not User.objects.filter(username=PAYLOAD["owner_username"]).exists()


def test_provision_never_reuses_existing_users_or_promotes_them(platform, setup):
    client, _ = platform
    before = Business.objects.count()
    response = client.post(
        f"{BASE}/businesses/", {**PAYLOAD, "owner_username": "owner"}, format="json"
    )
    assert response.status_code == 400
    assert Business.objects.count() == before
    assert not PlatformEvent.objects.exists()
    setup["owner"].refresh_from_db()
    assert not setup["owner"].has_perm("businesses.manage_platform")


def test_provision_rolls_back_access_if_audit_cannot_be_written(platform, monkeypatch):
    _, admin = platform
    before = Business.objects.count()

    def fail(**kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(PlatformEvent.objects, "create", fail)
    with pytest.raises(RuntimeError, match="audit unavailable"):
        provision_company(admin, **PAYLOAD)
    assert Business.objects.count() == before
    assert not User.objects.filter(username=PAYLOAD["owner_username"]).exists()


def test_first_password_is_enforced_by_api_then_owner_can_create_staff(platform):
    admin, _ = platform
    data = admin.post(f"{BASE}/businesses/", PAYLOAD, format="json").json()
    owner = APIClient()
    temporary = data["credentials"]["temporary_password"]
    login = owner.post(
        "/api/v1/auth/login/", {"username": "dion.aigul", "password": temporary}, format="json"
    )
    assert login.status_code == 200 and login.json()["user"]["must_change_password"]
    assert not login.json()["user"]["is_platform_admin"]
    business = data["business"]["id"]
    assert owner.get("/api/v1/auth/me/").status_code == 200
    assert owner.get("/api/v1/businesses/").status_code == 403
    staff = {
        "username": "dion.courier",
        "password": "Courier-test-password-2026",
        "name": "Курьер",
        "role": "courier",
    }
    assert (
        owner.post(f"/api/v1/businesses/{business}/staff/", staff, format="json").status_code == 403
    )
    assert (
        owner.post(
            "/api/v1/auth/password/",
            {"current_password": temporary, "new_password": "short"},
            format="json",
        ).status_code
        == 400
    )
    changed = owner.post(
        "/api/v1/auth/password/",
        {"current_password": temporary, "new_password": "New-private-owner-password-2026"},
        format="json",
    )
    assert changed.status_code == 204
    assert not owner.get("/api/v1/auth/me/").json()["must_change_password"]
    assert owner.get("/api/v1/businesses/").status_code == 200
    assert (
        owner.post(f"/api/v1/businesses/{business}/staff/", staff, format="json").status_code == 201
    )
    assert owner.get(f"{BASE}/businesses/").status_code == 403
    assert authenticate(username="dion.aigul", password=temporary) is None


def test_required_password_user_can_log_out(platform):
    client, admin = platform
    admin.must_change_password = True
    admin.save(update_fields=["must_change_password"])
    assert client.get(f"{BASE}/businesses/").status_code == 403
    assert client.post("/api/v1/auth/logout/").status_code == 204


def test_reset_owner_ends_old_sessions_and_requires_password_change(platform, setup):
    client, admin = platform
    owner_session = setup["client"]
    response = client.post(
        f"{BASE}/businesses/{setup['business'].id}/owners/{setup['owner'].id}/reset-password/"
    )
    assert response.status_code == 200
    assert response["Cache-Control"] == "no-store"
    assert owner_session.get("/api/v1/auth/me/").status_code == 403
    user = authenticate(username="owner", password=response.json()["temporary_password"])
    assert user and user.must_change_password
    assert authenticate(username="owner", password="test-owner-password") is None
    event = PlatformEvent.objects.get()
    assert event.actor == admin and event.action == "owner_password_reset"


@pytest.mark.parametrize("identity", ["other_owner", "manager", "florist"])
def test_reset_rejects_owner_from_other_company_or_other_role(platform, setup, identity):
    client, _ = platform
    assert (
        client.post(
            f"{BASE}/businesses/{setup['business'].id}/owners/{setup[identity].id}/reset-password/"
        ).status_code
        == 404
    )
    assert not PlatformEvent.objects.exists()


def test_store_recovery_cannot_reset_a_platform_admin(platform, setup):
    client, admin = platform
    Membership.objects.create(user=admin, business=setup["business"], role="owner")
    assert (
        client.post(
            f"{BASE}/businesses/{setup['business'].id}/owners/{admin.id}/reset-password/"
        ).status_code
        == 400
    )


def test_bootstrap_is_separate_and_never_promotes_existing_user(setup, monkeypatch):
    monkeypatch.setenv("TAPME_PLATFORM_ADMIN_PASSWORD", "Private-bootstrap-password-2026")
    with pytest.raises(CommandError, match="Логин уже занят"):
        call_command("bootstrap_platform_admin", username="owner")
    call_command("bootstrap_platform_admin", username="tapme.khasan", stdout=StringIO())
    user = User.objects.get(username="tapme.khasan")
    assert user.has_perm("businesses.manage_platform")
    assert not user.is_staff and not user.is_superuser and not user.memberships.exists()
