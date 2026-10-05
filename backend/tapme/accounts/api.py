from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from config.api import StrictSerializer, validated


class UserOutput(serializers.Serializer):
    id = serializers.UUIDField()
    username = serializers.CharField()


class LoginInput(StrictSerializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=256, trim_whitespace=False, write_only=True)


class TokenOutput(serializers.Serializer):
    csrf_token = serializers.CharField()


class LoginOutput(TokenOutput):
    user = UserOutput()


class CsrfView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(responses=TokenOutput)
    def get(self, request):
        return Response({"csrf_token": get_token(request)})


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    @extend_schema(request=LoginInput, responses=LoginOutput)
    def post(self, request):
        values = validated(LoginInput, request.data)
        user = authenticate(request, **values)
        if user is None:
            return Response({"detail": "Неверный логин или пароль."}, status=400)
        login(request, user)
        return Response({"user": UserOutput(user).data, "csrf_token": get_token(request)})


class MeView(APIView):
    @extend_schema(responses=UserOutput)
    def get(self, request):
        return Response(UserOutput(request.user).data)


class LogoutView(APIView):
    @extend_schema(request=None, responses={204: None})
    def post(self, request):
        logout(request)
        return Response(status=204)


class PasswordInput(StrictSerializer):
    current_password = serializers.CharField(max_length=256, trim_whitespace=False, write_only=True)
    new_password = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)


class PasswordView(APIView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    @extend_schema(request=PasswordInput, responses={204: None})
    def post(self, request):
        from django.contrib.auth import update_session_auth_hash
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError
        from django.db import transaction

        from tapme.accounts.models import User

        data = validated(PasswordInput, request.data)
        with transaction.atomic():
            user = User.objects.select_for_update().get(id=request.user.id)
            if not user.check_password(data["current_password"]):
                raise serializers.ValidationError("Текущий пароль указан неверно.")
            try:
                validate_password(data["new_password"], user=user)
            except ValidationError as exc:
                raise serializers.ValidationError(exc.messages) from None
            user.set_password(data["new_password"])
            user.save(update_fields=["password"])
            update_session_auth_hash(request, user)
        return Response(status=204)
