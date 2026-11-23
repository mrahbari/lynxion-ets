from types import SimpleNamespace

from infrastructure.services.risk_alerts import TelegramNotificationService


def test_credentials_have_no_source_default(monkeypatch):
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)

    service = TelegramNotificationService()

    assert service.config == {"bot_token": "", "chat_id": ""}


def test_missing_chat_id_fails_before_network(monkeypatch):
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "")   # tests/conftest.py sets "0"; an empty argument falls back to it
    service = TelegramNotificationService(bot_token="test-token", chat_id="")
    calls = []
    monkeypatch.setattr(
        "infrastructure.services.risk_alerts.requests.post",
        lambda *args, **kwargs: calls.append((args, kwargs)),
    )

    assert service.send_notification("message") is False
    assert calls == []


def test_html_subject_is_escaped(monkeypatch):
    service = TelegramNotificationService(bot_token="test-token", chat_id="chat-id")
    payloads = []

    def post(url, data, **kwargs):
        payloads.append(data)
        return SimpleNamespace(status_code=200)

    monkeypatch.setattr("infrastructure.services.risk_alerts.requests.post", post)

    assert service.send_notification(
        "<b>safe message</b>",
        subject="A < B & C",
        parse_mode="HTML",
    ) is True
    assert payloads[0]["text"].startswith("<b>A &lt; B &amp; C</b>")


def test_send_has_bounded_timeout(monkeypatch):
    service = TelegramNotificationService(bot_token="test-token", chat_id="chat-id")
    options = []

    def post(_url, **kwargs):
        options.append(kwargs)
        return SimpleNamespace(status_code=200)

    monkeypatch.setattr("infrastructure.services.risk_alerts.requests.post", post)
    assert service.send_notification("message") is True
    assert options[0]["timeout"] == 10


def test_exception_does_not_log_bot_token(monkeypatch):
    import requests

    token = "synthetic-secret-token"
    service = TelegramNotificationService(bot_token=token, chat_id="chat-id")
    errors = []
    service.logger = SimpleNamespace(error=errors.append)

    def post(url, **_kwargs):
        raise requests.exceptions.Timeout("timeout contacting " + url)

    monkeypatch.setattr("infrastructure.services.risk_alerts.requests.post", post)
    assert service.send_notification("message") is False
    assert errors
    assert all(token not in message for message in errors)
    assert "Timeout" in errors[0]
