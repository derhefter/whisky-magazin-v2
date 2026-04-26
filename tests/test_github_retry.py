"""Test fuer den 1x-Retry bei SHA-Konflikten in admin_topics._github_update_file.

Pruefungen:
- Erfolg beim ersten PUT -> kein Retry, Ergebnis durchgereicht.
- 409 -> SHA wird neu geholt + 1x neu versucht.
- 422 (GitHub liefert das ebenfalls bei stale SHA) -> ebenfalls Retry.
- Anderer Fehler (500, 401) -> KEIN Retry, Fehler durchgereicht.
"""
from unittest.mock import patch
from urllib.error import HTTPError

import admin_topics


def _http_err(code):
    return HTTPError(url="https://x", code=code, msg="conflict", hdrs=None, fp=None)


def test_update_succeeds_first_try():
    with patch.object(
        admin_topics, "_github_put_once", return_value=({"content": {"sha": "newsha"}}, None)
    ) as put:
        result = admin_topics._github_update_file("data/x.json", b"{}", "oldsha", "msg")
        assert "error" not in result
        assert put.call_count == 1


def test_409_triggers_retry_with_fresh_sha():
    calls = []

    def fake_put(path, content, sha, msg):
        calls.append(sha)
        if len(calls) == 1:
            return None, _http_err(409)
        return ({"content": {"sha": "ok"}}, None)

    with patch.object(admin_topics, "_github_put_once", side_effect=fake_put), patch.object(
        admin_topics, "_github_get", return_value={"sha": "freshsha"}
    ):
        result = admin_topics._github_update_file("data/x.json", b"{}", "oldsha", "msg")
        assert "error" not in result
        assert calls == ["oldsha", "freshsha"]


def test_422_also_retries():
    calls = []

    def fake_put(path, content, sha, msg):
        calls.append(sha)
        if len(calls) == 1:
            return None, _http_err(422)
        return ({"content": {"sha": "ok"}}, None)

    with patch.object(admin_topics, "_github_put_once", side_effect=fake_put), patch.object(
        admin_topics, "_github_get", return_value={"sha": "freshsha"}
    ):
        result = admin_topics._github_update_file("data/x.json", b"{}", "oldsha", "msg")
        assert "error" not in result
        assert len(calls) == 2


def test_500_does_not_retry():
    calls = []

    def fake_put(path, content, sha, msg):
        calls.append(sha)
        return None, _http_err(500)

    with patch.object(admin_topics, "_github_put_once", side_effect=fake_put):
        result = admin_topics._github_update_file("data/x.json", b"{}", "oldsha", "msg")
        assert "error" in result
        assert calls == ["oldsha"]  # KEIN Retry bei 500


def test_retry_fails_returns_error():
    """Wenn auch der Retry scheitert, kommt eine Fehler-Antwort zurueck (kein Crash)."""
    def fake_put(path, content, sha, msg):
        return None, _http_err(409)

    with patch.object(admin_topics, "_github_put_once", side_effect=fake_put), patch.object(
        admin_topics, "_github_get", return_value={"sha": "freshsha"}
    ):
        result = admin_topics._github_update_file("data/x.json", b"{}", "oldsha", "msg")
        assert "error" in result
        assert "retry failed" in result["error"]
