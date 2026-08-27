#!/usr/bin/env bash
# Safe, deterministic once-daily backup of MTD monitor artifacts.
set -euo pipefail

REPO='C:/Users/jltfo/HermesAgents-MTDSalesAlerts'
SOURCE='C:/Users/jltfo/AppData/Local/hermes/price-watches'
STAMP="$REPO/backup/.last-successful-backup-date"
TODAY="$(TZ=America/New_York date +%F)"

mkdir -p "$REPO/monitor" "$REPO/backup"

# No credentials are copied. The monitor's .env remains outside this repository.
cp "$SOURCE/mcfarlane-dc-contracts.txt" "$REPO/monitor/"
cp "$SOURCE/mcfarlane-dc-sales.json" "$REPO/monitor/"
cp "$SOURCE/mcfarlane-dc-sales-catalog.md" "$REPO/monitor/"
cp "$SOURCE/mcfarlane-dc-sales-database.md" "$REPO/monitor/"

cd "$REPO"
git add README.md .gitignore backup-mtd-sales-alerts.sh monitor/

if git diff --cached --quiet; then
  printf 'No MTD monitor changes to back up.\n'
  exit 0
fi

# This guard makes the scheduled job commit/push no more than once per Eastern calendar day.
if [ -f "$STAMP" ] && [ "$(tr -d '\r\n' < "$STAMP")" = "$TODAY" ]; then
  printf 'Changes detected, but a backup already succeeded today; deferring.\n'
  exit 0
fi

git -c user.name='JediJAFO' -c user.email='JediJAFO@users.noreply.github.com' \
  commit -m "backup: MTD sales monitor ${TODAY}"
git push origin main
printf '%s\n' "$TODAY" > "$STAMP"
printf 'Backed up MTD monitor artifacts for %s.\n' "$TODAY"
