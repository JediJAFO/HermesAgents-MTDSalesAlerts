# HermesAgents-MTDSalesAlerts

Private backup of the McFarlane Toys Digital (MTD) DC Comics completed-sales monitor.

## Included

- Polygon DC collection allowlist
- Monitor state, catalog, and human-readable database view
- Daily backup script and deterministic scheduled backup configuration

## Deliberately excluded

- API keys, bot tokens, `.env` files, authentication data, and Hermes session logs
- Runtime cache and browser data

## Monitoring behavior

The monitor looks for non-reverted Rarible Polygon `SELL` activities across the saved DC collection allowlist. Discord receives a one-line successful no-sale heartbeat; WhatsApp receives only genuine new-sale alerts.

## Backup schedule

A deterministic Hermes cron job runs once daily at 11:50 PM Eastern. It copies the current safe monitor artifacts, creates and pushes a Git commit only when those artifacts changed, and uses `no_agent: true`, so it consumes no ChatGPT/LLM tokens.
