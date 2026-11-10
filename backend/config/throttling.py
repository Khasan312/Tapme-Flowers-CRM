from ipaddress import ip_address

from django.conf import settings
from rest_framework.throttling import ScopedRateThrottle


def client_ip(request):
    # The public Caddy overwrites this header. The API is private in that setup.
    if settings.TRUST_PROXY:
        try:
            return str(ip_address(request.headers.get("X-Tapme-Client-IP", "")))
        except ValueError:
            pass
    return request.META.get("REMOTE_ADDR", "unknown")


class ClientRateThrottle(ScopedRateThrottle):
    def get_ident(self, request):
        return client_ip(request)
