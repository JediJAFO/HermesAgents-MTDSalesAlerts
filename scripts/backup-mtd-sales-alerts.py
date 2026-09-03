"""Reliable Windows no-agent backup for the MTD completed-sales monitor.

Only whitelisted monitor artifacts are copied.  The job commits/pushes only
when that backup snapshot differs, and never more than once per ET calendar day.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

REPO = Path("C:/Users/jltfo/HermesAgents-MTDSalesAlerts")
SOURCE = Path("C:/Users/jltfo/AppData/Local/hermes/price-watches")
DOCS = Path("C:/Users/jltfo/Documents")
PRD_REFRESH = Path("C:/Users/jltfo/AppData/Local/hermes/scripts/refresh-mcfarlane-prds.py")
ENRICHER = Path("C:/Users/jltfo/AppData/Local/hermes/scripts/enrich_mtd_dc_metadata.py")
DEST = REPO / "monitor"
STAMP = REPO / "backup" / ".last-successful-backup-date"
FILES = (
    "mcfarlane-dc-contracts.txt",
    "mcfarlane-dc-sales.json",
    "mcfarlane-dc-sales-catalog.md",
    "mcfarlane-dc-sales-database.md",
    "mcfarlane-dc-metadata.md",
)


def run_git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    # A scheduled backup must fail clearly instead of hanging on a credential prompt.
    env["GIT_TERMINAL_PROMPT"] = "0"
    result = subprocess.run(
        ["git", *args], cwd=REPO, text=True, capture_output=True, env=env, timeout=120
    )
    if check and result.returncode:
        detail = (result.stderr or result.stdout or "git command failed").strip().splitlines()[-1][:240]
        raise RuntimeError(detail)
    return result


def copy_sanitized_state(source: Path, destination: Path) -> None:
    """Exclude buyer/seller wallets and resolved Name Tags from backups."""
    data = json.loads(source.read_text(encoding="utf-8"))
    sensitive = {"buyer", "seller", "buyer_wallet", "seller_wallet", "buyer_name_tag", "seller_name_tag", "buyer_display", "seller_display"}

    def scrub(value):
        if isinstance(value, dict):
            return {key: scrub(item) for key, item in value.items() if key not in sensitive}
        if isinstance(value, list):
            return [scrub(item) for item in value]
        return value

    destination.write_text(json.dumps(scrub(data), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    # Review implementation signatures and regenerate both PRD formats before
    # evaluating this backup snapshot.
    refreshed = subprocess.run([sys.executable, str(PRD_REFRESH)], text=True, capture_output=True, timeout=120)
    if refreshed.returncode:
        raise RuntimeError("PRD refresh failed")
    today = datetime.now(ZoneInfo("America/New_York")).date().isoformat()
    missing = [name for name in FILES if not (SOURCE / name).is_file()]
    if missing:
        raise RuntimeError("required backup artifact missing: " + ", ".join(missing))

    DEST.mkdir(parents=True, exist_ok=True)
    STAMP.parent.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        if name == "mcfarlane-dc-sales.json":
            copy_sanitized_state(SOURCE / name, DEST / name)
        else:
            shutil.copy2(SOURCE / name, DEST / name)
    for name in ("McFarlane_DC_Sales_Alerts_PRD.md", "McFarlane_DC_Sales_Alerts_PRD.docx"):
        shutil.copy2(DOCS / name, REPO / name)
    scripts_dest = REPO / "scripts"
    scripts_dest.mkdir(exist_ok=True)
    shutil.copy2(Path(__file__), scripts_dest / "backup-mtd-sales-alerts.py")
    shutil.copy2(ENRICHER, scripts_dest / ENRICHER.name)

    run_git("add", "README.md", ".gitignore", "backup-mtd-sales-alerts.sh", "McFarlane_DC_Sales_Alerts_PRD.md", "McFarlane_DC_Sales_Alerts_PRD.docx", "monitor/", "scripts/")
    if run_git("diff", "--cached", "--quiet", check=False).returncode == 0:
        print("No MTD monitor changes to back up.")
        return

    if STAMP.is_file() and STAMP.read_text(encoding="utf-8").strip() == today:
        print("Changes detected, but a backup already succeeded today; deferring.")
        return

    run_git("-c", "user.name=JediJAFO", "-c", "user.email=JediJAFO@users.noreply.github.com", "commit", "-m", f"backup: MTD sales monitor {today}")
    run_git("push", "origin", "main")
    STAMP.write_text(today + "\n", encoding="utf-8")
    print(f"Backed up MTD monitor artifacts for {today}.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"MTD backup failed: {str(exc)[:300]}", file=sys.stderr)
        raise SystemExit(1)
