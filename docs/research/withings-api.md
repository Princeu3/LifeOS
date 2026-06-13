# Withings API — Integration Reference (single-user, self-hosted on Railway)

> Researched 2026-06-13 (11 tool calls vs. official docs + Context7). **Verdict: EASY** for one personal user.

## Why EASY
- **No manual app-review/approval** for the Public ("App-to-App") API — "no prerequisites, free access." Create account → create app in the [Developer Dashboard](https://developer.withings.com/dashboard/) → get `client_id` + `client_secret` instantly.
- **Demo user** for testing without a device: pass `mode=demo` on the authorize step.
- Only nudge toward MEDIUM = the signature/nonce quirk + refresh-token rotation discipline.

## OAuth2 flow (authorization code)
1. Redirect: `https://account.withings.com/oauth2_user/authorize2?response_type=code&client_id=...&scope=user.metrics[,user.activity]&redirect_uri=https://<railway-domain>/withings/callback&state=...`
2. Callback receives `code` — **valid only 30s**, exchange immediately.
3. Token endpoint: `POST https://wbsapi.withings.net/v2/oauth2` with `action=requesttoken&grant_type=authorization_code` (signed). Returns `access_token`, `refresh_token`, `expires_in`, `userid`, `scope`.

**Scopes:** `user.metrics` (body composition + Notify mgmt) · `user.activity` (steps/workouts + **Sleep v2**) · `user.info` (account/device).

**Token lifetimes:** access_token **3h**; refresh_token **1 year**; old refresh_token dies ~8h after a new one is issued (or on first use of the new access_token) → **must persist the new refresh_token atomically on every refresh.**

## THE GOTCHA — signature + nonce
- `getnonce` and `requesttoken` require `signature` = HMAC-SHA256 of comma-joined sorted param values, keyed by `client_secret`, plus a `nonce` fetched from `Signature v2 - getnonce`. Generic OAuth2 libs break here.
- Use a Withings-aware lib: Python **`withings-api`** (PyPI) or Node **`withings-node-oauth2`**; or hand-roll `sign()`/`getNonce()` from the docs.
- Note: regular **Data API** calls (`getmeas` etc.) are **NOT signed** — just `Authorization: Bearer <token>`.

## Body metrics — `GET https://wbsapi.withings.net/measure?action=getmeas&meastype=<codes>&lastupdate=<ts>`
Returns `measuregrps[].measures[]`; real value = `value × 10^unit`.

| Code | Metric | | Code | Metric |
|--|--|--|--|--|
| 1 | Weight (kg) | | 11 | Heart pulse (bpm) |
| 5 | Fat-free / lean mass (kg) | | 76 | **Muscle mass (kg)** |
| 6 | Fat ratio (%) | | 77 | **Body water (kg)** |
| 8 | Fat mass (kg) | | 88 | **Bone mass (kg)** |

- **No BMI field** — derive (weight ÷ height²; height = meastype 4).
- Fat mass comes through as **kg vs %** depending on the user's unit prefs.
- **Sleep:** `Sleep v2 - Get/Getsummary` (scope `user.activity`). **Steps/activity:** `Measure v2 - Getactivity/Getworkouts`.

## Webhooks (preferred over polling)
- `Notify - Subscribe` with `appli=1` (weight & body composition) + `callbackurl`. Withings POSTs `x-www-form-urlencoded` on new data → then call `getmeas?...&lastupdate=<last_seen>`.
- Delivery typically <2 min. Retries 5 cycles over ~5h; subscription auto-cancels after 20 days of failures. **Missed notifications are NOT redelivered** → always backfill with `lastupdate`.
- **Rate limit:** 120 req/min app-wide (trivial for one user).

## Minimal Railway recipe
1. Register app, set redirect_uri to Railway domain, store `client_id`/`client_secret` as env vars.
2. Run the authorize flow once by hand; persist `refresh_token` + `userid` in Postgres (one row).
3. Subscribe `appli=1` for push (or a Railway cron poll every 15–60 min as fallback).
4. Token-refresh helper before any Data API call: if expired, `requesttoken&grant_type=refresh_token` (signed) and **overwrite both stored tokens**.
5. Recovery if refresh_token lost: `recoverauthorizationcode` (use sparingly).

**Base URL** is the EU "Public Cloud" `https://wbsapi.withings.net` (GDPR/ISO 27001/HDS) — correct for consumer WiFi/BLE devices.
