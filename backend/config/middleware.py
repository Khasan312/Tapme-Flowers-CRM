from django.http import HttpResponse


def limit_api_accept_header(get_response):
    def middleware(request):
        # Bound negotiation work before DRF parses the header or checks the session.
        if request.path_info.startswith("/api/") and len(request.headers.get("Accept", "")) > 1024:
            return HttpResponse(status=431)
        return get_response(request)

    return middleware
