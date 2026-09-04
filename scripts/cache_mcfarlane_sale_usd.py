"""Persist already-retrieved Rarible USD sale values; makes no network calls."""
import json
import os
import tempfile
from pathlib import Path

BASE = Path("C:/Users/jltfo/AppData/Local/hermes/price-watches")
EXOTIC_USD = {
    "POLYGON:6999d715cdf6902f3b793c6b": ("2026-02-21T16:02:28Z", 33.4025911338402751),
    "POLYGON:69b4764afdcdf91e3b735bd9": ("2026-03-13T20:40:39Z", 53.111415817733603),
    "POLYGON:699758cb4e335818c03283a2": ("2026-02-19T18:39:04Z", 220.413228254035278),
    "POLYGON:699819704e335818c034a15d": ("2026-02-20T08:21:04Z", 44.815388661245034),
    "POLYGON:6a85ec23e7303c5185f81688": ("2026-08-19T17:47:13Z", 81.02627337354985),
    "POLYGON:69d906fdfdcdf91e3bf4bcb1": ("2026-04-10T14:19:37Z", 76.78729574054036),
    "POLYGON:698fe7364e335818c01d56ff": ("2026-02-14T03:08:27Z", 101.67578123602346),
    "POLYGON:698fe0f54e335818c01d3f4e": ("2026-02-14T02:41:13Z", 60.96475771809615),
    "POLYGON:698f607b4e335818c01bec48": ("2026-02-13T17:33:21Z", 34.37988518369412),
}
SOURCE = "Rarible completed-activity priceUsd captured once at sale time"


def atomic_write(path, value):
    fd, temp = tempfile.mkstemp(prefix=path.stem + "-", suffix=path.suffix, dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            json.dump(value, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)

exotic_path = BASE / "mcfarlane-exotics.json"
exotic = json.loads(exotic_path.read_text(encoding="utf-8"))
exotic_updated = []
for collection in exotic.get("collections", []):
    sale = collection.get("last_exotic_sale")
    if not isinstance(sale, dict):
        continue
    hit = EXOTIC_USD.get(sale.get("buyer_activity_id"))
    if not hit:
        continue
    sale["activity_date"] = hit[0]
    sale["usd_amount"] = hit[1]
    sale["usd_source"] = SOURCE
    exotic_updated.append(collection.get("name"))
atomic_write(exotic_path, exotic)

mtd_path = BASE / "mcfarlane-dc-sales.json"
mtd = json.loads(mtd_path.read_text(encoding="utf-8"))
mtd_updated = 0
for sale in mtd.get("recent_sales", []):
    value = sale.get("priceUsd", sale.get("amountUsd"))
    if value is None:
        continue
    sale["usd_amount"] = float(value)
    sale["usd_source"] = SOURCE
    mtd_updated += 1
for collection in mtd.get("collections", []):
    sale = collection.get("last_sale")
    if not isinstance(sale, dict):
        continue
    value = sale.get("amount_usd", sale.get("priceUsd", sale.get("amountUsd")))
    if value is None:
        continue
    sale["usd_amount"] = float(value)
    sale["usd_source"] = SOURCE
    mtd_updated += 1
atomic_write(mtd_path, mtd)
print(json.dumps({"network_calls": 0, "exotic_sales_cached": len(exotic_updated), "exotic_collections": exotic_updated, "mtd_sales_cached": mtd_updated}, indent=2))
