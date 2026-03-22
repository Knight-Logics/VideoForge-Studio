# VideoForge Studio - Render Deployment Checklist

Use this checklist to deploy the AutoTop5/VideoForge app as a standalone production web service.

## Why Render (for this app)

This app requires:
- Python backend execution
- FFmpeg subprocesses
- Writable disk for uploads/jobs/outputs
- Long-running render tasks

Render supports this directly with Docker + persistent disk.

## 1. Repository Setup

1. Create a dedicated GitHub repo (recommended under Knight-Logics org)
2. Push this project root to that repo
3. Confirm these files exist in root:
   - `Dockerfile`
   - `render.yaml`
   - `requirements.txt`
   - `app.py`

## 2. Render Blueprint Deploy

1. Sign in to Render
2. Choose **New +**
3. Choose **Blueprint**
4. Select your new GitHub repo
5. Approve deployment from `render.yaml`
6. Wait until service is live

## 3. Required Environment Variables

Set these in Render dashboard (Environment):

Required baseline:
- `SECRET_KEY` (strong random)
- `ADMIN_BILLING_KEY` (strong random)
- `APP_BASE_URL` = temporary Render URL first, then custom domain URL
- `APP_HOST` = `0.0.0.0`
- `APP_DEBUG` = `false`

App behavior defaults you can keep:
- `MAX_UPLOAD_MB` = `4096`
- `ALLOW_SHARED_ELEVENLABS_KEY` = `false`
- `REQUIRE_PAYMENT_FOR_SHARED_KEY` = `true`
- `SHARED_KEY_RENDER_PRICE_CREDITS` = `1`

Billing (only if using credits/payments):
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PUBLISHABLE_KEY`
- `STRIPE_SUCCESS_URL`
- `STRIPE_CANCEL_URL`
- `STRIPE_CURRENCY` (default `usd`)
- `STRIPE_PRICE_1_CREDIT_CENTS` (default `100`)

Email recovery (only if using account recovery emails):
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASS`
- `SMTP_FROM`
- `APP_NAME`

Narration (only if app-hosted narration mode is enabled):
- `ELEVENLABS_API_KEY`
- `ELEVENLABS_VOICE_ID`

## 4. Persistent Disk

The blueprint mounts persistent storage at `/app/workspace`.

Verify disk is attached and healthy in Render:
- Disk name: `videoforge-workspace`
- Mount path: `/app/workspace`

## 5. Custom Domain

1. In Render service settings, add custom domain:
   - `videoforge.knightlogics.com`
2. Add DNS records in your domain provider exactly as Render instructs
3. Wait for SSL to provision
4. Update `APP_BASE_URL` to:
   - `https://videoforge.knightlogics.com`

## 6. Smoke Test

Run these checks after deploy:

1. `GET /health` returns OK JSON
2. Home page `/` loads
3. Upload 3 small clips and render without narration
4. Download final output
5. If enabled, test credits flow and Stripe webhook
6. If enabled, test email recovery flow

## 7. Link from KnightLogics

After domain is live, verify these links resolve:
- `https://knightlogics.com/videoforge.html`
- `https://videoforge.knightlogics.com`

## Vercel note

Vercel is excellent for the static KnightLogics site, but it is not a strong fit for this app's FFmpeg-heavy long-running backend workload and writable-storage needs.
