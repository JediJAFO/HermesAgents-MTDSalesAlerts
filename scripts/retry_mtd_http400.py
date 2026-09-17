"""Run one due MTD sales retry after a saved Rarible HTTP 400.

The primary monitor creates `http400_retry` with a three-attempt budget.
This wrapper is safe to schedule every five minutes: it makes no API call
unless a retry is due, and the primary monitor clears the marker on success.
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

STATE = Path("__HERMES_HOME__/price-watches/mcfarlane-dc-sales.json")
MONITOR = Path("__HERMES_HOME__/price-watches/run_mcfarlane_dc_sales.py")

state = json.loads(STATE.read_text(encoding="utf-8"))
retry = state.get("http400_retry")
if not isinstance(retry, dict) or not retry.get("remaining") or not retry.get("next_attempt_at"):
    print("[SILENT]")
    raise SystemExit(0)

due = datetime.fromisoformat(str(retry["next_attempt_at"]).replace("Z", "+00:00"))
if datetime.now(timezone.utc) < due:
    print("[SILENT]")
    raise SystemExit(0)

env = os.environ.copy()
env["MTD_HTTP400_RETRY"] = "1"
result = subprocess.run([sys.executable, str(MONITOR)], env=env, text=True, capture_output=True)
if result.returncode:
    raise SystemExit(result.stderr.strip() or "MTD HTTP-400 retry monitor failed")
print(result.stdout.strip() or "[SILENT]")
