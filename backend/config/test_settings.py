from .settings import *  # noqa: F403

ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

SECURE_SSL_REDIRECT = False
