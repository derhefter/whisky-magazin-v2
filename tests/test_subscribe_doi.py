"""Tests fuer Newsletter-DOI/Unsubscribe-Token-Verifikation.

Pruefungen:
- Frisch erzeugter Token verifiziert.
- Falscher Token wird abgelehnt.
- Email-Casing/-Whitespace ist normalisiert.
- Migration: alte Tokens (Legacy-Schema = sha256(BREVO_API_KEY)) bleiben gueltig
  wenn NEWSLETTER_TOKEN_SECRET nachtraeglich gesetzt wird.
- Turnstile-Fail-open wenn TURNSTILE_SECRET_KEY leer ist.
"""
import hashlib
import hmac
import importlib

import subscribe


def test_make_and_verify_token_roundtrip():
    email = "test@example.com"
    token = subscribe._make_token(email)
    assert subscribe._verify_token(email, token) is True


def test_email_normalization():
    """Token fuer gemischtes Casing/Whitespace muss zur normalisierten Form passen."""
    t = subscribe._make_token("Test@Example.COM")
    assert subscribe._verify_token("  test@example.com  ", t) is True
    assert subscribe._verify_token("TEST@example.com", t) is True


def test_wrong_token_rejected():
    email = "user@example.com"
    other = subscribe._make_token("attacker@example.com")
    assert subscribe._verify_token(email, other) is False
    assert subscribe._verify_token(email, "") is False
    assert subscribe._verify_token(email, "deadbeef" * 8) is False


def test_legacy_token_still_valid_after_secret_introduction(monkeypatch):
    """Wichtig fuer 30-Tage-Migration: ein vor dem Secret-Wechsel versandter Link
    muss nach dem Setzen von NEWSLETTER_TOKEN_SECRET weiter funktionieren."""
    email = "old-subscriber@example.com"
    # Legacy-Token mit dem alten Schema haendisch erzeugen
    legacy_secret = hashlib.sha256(b"xkeysib-test-12345").hexdigest()[:32]
    legacy_token = hmac.new(
        legacy_secret.encode(), email.encode(), hashlib.sha256
    ).hexdigest()

    # Jetzt das neue Secret einfuehren + Modul reloaden
    monkeypatch.setenv("NEWSLETTER_TOKEN_SECRET", "ein-frisches-32byte-random-secret-aaaa")
    importlib.reload(subscribe)

    # Der alte Token muss weiterhin verifizieren (Legacy-Fallback im _verify_token)
    assert subscribe._verify_token(email, legacy_token) is True

    # Aber neue Tokens werden mit dem neuen Secret erzeugt — und sind auch gueltig
    new_token = subscribe._make_token(email)
    assert subscribe._verify_token(email, new_token) is True

    # Cleanup: zurueck auf Legacy fuer andere Tests
    monkeypatch.setenv("NEWSLETTER_TOKEN_SECRET", "")
    importlib.reload(subscribe)


def test_turnstile_fail_open_when_no_secret():
    """Wenn TURNSTILE_SECRET_KEY leer ist, soll _verify_turnstile True liefern
    (Fail-open fuer Migrations-/Setup-Phase)."""
    importlib.reload(subscribe)
    assert subscribe._verify_turnstile("any-token", "1.2.3.4") is True
    assert subscribe._verify_turnstile("", "1.2.3.4") is True


def test_turnstile_rejects_empty_token_when_secret_set(monkeypatch):
    monkeypatch.setenv("TURNSTILE_SECRET_KEY", "0xTEST_SECRET")
    importlib.reload(subscribe)
    # Leerer Token muss vor dem Netzwerk-Call abgelehnt werden
    assert subscribe._verify_turnstile("", "1.2.3.4") is False
    monkeypatch.setenv("TURNSTILE_SECRET_KEY", "")
    importlib.reload(subscribe)
