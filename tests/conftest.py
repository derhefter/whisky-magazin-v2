"""Test-Setup: api/-Verzeichnis in sys.path haengen, Env-Vars stubben."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))

# Stub-Env: tests muessen ohne echte Secrets laufen.
os.environ.setdefault("DASHBOARD_PASSWORD", "test-password-1234")
os.environ.setdefault("ADMIN_KEY_VERSION", "1")
os.environ.setdefault("BREVO_API_KEY", "xkeysib-test-12345")
os.environ.setdefault("NEWSLETTER_TOKEN_SECRET", "")  # erst Legacy testen
os.environ.setdefault("GITHUB_TOKEN", "ghp_test")
os.environ.setdefault("GITHUB_REPO", "test/repo")
os.environ.setdefault("GITHUB_BRANCH", "main")
os.environ.setdefault("TURNSTILE_SECRET_KEY", "")  # Fail-open
