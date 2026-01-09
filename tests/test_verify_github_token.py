import os
import json
import pytest
from unittest.mock import patch

import scripts.verify_github_token as vgt


class FakeResp:
    def __init__(self, status_code, json_data=None):
        self.status_code = status_code
        self._json = json_data or {}

    def json(self):
        return self._json

    def raise_for_status(self):
        raise Exception(f"Status {self.status_code}")


@patch("requests.get")
def test_verify_token_success(mock_get, monkeypatch):
    mock_get.return_value = FakeResp(200, {"login": "test-user", "id": 123})
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_fake")
    info = vgt.verify_token("ghp_fake")
    assert info["login"] == "test-user"


@patch("requests.get")
def test_verify_token_failure(mock_get, monkeypatch):
    mock_get.return_value = FakeResp(401)
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_bad")
    with pytest.raises(Exception):
        vgt.verify_token("ghp_bad")
