#!/usr/bin/env python
"""Enrich one pending MTD DC collection per run without burst requests."""
import json
import os
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

STATE = Path("C:/Users/jltfo/AppData/Local/hermes/price-watches/mcfarlane-dc-sales.json")
API = "https://api.rarible.org/v0.1/collections/"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")


def now():
    return datetime.now(timezone.utc)


def iso(value):
    return value.isoformat().replace("+00:00", "Z")


def parse_time(value):
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError):
        return None


def save(state):
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False,
                                     dir=STATE.parent, suffix=".tmp") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)
        f.write("\n")
        temp = f.name
    os.replace(temp, STATE)
    report = STATE.with_name("mcfarlane-dc-metadata.md")
    rows = [
        "# MTD DC Collection Metadata Progress",
        "",
        f"Updated: {state.get('metadata_enrichment', {}).get('last_attempt_at', 'unknown')}",
        "",
        "| Collection | Symbol | Type | Metadata status | Last metadata update |",
        "|---|---|---|---|---|",
    ]
    for item in state["collections"]:
        metadata = item.get("metadata") or {}
        name = item.get("display_name") or "Pending name lookup"
        symbol = item.get("symbol") or "—"
        kind = metadata.get("type") or "—"
        status = item.get("metadata_status") or "pending"
        updated = item.get("last_metadata_update_at") or "—"
        safe_name = name.replace("|", "\\|")
        rows.append(f"| {safe_name} | {symbol} | {kind} | {status} | {updated} |")
    report.write_text("\n".join(rows) + "\n", encoding="utf-8")


with STATE.open(encoding="utf-8") as f:
    state = json.load(f)

current = now()
pending = []
for collection in state["collections"]:
    if collection.get("display_name"):
        continue
    retry_at = parse_time(collection.get("next_metadata_retry_at"))
    if retry_at is None or retry_at <= current:
        pending.append(collection)

# Prioritize unresolved collections that already appear in a sale event. This ensures
# any collection that may be named in an alert is enriched before catalog-only rows.
priority_ids = {
    sale.get("collection")
    for sale in state.get("recent_sales", [])
    if sale.get("collection")
}
pending.sort(key=lambda row: (row["id"] not in priority_ids, row["id"]))

state.setdefault("metadata_enrichment", {})
state["metadata_enrichment"]["last_attempt_at"] = iso(current)
state["metadata_enrichment"]["strategy"] = (
    "one serial authenticated Rarible collection request every five minutes; "
    "sale-referenced collections are prioritized; 429/errors cool down for one hour"
)

if not pending:
    state["metadata_enrichment"]["last_result"] = "No eligible pending collections"
    save(state)
    print("No eligible pending MTD DC collections.")
    raise SystemExit(0)

collection = pending[0]
collection_id = collection["id"]
url = API + urllib.parse.quote(collection_id, safe="")
headers = {
    "X-API-KEY": os.environ["RARIBLE_API_KEY"],
    "User-Agent": UA,
    "Accept": "application/json",
}

try:
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=45) as response:
        if response.status != 200:
            raise urllib.error.HTTPError(url, response.status, "Unexpected response", response.headers, None)
        payload = json.load(response)
except (KeyError, OSError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError) as exc:
    status = getattr(exc, "code", None)
    detail = f"Rarible metadata request failed{f' HTTP {status}' if status else ''}"
    collection["metadata_status"] = f"pending ({detail})"
    collection["last_metadata_error"] = detail
    collection["next_metadata_retry_at"] = iso(current + timedelta(hours=1))
    state["metadata_enrichment"]["last_result"] = detail
    save(state)
    print(detail)
    raise SystemExit(0)

meta = payload.get("meta") or {}
name = meta.get("name") or payload.get("name")
collection["metadata"] = {
    "id": payload.get("id"),
    "type": payload.get("type"),
    "status": payload.get("status"),
    "features": payload.get("features"),
    "has_traits": payload.get("hasTraits"),
    "last_updated_at": payload.get("lastUpdatedAt"),
    "meta": meta,
}
collection["symbol"] = payload.get("symbol")
collection["last_metadata_update_at"] = payload.get("lastUpdatedAt")
collection.pop("last_metadata_error", None)
collection.pop("next_metadata_retry_at", None)

if name:
    collection["display_name"] = name
    collection["name_source"] = "Rarible collection metadata"
    collection["metadata_status"] = "verified"
    result = f"Verified {collection_id}: {name}"
else:
    collection["metadata_status"] = "pending (Rarible collection metadata has no name)"
    collection["next_metadata_retry_at"] = iso(current + timedelta(hours=24))
    result = f"Metadata fetched but name unavailable for {collection_id}"

state["metadata_enrichment"]["last_result"] = result
state["metadata_enrichment"]["remaining_pending"] = sum(
    not row.get("display_name") for row in state["collections"]
)
save(state)
print(result)
