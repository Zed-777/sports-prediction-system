import os
from scripts.collect_historical_results import send_notification_email


class DummySMTP:
    def __init__(self, host, port):
        pass

    def starttls(self):
        pass

    def login(self, user, pw):
        pass

    def send_message(self, msg):
        self.sent = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        pass


def test_send_notification_email(monkeypatch, tmp_path):
    monkeypatch.setenv("SMTP_HOST", "smtp.example.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USER", "user@example.com")
    monkeypatch.setenv("SMTP_PASS", "pw")
    monkeypatch.setenv("EMAIL_TO", "dest@example.com")

    monkeypatch.setattr("smtplib.SMTP", DummySMTP)

    res = send_notification_email("la-liga", 2, {"overall_accuracy": 0.8})
    assert res is True
