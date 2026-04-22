"""Vercel Serverless Function: Admin Glossary Management.

Handles CRUD for all glossary entities (countries, regions, distilleries, whiskies)
and the full import/review workflow.

Endpoints (via ?action=...):
  GET  ?action=list&entity=whiskies        – list all entries
  GET  ?action=get&entity=whiskies&id=...  – single entry
  POST ?action=save&entity=whiskies        – create / update entry
  POST ?action=delete&entity=whiskies      – delete entry (soft: sets published=false + deleted=true)
  POST ?action=import_batch                – upload a raw import batch (CSV or JSON)
  GET  ?action=review_queue                – list items awaiting review
  POST ?action=review_decision             – approve / reject / merge a review item
  POST ?action=publish_approved            – write approved items into live data files
"""
import base64
import csv
import hashlib
import hmac
import io
import json
import os
import re
import time
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlparse
from urllib.request import Request, urlopen

ADMIN_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "").strip()
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
GITHUB_REPO = os.environ.get("GITHUB_REPO", "derhefter/whisky-magazin-v2").strip()
GITHUB_BRANCH = os.environ.get("GITHUB_BRANCH", "main").strip()

TOKEN_TTL = 86400

VALID_ENTITIES = {"countries", "regions", "distilleries", "whiskies"}

ALLOWED_ORIGINS = [
    "https://www.whisky-reise.com",
    "https://whisky-reise.com",
    "http://localhost:8000",
]

# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def _verify_token(token: str) -> bool:
    if not ADMIN_PASSWORD or not token or "." not in token:
        return False
    parts = token.split(".", 1)
    if len(parts) != 2:
        return False
    ts_str, _ = parts
    try:
        ts = int(ts_str)
    except ValueError:
        return False
    if time.time() - ts > TOKEN_TTL:
        return False
    key = ADMIN_PASSWORD.encode()
    sig = hmac.new(key, ts_str.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(token, f"{ts_str}.{sig}")


def _cors_headers(origin=""):
    allowed = origin if origin in ALLOWED_ORIGINS else ALLOWED_ORIGINS[0]
    return {
        "Access-Control-Allow-Origin": allowed,
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, x-admin-token",
    }


# ---------------------------------------------------------------------------
# GitHub file I/O
# ---------------------------------------------------------------------------

def _github_get(path: str):
    if path.startswith("contents/"):
        sep = "&" if "?" in path else "?"
        path = f"{path}{sep}ref={GITHUB_BRANCH}"
    url = f"https://api.github.com/repos/{GITHUB_REPO}/{path}"
    req = Request(url, headers={
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "WhiskyMagazin-Glossary",
    })
    try:
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return {"error": str(e), "detail": body}
    except Exception as e:
        return {"error": str(e)}


def _github_put(path: str, content_bytes: bytes, sha: str, message: str):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{path}"
    payload = {
        "message": message,
        "content": base64.b64encode(content_bytes).decode("utf-8"),
        "branch": GITHUB_BRANCH,
    }
    if sha:
        payload["sha"] = sha
    data = json.dumps(payload).encode("utf-8")
    req = Request(url, data=data, headers={
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "User-Agent": "WhiskyMagazin-Glossary",
    }, method="PUT")
    try:
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return {"error": str(e), "detail": body}
    except Exception as e:
        return {"error": str(e)}


def _read_json_file(gh_path: str):
    """Returns (data, sha) or (None, None) on error.
    Falls back to the Git Blobs API for files >1 MB where the Contents API
    returns an empty 'content' field."""
    result = _github_get(f"contents/{gh_path}")
    if "error" in result:
        return None, None
    sha = result.get("sha", "")
    raw_content = result.get("content", "")
    # GitHub Contents API returns empty content for files >1 MB — use Blobs API
    if not raw_content.strip():
        blob_sha = result.get("sha", "")
        if not blob_sha:
            return None, None
        blob = _github_get(f"git/blobs/{blob_sha}")
        if "error" in blob:
            return None, None
        raw_content = blob.get("content", "")
    try:
        content = base64.b64decode(raw_content).decode("utf-8")
        return json.loads(content), sha
    except Exception:
        return None, None


def _write_json_file(gh_path: str, data, sha: str, message: str):
    content_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    return _github_put(gh_path, content_bytes, sha, message)


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _entity_path(entity: str) -> str:
    return f"data/glossary/{entity}.json"


def _review_queue_path() -> str:
    return "data/glossary/review/queue.json"


def _import_raw_path(batch_id: str) -> str:
    return f"data/glossary/imports/raw/{batch_id}.json"


def _import_report_path(batch_id: str) -> str:
    return f"data/glossary/imports/reports/{batch_id}_report.json"


# ---------------------------------------------------------------------------
# Slug helpers
# ---------------------------------------------------------------------------

_UMLAUT_MAP = str.maketrans({
    "ä": "ae", "ö": "oe", "ü": "ue",
    "Ä": "ae", "Ö": "oe", "Ü": "ue", "ß": "ss",
})


def _slugify(text: str) -> str:
    text = text.translate(_UMLAUT_MAP).lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = {
    "countries": ["id", "slug", "name_de"],
    "regions": ["id", "slug", "name", "country_id"],
    "distilleries": ["id", "slug", "name", "country_id", "region_id"],
    "whiskies": ["id", "slug", "name", "country_id", "distillery_id", "whisky_type", "abv"],
}


def _validate_entry(entity: str, entry: dict, existing_ids: set) -> list:
    errors = []
    for field in REQUIRED_FIELDS.get(entity, []):
        if not entry.get(field):
            errors.append(f"Pflichtfeld fehlt: {field}")

    # Slug-Format
    slug = entry.get("slug", "")
    if slug and not re.match(r"^[a-z0-9-]+$", slug):
        errors.append(f"Slug ungültig (nur a-z, 0-9, Bindestrich): {slug}")

    # ABV range for whiskies
    if entity == "whiskies":
        try:
            abv = float(entry.get("abv", 0))
            if not (20 <= abv <= 95):
                errors.append(f"ABV außerhalb des gültigen Bereichs (20–95): {abv}")
        except (TypeError, ValueError):
            errors.append("ABV muss eine Zahl sein")

    # Duplicate check (for new entries only – updates share the same id)
    entry_id = entry.get("id", "")
    if entry_id and entry_id in existing_ids:
        errors.append(f"ID bereits vorhanden (Duplikat): {entry_id}")

    return errors


def _normalize_entry(entity: str, entry: dict, now_iso: str) -> dict:
    """Auto-generate slug, id, and timestamps when missing."""
    name_field = "name_de" if entity == "countries" else "name"
    name = entry.get(name_field, "")

    if not entry.get("slug") and name:
        entry["slug"] = _slugify(name)

    if not entry.get("id") and entry.get("slug"):
        entry["id"] = entry["slug"]

    if not entry.get("created_at"):
        entry["created_at"] = now_iso

    entry["last_updated"] = now_iso
    entry.setdefault("published", False)

    return entry


# ---------------------------------------------------------------------------
# Smart-merge helpers (used for "merged" review decisions at publish time)
# ---------------------------------------------------------------------------

_TEXT_FIELDS = frozenset({
    "long_description", "short_description", "travel_context",
    "editorial_notes", "visit_info", "style_notes",
})


def _smart_merge_entry(existing: dict, incoming: dict) -> dict:
    """Merge an incoming (import) entry into an existing live entry.

    Rules (applied per field):
    - Text fields (descriptions, notes): keep existing if incoming is empty OR shorter
      — prevents accidental content loss; use incoming only when it is a genuine extension.
    - All other fields: use incoming when non-empty; fall back to existing when incoming
      is empty/null — preserves URLs, coordinates, images that weren't re-supplied.
    """
    result = dict(incoming)
    for field, ex_val in existing.items():
        in_val = result.get(field)
        if field in _TEXT_FIELDS:
            ex_text = (ex_val or "").strip()
            in_text = (in_val or "").strip()
            if not in_text or (ex_text and len(in_text) < len(ex_text)):
                result[field] = ex_val
        else:
            if not in_val and ex_val:
                result[field] = ex_val
    return result


# ---------------------------------------------------------------------------
# Duplicate detection helpers
# ---------------------------------------------------------------------------

def _normalize_name_cmp(name: str) -> str:
    """Normalize a name for fuzzy comparison: lowercase, umlaut-expand, strip non-alnum."""
    name = name.translate(_UMLAUT_MAP).lower()
    name = re.sub(r"[^a-z0-9\s]", " ", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def _bigram_similarity(a: str, b: str) -> float:
    """Jaccard similarity on character bigrams (0.0–1.0)."""
    def bigrams(s):
        return {s[i:i+2] for i in range(len(s) - 1)}
    bg_a, bg_b = bigrams(a), bigrams(b)
    if not bg_a or not bg_b:
        return 0.0
    inter = len(bg_a & bg_b)
    return inter / len(bg_a | bg_b)


def _find_duplicate_candidates(entity: str, item: dict, existing: list) -> list:
    """Return list of potential duplicates from existing data (excluding exact id/slug matches)."""
    item_id   = item.get("id", "")
    item_slug = item.get("slug", "")
    item_name = item.get("name") or item.get("name_de") or ""
    item_norm = _normalize_name_cmp(item_name)

    candidates = []
    for ex in existing:
        ex_id   = ex.get("id", "")
        ex_slug = ex.get("slug", "")
        # Exact id/slug matches are already "update_candidate" – skip here
        if ex_id == item_id or ex_slug == item_slug:
            continue

        ex_name = ex.get("name") or ex.get("name_de") or ""
        ex_norm = _normalize_name_cmp(ex_name)
        reason  = None

        # 1. Substring match (e.g. "Ardbeg 10" ↔ "Ardbeg 10 Jahre")
        if item_norm and ex_norm:
            if item_norm in ex_norm or ex_norm in item_norm:
                reason = "Ähnlicher Name (Teilstring)"
            elif _bigram_similarity(item_norm, ex_norm) >= 0.80:
                reason = f"Sehr ähnlicher Name ({int(_bigram_similarity(item_norm, ex_norm)*100)} % Übereinstimmung)"

        # 2. Whisky-specific: same distillery + same age statement
        if entity == "whiskies" and not reason:
            same_dist = item.get("distillery_id") and item.get("distillery_id") == ex.get("distillery_id")
            age_item  = item.get("age_statement")
            age_ex    = ex.get("age_statement")
            if same_dist and age_item is not None and age_item == age_ex:
                reason = f"Gleiche Destillerie + Reifezeit ({age_item} J.)"

        if reason:
            candidates.append({
                "id":           ex_id,
                "slug":         ex_slug,
                "name":         ex_name,
                "match_reason": reason,
            })

    return candidates


# ---------------------------------------------------------------------------
# Import / Review workflow
# ---------------------------------------------------------------------------

def _parse_import_payload(raw: str, fmt: str) -> list:
    """Parse CSV or JSON import payload into a list of dicts."""
    if fmt == "json":
        data = json.loads(raw)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "items" in data:
            return data["items"]
        return [data]

    if fmt == "csv":
        reader = csv.DictReader(io.StringIO(raw))
        return [dict(row) for row in reader]

    raise ValueError(f"Unbekanntes Format: {fmt}")


def _build_import_report(batch_id: str, entity: str, items: list,
                         existing: list, now_iso: str) -> dict:
    existing_ids = {e["id"] for e in existing if e.get("id")}
    existing_slugs = {e["slug"] for e in existing if e.get("slug")}

    report_items = []
    for raw_item in items:
        normalized = _normalize_entry(entity, dict(raw_item), now_iso)
        errors = _validate_entry(entity, normalized, existing_ids)

        # Determine status
        item_id = normalized.get("id", "")
        item_slug = normalized.get("slug", "")

        if item_id in existing_ids or item_slug in existing_slugs:
            status = "update_candidate"
        elif errors:
            status = "error" if any("Pflichtfeld" in e for e in errors) else "incomplete"
        else:
            status = "new"

        # Fuzzy duplicate detection (only for new entries – updates are intentional)
        duplicate_candidates = (
            _find_duplicate_candidates(entity, normalized, existing)
            if status == "new" else []
        )

        report_items.append({
            "raw": raw_item,
            "normalized": normalized,
            "status": status,
            "errors": errors,
            "duplicate_candidates": duplicate_candidates,
            "review_status": "pending",
            "reviewer_notes": "",
            "decision": None,
        })

    return {
        "batch_id": batch_id,
        "entity": entity,
        "imported_at": now_iso,
        "total": len(report_items),
        "new": sum(1 for i in report_items if i["status"] == "new"),
        "update_candidates": sum(1 for i in report_items if i["status"] == "update_candidate"),
        "errors": sum(1 for i in report_items if i["status"] == "error"),
        "incomplete": sum(1 for i in report_items if i["status"] == "incomplete"),
        "potential_duplicates": sum(1 for i in report_items if i.get("duplicate_candidates")),
        "items": report_items,
    }


# ---------------------------------------------------------------------------
# HTTP handler
# ---------------------------------------------------------------------------

class handler(BaseHTTPRequestHandler):

    def _send(self, status: int, body: dict, origin=""):
        payload = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        for k, v in _cors_headers(origin).items():
            self.send_header(k, v)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _origin(self):
        return self.headers.get("Origin", "")

    def _token(self):
        return self.headers.get("x-admin-token", "")

    def _auth(self):
        return _verify_token(self._token())

    def _read_body(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        try:
            return json.loads(raw)
        except Exception:
            return {}

    # --- OPTIONS preflight ---
    def do_OPTIONS(self):
        self.send_response(204)
        for k, v in _cors_headers(self._origin()).items():
            self.send_header(k, v)
        self.end_headers()

    # --- GET ---
    def do_GET(self):
        origin = self._origin()
        if not self._auth():
            return self._send(401, {"error": "Unauthorized"}, origin)

        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        action = params.get("action", [""])[0]
        entity = params.get("entity", [""])[0]
        entry_id = params.get("id", [""])[0]

        if action == "list":
            if entity not in VALID_ENTITIES:
                return self._send(400, {"error": f"Unbekannte Entität: {entity}"}, origin)
            data, _ = _read_json_file(_entity_path(entity))
            return self._send(200, {"entity": entity, "items": data or []}, origin)

        if action == "get":
            if entity not in VALID_ENTITIES:
                return self._send(400, {"error": f"Unbekannte Entität: {entity}"}, origin)
            data, _ = _read_json_file(_entity_path(entity))
            items = data or []
            match = next((i for i in items if i.get("id") == entry_id), None)
            if not match:
                return self._send(404, {"error": f"Nicht gefunden: {entry_id}"}, origin)
            return self._send(200, match, origin)

        if action == "review_queue":
            queue, _ = _read_json_file(_review_queue_path())
            return self._send(200, queue or {"batches": [], "items": []}, origin)

        return self._send(400, {"error": f"Unbekannte Action: {action}"}, origin)

    # --- POST ---
    def do_POST(self):
        origin = self._origin()
        if not self._auth():
            return self._send(401, {"error": "Unauthorized"}, origin)

        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        action = params.get("action", [""])[0]
        body = self._read_body()

        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # --- save (create / update) ---
        if action == "save":
            entity = body.get("entity", "")
            if entity not in VALID_ENTITIES:
                return self._send(400, {"error": f"Unbekannte Entität: {entity}"}, origin)
            entry = body.get("entry", {})
            if not entry:
                return self._send(400, {"error": "entry fehlt"}, origin)

            data, sha = _read_json_file(_entity_path(entity))
            items = data or []

            entry = _normalize_entry(entity, entry, now_iso)
            existing_ids = {e["id"] for e in items if e.get("id") and e.get("id") != entry.get("id")}
            errors = _validate_entry(entity, entry, existing_ids)
            if errors:
                return self._send(422, {"error": "Validierungsfehler", "details": errors}, origin)

            # Update existing or append new
            idx = next((i for i, e in enumerate(items) if e.get("id") == entry.get("id")), None)
            if idx is not None:
                items[idx] = entry
                msg = f"glossary: update {entity} {entry.get('id')}"
            else:
                items.append(entry)
                msg = f"glossary: add {entity} {entry.get('id')}"

            result = _write_json_file(_entity_path(entity), items, sha, msg)
            if "error" in result:
                return self._send(500, {"error": result["error"]}, origin)
            return self._send(200, {"ok": True, "id": entry.get("id")}, origin)

        # --- delete ---
        if action == "delete":
            entity = body.get("entity", "")
            entry_id = body.get("id", "")
            if entity not in VALID_ENTITIES or not entry_id:
                return self._send(400, {"error": "entity und id erforderlich"}, origin)

            data, sha = _read_json_file(_entity_path(entity))
            items = data or []
            idx = next((i for i, e in enumerate(items) if e.get("id") == entry_id), None)
            if idx is None:
                return self._send(404, {"error": f"Nicht gefunden: {entry_id}"}, origin)

            items[idx]["published"] = False
            items[idx]["deleted"] = True
            items[idx]["last_updated"] = now_iso

            result = _write_json_file(
                _entity_path(entity), items, sha,
                f"glossary: soft-delete {entity} {entry_id}"
            )
            if "error" in result:
                return self._send(500, {"error": result["error"]}, origin)
            return self._send(200, {"ok": True}, origin)

        # --- import_batch ---
        if action == "import_batch":
            entity = body.get("entity", "")
            fmt = body.get("format", "json")
            raw_payload = body.get("data", "")

            if entity not in VALID_ENTITIES:
                return self._send(400, {"error": f"Unbekannte Entität: {entity}"}, origin)
            if not raw_payload:
                return self._send(400, {"error": "data fehlt"}, origin)

            try:
                items = _parse_import_payload(raw_payload if isinstance(raw_payload, str) else json.dumps(raw_payload), fmt)
            except Exception as e:
                return self._send(400, {"error": f"Parse-Fehler: {e}"}, origin)

            existing, _ = _read_json_file(_entity_path(entity))
            batch_id = f"{entity}_{now_iso.replace(':', '').replace('-', '')[:15]}_{uuid.uuid4().hex[:6]}"

            report = _build_import_report(batch_id, entity, items, existing or [], now_iso)

            # Write raw batch
            raw_sha = ""
            raw_result = _write_json_file(
                _import_raw_path(batch_id),
                {"batch_id": batch_id, "entity": entity, "imported_at": now_iso, "raw": items},
                raw_sha,
                f"glossary-import: raw batch {batch_id}"
            )

            # Write report
            _write_json_file(
                _import_report_path(batch_id),
                report,
                "",
                f"glossary-import: report {batch_id}"
            )

            # Enqueue in review queue
            queue, q_sha = _read_json_file(_review_queue_path())
            if not queue:
                queue = {"batches": [], "items": []}

            queue["batches"].append({
                "batch_id": batch_id,
                "entity": entity,
                "imported_at": now_iso,
                "total": report["total"],
                "status": "pending_review",
            })

            for item in report["items"]:
                queue["items"].append({
                    "batch_id": batch_id,
                    "entity": entity,
                    "item_id": item["normalized"].get("id", ""),
                    "item_slug": item["normalized"].get("slug", ""),
                    "status": item["status"],
                    "errors": item["errors"],
                    "duplicate_candidates": item.get("duplicate_candidates", []),
                    "review_status": "pending",
                    "normalized": item["normalized"],
                    "raw": item["raw"],
                })

            _write_json_file(_review_queue_path(), queue, q_sha, f"glossary-import: queue {batch_id}")

            if "error" in raw_result:
                return self._send(500, {"error": raw_result["error"]}, origin)

            return self._send(200, {
                "ok": True,
                "batch_id": batch_id,
                "total": report["total"],
                "new": report["new"],
                "update_candidates": report["update_candidates"],
                "errors": report["errors"],
                "incomplete": report["incomplete"],
                "potential_duplicates": report["potential_duplicates"],
            }, origin)

        # --- review_decision ---
        if action == "review_decision":
            batch_id = body.get("batch_id", "")
            item_id = body.get("item_id", "")
            decision = body.get("decision", "")  # approve | reject | merge
            reviewer_notes = body.get("reviewer_notes", "")
            corrections = body.get("corrections", {})  # optional field corrections

            if decision not in ("approve", "reject", "merge"):
                return self._send(400, {"error": "decision muss approve, reject oder merge sein"}, origin)

            queue, q_sha = _read_json_file(_review_queue_path())
            if not queue:
                return self._send(404, {"error": "Review-Queue nicht gefunden"}, origin)

            # Find the item
            item = next(
                (i for i in queue["items"]
                 if i.get("batch_id") == batch_id and i.get("item_id") == item_id),
                None
            )
            if not item:
                return self._send(404, {"error": f"Review-Item nicht gefunden: {item_id}"}, origin)

            item["review_status"] = "approved" if decision == "approve" else ("merged" if decision == "merge" else "rejected")
            item["decision"] = decision
            item["reviewer_notes"] = reviewer_notes
            item["reviewed_at"] = now_iso

            if corrections:
                item["normalized"].update(corrections)
                item["normalized"]["last_updated"] = now_iso

            _write_json_file(_review_queue_path(), queue, q_sha,
                             f"glossary-review: {decision} {item_id}")

            return self._send(200, {"ok": True, "item_id": item_id, "decision": decision}, origin)

        # --- publish_approved ---
        if action == "publish_approved":
            entity = body.get("entity", "")
            batch_id = body.get("batch_id", "")

            if entity not in VALID_ENTITIES:
                return self._send(400, {"error": f"Unbekannte Entität: {entity}"}, origin)

            queue, q_sha = _read_json_file(_review_queue_path())
            if not queue:
                return self._send(404, {"error": "Review-Queue nicht gefunden"}, origin)

            approved_items = [
                i for i in queue["items"]
                if i.get("entity") == entity
                and i.get("review_status") in ("approved", "merged")
                and (not batch_id or i.get("batch_id") == batch_id)
            ]

            if not approved_items:
                return self._send(200, {"ok": True, "published": 0, "message": "Keine freigegebenen Datensätze"}, origin)

            live_data, live_sha = _read_json_file(_entity_path(entity))
            items = live_data or []
            live_index = {e["id"]: i for i, e in enumerate(items) if e.get("id")}

            published_count = 0
            for qi in approved_items:
                entry = dict(qi["normalized"])
                entry["published"] = True
                entry["last_updated"] = now_iso

                existing_idx = live_index.get(entry.get("id"))
                if existing_idx is not None:
                    if qi.get("review_status") == "merged":
                        entry = _smart_merge_entry(items[existing_idx], entry)
                    items[existing_idx] = entry
                else:
                    items.append(entry)
                    live_index[entry["id"]] = len(items) - 1

                # Mark as published in queue
                qi["review_status"] = "published"
                qi["published_at"] = now_iso
                published_count += 1

            result = _write_json_file(
                _entity_path(entity), items, live_sha,
                f"glossary: publish {published_count} {entity} from {batch_id or 'review'}"
            )
            if "error" in result:
                return self._send(500, {"error": result["error"]}, origin)

            _write_json_file(_review_queue_path(), queue, q_sha,
                             f"glossary-review: mark published {entity}")

            return self._send(200, {"ok": True, "published": published_count}, origin)

        return self._send(400, {"error": f"Unbekannte Action: {action}"}, origin)
