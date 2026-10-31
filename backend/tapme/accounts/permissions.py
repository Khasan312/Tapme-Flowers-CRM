from rest_framework.permissions import BasePermission


def is_platform_admin(user):
    return bool(
        user.is_authenticated and user.is_active and user.has_perm("businesses.manage_platform")
    )


class PasswordChanged(BasePermission):
    message = "Перед началом работы смените временный пароль."
    code = "password_change_required"

    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and not request.user.must_change_password)


class PlatformAdmin(BasePermission):
    message = "Доступ разрешён только администраторам TapMe."

    def has_permission(self, request, view):
        return is_platform_admin(request.user)
