"""Tests fuer HMAC-Token-Verifikation im Admin-Auth.

Pruefungen:
- Validitaet eines frisch generierten Tokens.
- Ablauf (TTL = 8h).
- Tampering (manipulierte Signatur).
- KEY_VERSION-Bump invalidiert Tokens sofort.
"""
import hashlib
import hmac
import importlib
import os
import time

import admin_auth


def _make_token(password, key_version, ts=None):
    if ts is None:
        ts = int(time.time())
    key = f"{password}:{key_version}".encode()
    sig = hmac.new(key, str(ts).encode(), hashlib.sha256).hexdigest()
    return f"{ts}.{sig}"


def test_fresh_token_is_valid():
    token = _make_token("test-password-1234", "1")
    assert admin_auth._verify_token(token) is True


def test_expired_token_rejected():
    # Token von vor 9 Stunden — TTL ist 8h
    old_ts = int(time.time()) - 9 * 3600
    token = _make_token("test-password-1234", "1", ts=old_ts)
    assert admin_auth._verify_token(token) is False


def test_tampered_signature_rejected():
    token = _make_token("test-password-1234", "1")
    ts, sig = token.split(".", 1)
    # Letzte Stelle der Signatur kippen
    bad_char = "0" if sig[-1] != "0" else "1"
    bad_token = f"{ts}.{sig[:-1]}{bad_char}"
    assert admin_auth._verify_token(bad_token) is False


def test_wrong_password_rejected():
    token = _make_token("wrong-password", "1")
    assert admin_auth._verify_token(token) is False


def test_key_version_bump_invalidates_token(monkeypatch):
    # Token mit KEY_VERSION=1 erzeugen
    token = _make_token("test-password-1234", "1")
    assert admin_auth._verify_token(token) is True

    # KEY_VERSION auf 2 hochdrehen + Modul reloaden
    monkeypatch.setenv("ADMIN_KEY_VERSION", "2")
    importlib.reload(admin_auth)

    # Token mit alter Version muss jetzt 401 sein
    assert admin_auth._verify_token(token) is False

    # Aber ein frischer Token mit Version 2 funktioniert
    new_token = _make_token("test-password-1234", "2")
    assert admin_auth._verify_token(new_token) is True


def test_malformed_token_rejected():
    assert admin_auth._verify_token("") is False
    assert admin_auth._verify_token("nodot") is False
    assert admin_auth._verify_token("notanumber.somesig") is False
    assert admin_auth._verify_token("12345.") is False
