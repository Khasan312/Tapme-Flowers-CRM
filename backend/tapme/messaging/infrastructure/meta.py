import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import uuid4

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

from tapme.messaging.domain import DeliveryRejected, DeliveryUnknown
from tapme.shared.domain import InvalidInput


def configured():
    return bool(
        settings.TAPME_SECRETS_KEY
        and (settings.TAPME_META_MODE == "fake" or settings.META_GRAPH_VERSION)
    )


def gateway_for(channel=None):
    mode = settings.TAPME_META_MODE
    if mode not in {"fake", "live"} or (channel and channel.provider_mode != mode):
        raise DeliveryRejected(
            "Режим канала не совпадает с режимом сервера. Подключите канал заново в нужном режиме."
        )
    if mode == "fake":
        return FakeGateway()
    return MetaGateway()


def cipher():
    try:
        return Fernet(settings.TAPME_SECRETS_KEY.encode())
    except (ValueError, TypeError):
        raise InvalidInput("На сервере не настроен ключ шифрования каналов.") from None


def encrypt(token):
    return cipher().encrypt(token.encode()).decode()


def decrypt(token):
    try:
        return cipher().decrypt(token.encode()).decode()
    except InvalidToken:
        raise InvalidInput(
            "Не удалось расшифровать доступ к WhatsApp. Проверьте ключ сервера."
        ) from None


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class MetaGateway:
    def _request(self, path, token, payload=None, raw=None, content_type="application/json"):
        version = settings.META_GRAPH_VERSION
        if not re.fullmatch(r"v\d+\.\d+", version):
            raise DeliveryRejected("Укажите версию Meta Graph API на сервере.")
        request = Request(
            f"https://graph.facebook.com/{version}/{path}",
            data=raw
            if raw is not None
            else json.dumps(payload).encode()
            if payload is not None
            else None,
            headers={"Authorization": f"Bearer {token}", "Content-Type": content_type},
        )
        try:
            with build_opener(NoRedirect).open(request, timeout=20) as response:
                result = json.loads(response.read(1024 * 1024))
                if not isinstance(result, dict):
                    raise ValueError
                return result
        except HTTPError as error:
            # Do not expose provider bodies: they may contain tokens or personal data.
            if 400 <= error.code < 500:
                raise DeliveryRejected(
                    f"WhatsApp отклонил запрос (HTTP {error.code}). Проверьте доступ и окно ответа."
                ) from None
            raise DeliveryUnknown(
                "WhatsApp не подтвердил результат. Повтор автоматически не отправлялся."
            ) from None
        except (URLError, TimeoutError, OSError, ValueError):
            raise DeliveryUnknown(
                "Не удалось получить подтверждение WhatsApp. Дождитесь статуса; не повторяйте сообщение вслепую."
            ) from None

    def inspect(self, phone_id, token):
        return self._request(
            f"{phone_id}?fields=id,display_phone_number,verified_name,quality_rating,platform_type",
            token,
        )

    def upload(self, phone_id, token, content, mime):
        boundary = "tapme" + uuid4().hex
        body = (
            (
                f'--{boundary}\r\nContent-Disposition: form-data; name="messaging_product"\r\n\r\nwhatsapp\r\n'
                f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="attachment"\r\nContent-Type: {mime}\r\n\r\n'
            ).encode()
            + content
            + f"\r\n--{boundary}--\r\n".encode()
        )
        result = self._request(
            f"{phone_id}/media",
            token,
            raw=body,
            content_type=f"multipart/form-data; boundary={boundary}",
        )
        if not result.get("id"):
            raise DeliveryRejected("WhatsApp не принял вложение.")
        return str(result["id"])

    def download(self, phone_id, token, media_id):
        if not re.fullmatch(r"[0-9]{1,80}", media_id):
            raise DeliveryRejected("Некорректный идентификатор вложения.")
        meta = self._request(f"{media_id}?phone_number_id={phone_id}", token)
        url = str(meta.get("url", ""))
        try:
            parsed = urlsplit(url)
            port = parsed.port
            size = int(meta.get("file_size", 0))
        except (TypeError, ValueError):
            raise DeliveryRejected("Некорректные данные вложения WhatsApp.") from None
        if (
            parsed.scheme != "https"
            or parsed.hostname != "lookaside.fbsbx.com"
            or port not in {None, 443}
            or parsed.username
            or parsed.password
        ):
            raise DeliveryRejected("Адрес вложения WhatsApp не разрешён.")
        if size > 16 * 1024 * 1024:
            raise DeliveryRejected("Вложение превышает 16 МБ.")
        try:
            with build_opener(NoRedirect).open(
                Request(url, headers={"Authorization": f"Bearer {token}"}), timeout=20
            ) as response:
                content = response.read(16 * 1024 * 1024 + 1)
            if len(content) > 16 * 1024 * 1024:
                raise DeliveryRejected("Вложение превышает 16 МБ.")
            return content, str(meta.get("mime_type", ""))
        except (HTTPError, URLError, OSError):
            raise DeliveryRejected("Не удалось загрузить вложение WhatsApp.") from None

    def send(self, phone_id, token, payload):
        result = self._request(f"{phone_id}/messages", token, payload)
        try:
            return str(result["messages"][0]["id"])
        except (KeyError, IndexError, TypeError):
            raise DeliveryUnknown(
                "WhatsApp не вернул номер сообщения. Ожидаем подтверждение."
            ) from None

    def verify_account(self, phone_id, waba_id, token):
        result = self._request(f"{waba_id}/phone_numbers?fields=id&limit=100", token)
        for _ in range(20):
            if any(str(p.get("id")) == phone_id for p in result.get("data", [])):
                return
            after = result.get("paging", {}).get("cursors", {}).get("after")
            if not result.get("paging", {}).get("next") or not after:
                break
            from urllib.parse import quote

            result = self._request(
                f"{waba_id}/phone_numbers?fields=id&limit=100&after={quote(str(after), safe='')}",
                token,
            )
        raise DeliveryRejected("Номер не принадлежит указанному WhatsApp Business Account ID.")

    def register(self, phone_id, token, pin):
        if not self._request(
            f"{phone_id}/register", token, {"messaging_product": "whatsapp", "pin": pin}
        ).get("success"):
            raise DeliveryRejected("Meta не подтвердила регистрацию номера.")

    def subscribe(self, waba_id, token):
        if not self._request(f"{waba_id}/subscribed_apps", token, {}).get("success"):
            raise DeliveryRejected("Meta не подтвердила подписку приложения.")
        result = self._request(f"{waba_id}/subscribed_apps", token)
        if not result.get("data"):
            raise DeliveryRejected("Подписка не найдена. Проверьте приложение в Meta.")

    def mark_read(self, phone_id, token, external_id):
        self._request(
            f"{phone_id}/messages",
            token,
            {"messaging_product": "whatsapp", "status": "read", "message_id": external_id},
        )


class FakeGateway:
    """Explicit simulator: never opens a network connection."""

    def inspect(self, phone_id, token):
        return {
            "id": phone_id,
            "display_phone_number": "+996700555010",
            "verified_name": "Тестовый номер",
            "quality_rating": "GREEN",
            "platform_type": "CLOUD_API",
        }

    def verify_account(self, phone_id, waba_id, token):
        return None

    def register(self, phone_id, token, pin):
        return None

    def subscribe(self, waba_id, token):
        return None

    def mark_read(self, phone_id, token, external_id):
        return None

    def send(self, phone_id, token, payload):
        return "wamid.fake." + uuid4().hex

    def upload(self, phone_id, token, content, mime):
        return "fake-media-" + uuid4().hex

    def download(self, phone_id, token, media_id):
        raise DeliveryRejected("Для тестового вложения используйте симулятор с файлом.")
