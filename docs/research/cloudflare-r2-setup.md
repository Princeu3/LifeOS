# Cloudflare R2 — Get Your S3 Credentials (verified mid-2026)

> Goal: fill `S3_ENDPOINT`, `S3_ACCESS_KEY_ID`, `S3_SECRET_ACCESS_KEY`, `S3_BUCKET`, `S3_REGION=auto` in `api/.env`.

## 0. Enable R2 (one-time)
Cloudflare dashboard → **Storage & databases → R2**. **You must complete the R2 subscription checkout (a payment method is required) before you can create a bucket or token** — but the **free tier is $0**: 10 GB storage, 1M writes, 10M reads/mo, **zero egress**.

## 1. Create the bucket
R2 → **Create bucket** → name `lifeos-media` (lowercase) → leave **private** → Location: Automatic → Jurisdiction: **Default** (unless you need EU data-residency, which changes the endpoint). → **Create bucket**.

## 2. Create the S3 API token
R2 Overview → right panel **API Tokens → Manage** → **Create Account API token** (account-scoped — survives staff changes; better than a User token) → Permission **Object Read & Write** → **Apply to specific buckets only → `lifeos-media`** → (optional TTL) → **Create**.

## 3. Copy the values (shown ONCE)
- **Access Key ID** → `S3_ACCESS_KEY_ID`
- **Secret Access Key** → `S3_SECRET_ACCESS_KEY`  ← shown once; if lost, roll the token
- **S3 endpoint** `https://<ACCOUNT_ID>.r2.cloudflarestorage.com` → `S3_ENDPOINT`
- bucket name `lifeos-media` → `S3_BUCKET`; `S3_REGION=auto`

(EU bucket → endpoint is `https://<ACCOUNT_ID>.eu.r2.cloudflarestorage.com`.)

## 4. CORS (only needed later, for browser presigned uploads)
Bucket → **Settings → CORS Policy → Add → JSON**:
```json
[{"AllowedOrigins":["https://your-app.example.com"],"AllowedMethods":["PUT","GET","HEAD"],"AllowedHeaders":["Content-Type"],"ExposeHeaders":["ETag"],"MaxAgeSeconds":3600}]
```
Origins must be `scheme://host` (no trailing slash/path). Server-side boto3 never needs CORS.

## Gotchas (already handled in `api/app/storage.py`)
- **CRC32 checksum break (Jan-2025+):** boto3 ≥1.36 adds checksums R2 rejects → we set `request_checksum_calculation="when_required"` + `response_checksum_validation="when_required"` + `addressing_style="path"`. ✅ patched.
- **Secret shown once.** **Region must be `auto`.** **Presigned PUT Content-Type must match the signed value or 403.** **S3 endpoint ≠ public URL** (private bucket returns 401 without a signature). **Keep host clock synced** (skew → 403).

## How to hand me the values
Safest: paste the 4 values straight into `api/.env` yourself (the `S3_*` lines are there, blank). Or paste them to me and I'll write them (gitignored) — then rotate after, since chat is logged. The secret never goes in the frontend.

Source: developers.cloudflare.com/r2 (buckets/create, api/tokens, pricing, api/s3, examples/aws/boto3, buckets/cors) — verified June 2026.
