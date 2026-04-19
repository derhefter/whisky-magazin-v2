"""Diagnostic endpoint to verify which translation env vars Vercel sees."""
import json
import os
from http.server import BaseHTTPRequestHandler


def _mask(v):
    if not v:
        return None
    s = v.strip()
    if len(s) < 8:
        return f"set (len={len(s)})"
    return f"set (len={len(s)}, starts={s[:4]}, ends={s[-4:]})"


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = {
            "DEEPL_API_KEY": _mask(os.environ.get("DEEPL_API_KEY", "")),
            "AZURE_TRANSLATOR_KEY": _mask(os.environ.get("AZURE_TRANSLATOR_KEY", "")),
            "AZURE_TRANSLATOR_REGION": os.environ.get("AZURE_TRANSLATOR_REGION", "") or None,
            "GITHUB_TOKEN": _mask(os.environ.get("GITHUB_TOKEN", "")),
            "GITHUB_REPO": os.environ.get("GITHUB_REPO", "") or None,
        }
        payload = json.dumps(body, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt, *args):
        pass
