"""Cron entrypoint for the categorized MTD DC + UFC completed-sale monitor."""
import subprocess
import sys
from pathlib import Path

monitor = Path("__HERMES_HOME__/price-watches/run_mcfarlane_dc_sales.py")
result = subprocess.run([sys.executable, str(monitor)], text=True, capture_output=True)
if result.returncode:
    raise SystemExit(result.stderr.strip() or "MTD completed-sale monitor failed")
print(result.stdout.strip() or "[SILENT]")
