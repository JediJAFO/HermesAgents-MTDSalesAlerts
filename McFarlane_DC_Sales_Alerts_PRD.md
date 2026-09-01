# Product Requirements Document — McFarlane DC Completed-Sale Alerts

**Version:** 1.0  
**Last updated:** 2026-09-01 EDT  
**Implementation signature:** `decf9fb33a6c`  
**Status:** Active  
**Private state:** `C:/Users/jltfo/AppData/Local/hermes/price-watches/mcfarlane-dc-sales.json`

## Purpose

Detect newly completed McFarlane DC marketplace sales across the configured storefront collection allowlist. Discord receives a reliable result for each primary interval; WhatsApp receives only actual, newly verified completed-sale events.

## Scope and schedule

- Main completed-sale check: 00:00, 08:00, 12:00, 16:00, and 20:00 Eastern.
- WhatsApp sales-only delivery: 15 minutes after every main interval.
- The full collection allowlist is held privately in the state file.
- Completed sales are authoritative from Rarible Activities, not mutable order listings.
- Mints, transfers, reverted events, and already-known activity IDs are excluded.

## Data source and collection procedure

1. Read the saved baseline activity and collection allowlist from private state.
2. Query `POST /v0.1/activities/search` with the saved collection-ID strings, `POLYGON`, type `SELL`, newest-first ordering, and the baseline date.
3. Send the configured Rarible API key only as an API header; never write, log, or publish it.
4. Require a successful, complete, parseable response before changing state or sending a Discord heartbeat.
5. Deduplicate new activity by activity ID and ignore reverted activity.
6. For each new sale, fetch item metadata serially with a measured 10-second gap between metadata requests.
7. Use the item metadata attribute whose key is exactly `Rarity`; report `Unknown` when unavailable rather than inferring rarity.
8. Atomically update recent-sale history, collection last-sale data, baseline, and a pending WhatsApp sale event.

## Failure handling

- HTTP failure, malformed/incomplete response, missing API access, or metadata failure retains existing sale history and baseline.
- Failed/incomplete checks do not produce a Discord no-sale heartbeat or WhatsApp alert.
- A successful no-sale check updates only its successful-check timestamp and sends the configured one-line Discord heartbeat.

## Notifications

### Discord

A successful primary run always reports either:

- one line confirming no new completed sales; or
- one aggregate message containing every newly found sale, one CRLF-terminated physical line per sale.

A sale line includes collection display name, item name, verified rarity or `Unknown`, price/payment asset, quantity, and sale time.

### WhatsApp

The downstream job reads only the pending state event. It sends one aggregated alert only for undelivered sale IDs, marks that event delivered atomically, and otherwise returns `[SILENT]`. It never sends a no-activity status.

## Security and privacy

- Rarible credentials stay in runtime secret configuration only.
- State and backup handling exclude credentials and delivery identities.
- Public reports do not expose internal baseline IDs, API credentials, or diagnostic logs.

## Backup and review

The daily MTD backup refreshes this PRD before evaluating backup changes, then includes this Markdown PRD and its DOCX counterpart in the same once-per-Eastern-day commit/push policy. It copies only whitelisted, non-secret monitor artifacts.
