"""Exercise route checks with valid resources and common production failures."""

from io import BytesIO
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_web_routes import check


PAGE = b"""<link rel="icon" href="/crm-flowers/favicon-32x32.png">
<link rel="icon" href="/crm-flowers/favicon.svg">
<link rel="apple-touch-icon" href="/crm-flowers/apple-touch-icon.png">
<link rel="stylesheet" href="/crm-flowers/assets/app-hash.css">
<link rel="modulepreload" href="/crm-flowers/assets/vendor-hash.js">
<script type="module" src="/crm-flowers/assets/app-hash.js"></script>"""


class Response(BytesIO):
    def __init__(self, status, headers, body):
        super().__init__(body)
        self.status, self.headers = status, headers


class WebRoutesTests(unittest.TestCase):
    def setUp(self):
        self.routes = {
            "/crm-flowers/": (200, {"Content-Type": "text/html"}, PAGE),
            "/track/existing-customer-link": (200, {}, b"tracking"),
        }
        for path in ("/", "/crm-flowers"):
            self.routes[path + "?view=customers&business=example"] = (
                308,
                {"Location": "/crm-flowers/?view=customers&business=example"},
                b"",
            )
        for file, mime in (
            ("app-hash.js", "text/javascript"),
            ("vendor-hash.js", "text/javascript"),
            ("app-hash.css", "text/css"),
        ):
            result = (200, {"Content-Type": mime, "Cache-Control": "public, immutable"}, b"asset")
            self.routes["/crm-flowers/assets/" + file] = result
            self.routes["/assets/" + file] = result
        for file, mime in (
            ("favicon-32x32.png", "image/png"),
            ("favicon.svg", "image/svg+xml"),
            ("apple-touch-icon.png", "image/png"),
        ):
            self.routes["/crm-flowers/" + file] = (
                200,
                {"Content-Type": mime, "Cache-Control": "no-cache"},
                b"icon",
            )

    def run_check(self):
        def open_request(request, timeout):
            return Response(*self.routes.get(request.selector, (404, {}, b"missing")))

        with patch("check_web_routes.build_opener") as opener:
            opener.return_value.open.side_effect = open_request
            with patch("builtins.print"):
                check("http://localhost")

    def test_icons_and_hashed_assets_are_available(self):
        self.run_check()

    def test_missing_or_wrong_icon_fails(self):
        for response in (
            (404, {}, b"missing"),
            (200, {"Content-Type": "text/html", "Cache-Control": "no-cache"}, PAGE),
            (200, {"Content-Type": "image/png", "Cache-Control": "no-cache"}, b""),
        ):
            with self.subTest(response=response):
                self.routes["/crm-flowers/favicon-32x32.png"] = response
                with self.assertRaises(AssertionError):
                    self.run_check()

    def test_hashed_assets_still_require_content_cache_and_legacy_route(self):
        path = "/crm-flowers/assets/app-hash.js"
        good = self.routes[path]
        for response in (
            (404, {}, b"missing"),
            (200, {"Content-Type": "text/html", "Cache-Control": "immutable"}, PAGE),
            (200, {"Content-Type": "text/javascript", "Cache-Control": "no-cache"}, b"js"),
        ):
            with self.subTest(response=response):
                self.routes[path] = response
                with self.assertRaises(AssertionError):
                    self.run_check()
        self.routes[path] = good
        del self.routes["/assets/app-hash.js"]
        with self.assertRaises(AssertionError):
            self.run_check()

    def test_icons_do_not_replace_javascript_and_styles(self):
        self.routes["/crm-flowers/"] = (
            200,
            {},
            b'<link rel="icon" href="/crm-flowers/favicon.svg">',
        )
        with self.assertRaises(AssertionError):
            self.run_check()

    def test_script_cannot_bypass_hashed_asset_rules(self):
        self.routes["/crm-flowers/"] = (
            200,
            {},
            PAGE.replace(b"/crm-flowers/assets/app-hash.js", b"/crm-flowers/app.js"),
        )
        with self.assertRaises(AssertionError):
            self.run_check()


if __name__ == "__main__":
    unittest.main()
