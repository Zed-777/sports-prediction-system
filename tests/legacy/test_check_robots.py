

import scripts.check_robots as cr


class FakeResp:
    def __init__(self, text, status_code=200):
        self.text = text
        self.status_code = status_code


def test_parse_disallows_simple(monkeypatch):
    sample = """# robots
User-agent: *
Disallow: /team/
Disallow: /match/
"""
    dis = cr.parse_disallows(sample)
    assert "/team/" in dis
    assert "/match/" in dis


def test_fetch_and_parse(monkeypatch):
    def fake_get(url, timeout=10):
        return FakeResp("User-agent: *\nDisallow: /test/")

    monkeypatch.setattr(cr.requests, "get", fake_get)
    rep = cr.check_hosts(["example.com"])
    assert "example.com" in rep
    assert rep["example.com"] == ["/test/"]
