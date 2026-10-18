"""Smoke test the built web image through its real Caddy configuration."""

import argparse
from html.parser import HTMLParser
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Assets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if tag in {"script", "link"} and name in {"src", "href"} and value:
                self.urls.append(value)


def check(base):
    opener = build_opener(NoRedirect)

    def get(path):
        try:
            response = opener.open(Request(base + path), timeout=3)
        except HTTPError as error:
            response = error
        with response:
            return response.status, response.headers, response.read()

    for attempt in range(30):
        try:
            status, _, html = get("/crm-flowers/")
            assert status == 200, status
            break
        except (URLError, TimeoutError, ConnectionError):
            if attempt == 29:
                raise
            time.sleep(0.2)
    for path in ("/", "/crm-flowers"):
        status, headers, _ = get(path + "?view=customers&business=example")
        assert status == 308, (path, status)
        target = urlsplit(headers["Location"])
        assert target.path == "/crm-flowers/", target
        assert target.query == "view=customers&business=example", target
    assets = Assets()
    assets.feed(html.decode())
    assert assets.urls, "No JS/CSS resources in the built page"
    for path in assets.urls:
        assert path.startswith("/crm-flowers/assets/"), path
        status, headers, body = get(path)
        assert status == 200 and body, (path, status)
        assert "text/html" not in headers["Content-Type"], path
        assert "immutable" in headers["Cache-Control"], path
        # Already opened pages from the previous root deployment still load assets.
        assert get(path.removeprefix("/crm-flowers"))[0] == 200
    assert get("/crm-flowers/assets/absent.js")[0] == 404
    assert get("/track/existing-customer-link")[0] == 200
    assert get("/unknown-page")[0] == 404
    print("Web routes verified: redirects, query strings, JS/CSS, cache, public tracking, 404.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("base_url")
    check(parser.parse_args().base_url.rstrip("/"))
