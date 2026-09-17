"""Saved-state-only WhatsApp delivery for MTD completed-sale alerts.

This replaces an agent cron session. It performs no LLM, marketplace, or rate
request; an undelivered pending sale batch is emitted exactly once.
"""
import json
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

STATE = Path(os.environ.get("MTD_SALES_STATE", "__HERMES_HOME__/price-watches/mcfarlane-dc-sales.json"))


def atomic(path, value):
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write("\n")
        temp = f.name
    os.replace(temp, path)


state = json.loads(STATE.read_text(encoding="utf-8"))
pending = state.get("pending_whatsapp_sale_alert")
if not isinstance(pending, dict) or pending.get("delivered") or not pending.get("alert_text"):
    print("[SILENT]")
    raise SystemExit(0)
pending["delivered"] = True
pending["delivered_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
state["pending_whatsapp_sale_alert"] = pending
atomic(STATE, state)
message = "**MTD Sales Alert**\n" + str(pending["alert_text"]).replace("\r\n", "\n").replace("\r", "\n")
sys.stdout.write(message if message.endswith("\n") else message + "\n")
