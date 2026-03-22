# VideoForge Studio

A web application for rendering ranked/countdown-style videos from uploaded clips. Built with Python (Flask), FFmpeg, Pillow, Stripe, and ElevenLabs.

> Developed by [Knight Logics](https://knightlogics.com)

Recommended public deployment: its own repository in the Knight Logics GitHub organization, published on a subdomain such as `videoforge.knightlogics.com`.


## Features

- **Drag-and-drop clip upload** — Upload 3–10 video clips per render job
- **Animated overlays** — Ranked number reveals + animated title cards generated via Pillow
- **ElevenLabs narration** — Optional AI-generated voiceover with synced word captions
- **Intermissions** — Configurable transition segments between clips
- **Background music** — Optional mix-in with adjustable volume
- **Output presets** — 1440×2560 (portrait), 1920×1080 (landscape), and custom dimensions
- **Credit billing system** — Stripe-powered credit purchases with per-render deduction
- **Email recovery** — Link your access token to an email for recovery via Gmail SMTP
- **Job queue** — Threaded background render jobs with real-time SSE progress updates
- **Audit log** — Append-only JSONL billing audit trail

---

## Why RawGitHack Will Not Work

RawGitHack is for serving static files (HTML/CSS/JS) directly from a Git repository.

VideoForge Studio is not a static app. It requires:

- Python server execution (Flask + Waitress)
- FFmpeg processes at runtime
- Writable server storage for uploads/jobs/outputs
- Server-side billing/token handling

Because of this, use a backend host (for example Render, Railway, Fly.io, or a VPS with Docker), not RawGitHack.

---

## Free Deployment Option (No Monthly Hosting Bill)

If you need zero monthly hosting cost, run VideoForge on your own machine and expose it using a Cloudflare Tunnel.

This keeps infrastructure cost at $0, with these tradeoffs:

- Your computer must stay on while the app is public
- Upload/render performance depends on your machine and internet
- Availability is not guaranteed like managed cloud hosting

### Quick temporary public URL (free)

1. Start the app locally:
  - `./run_prod.ps1`
2. In another terminal, run:
  - `cloudflared tunnel --url http://127.0.0.1:5050`
3. Cloudflare prints a temporary `trycloudflare.com` URL you can share.

### Stable free custom domain URL

Use this when you want `videoforge.knightlogics.com` without a paid host:

1. Move DNS for your domain to Cloudflare (free plan)
2. Install `cloudflared` on the machine running VideoForge
3. Authenticate once:
  - `cloudflared tunnel login`
4. Create a named tunnel:
  - `cloudflared tunnel create videoforge`
5. Route DNS:
  - `cloudflared tunnel route dns videoforge videoforge.knightlogics.com`
6. Run the tunnel mapped to local app:
  - `cloudflared tunnel --url http://127.0.0.1:5050 --hostname videoforge.knightlogics.com`

When this tunnel is running, your app is publicly reachable at `https://videoforge.knightlogics.com` with no monthly hosting bill.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Web server | Python 3.11+ · Flask · Waitress (WSGI) |
| Video processing | FFmpeg |
| Image / overlay generation | Pillow |
| Narration (optional) | ElevenLabs REST API |
| Payments | Stripe Checkout |
| Email | SMTP · Gmail App Password |
| Config | python-dotenv |

---

## Quick Start

### 1. Prerequisites

- Python 3.11+
- [FFmpeg](https://ffmpeg.org/download.html) — must be on system `PATH`
- A Stripe account (optional — credit purchasing disabled without it)
- A Gmail App Password (optional — email recovery disabled without it)

### 2. Set up Python environment

```powershell
# From the project root
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. Configure environment

```powershell
Copy-Item .env.example .env
# Edit .env with your keys (see Configuration section below)
```

### 4. Run

```powershell
# Production (Waitress WSGI)
.\run_prod.ps1

# Development (Flask dev server, auto-reload)
.\run_dev.ps1
```

The app will be available at **http://localhost:5050**

For public hosting, deploy this repository as a standalone service instead of trying to fold it into the static Knight Logics website repo. This app needs Python execution, FFmpeg, writable storage, and long-running render jobs, so it belongs in its own backend-capable deployment target.

---

## Production Deploy (Docker)

This repository is already container-ready via `Dockerfile` and can be deployed to any provider that supports Docker containers.

Recommended public URL pattern:

- `https://videoforge.knightlogics.com`

### Minimum deployment requirements

- Docker runtime with FFmpeg available inside the container (handled by included `Dockerfile`)
- Writable runtime storage for:
  - `workspace/uploads`
  - `workspace/jobs`
  - `workspace/outputs`
  - `workspace/billing_tokens.json`
  - `workspace/billing_audit.jsonl`
- Environment variables set from `.env.example`

### Basic provider-agnostic flow

1. Create a new GitHub repository for this app (recommended org: Knight-Logics)
2. Push this project and connect it to your container host
3. Set environment variables from `.env.example`
4. Set `APP_BASE_URL` to your live domain (for example `https://videoforge.knightlogics.com`)
5. Ensure your domain DNS points to the deployment
6. Validate health endpoint:
   - `GET /health`

### Render quick deploy (included in this repo)

This repository now includes `render.yaml` for one-click Render Blueprint deployment.

1. Push this project to its own GitHub repository
2. In Render, choose **New + > Blueprint**
3. Select your repository
4. Confirm `render.yaml` values, then deploy
5. Add required secrets in Render dashboard:
  - Stripe keys (if billing enabled)
  - SMTP values (if email recovery enabled)
  - ElevenLabs key (if shared hosted narration enabled)
6. Point DNS for `videoforge.knightlogics.com` to the Render service
7. Update `APP_BASE_URL` to your final domain and redeploy if needed

### Post-deploy smoke test

1. Open `/health` and confirm status OK
2. Open `/` and confirm UI loads
3. Run one render job without narration
4. Run one render job with narration (if enabled)
5. Verify output download works

---

## Configuration (`.env`)

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | Yes | Random secret for session signing — generate one: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `MAX_UPLOAD_MB` | No | Max upload size in MB (default: `4096`) |
| `FREE_TRIAL_CREDITS` | No | Free credits per new IP (default: `3`) |
| `STRIPE_SECRET_KEY` | For billing | Stripe secret key |
| `STRIPE_PUBLISHABLE_KEY` | For billing | Stripe publishable key |
| `STRIPE_WEBHOOK_SECRET` | Recommended | Stripe webhook signing secret |
| `STRIPE_SUCCESS_URL` | No | Redirect after successful payment |
| `STRIPE_PRICE_1_CREDIT_CENTS` | No | Price per credit in cents (default: `100` = $1.00) |
| `SMTP_HOST` | For email | `smtp.gmail.com` |
| `SMTP_PORT` | For email | `587` |
| `SMTP_USER` | For email | Your Gmail address |
| `SMTP_PASS` | For email | 16-character Gmail App Password |
| `SMTP_FROM` | For email | Display name + address, e.g. `VideoForge Studio <you@gmail.com>` |
| `APP_BASE_URL` | For email | Full URL shown in recovery emails (default: `http://127.0.0.1:5050`) |
| `ALLOW_SHARED_ELEVENLABS_KEY` | No | Allow users to use your hosted ElevenLabs key (default: `false`) |
| `ELEVENLABS_API_KEY` | If shared key | Your ElevenLabs API key |
| `ADMIN_BILLING_KEY` | No | Admin key for `/api/admin/*` endpoints |

---

## Project Structure

```
VideoForge-Studio/
  app.py                  # Flask application + all route handlers
  wsgi.py                 # WSGI entry point (for Waitress / Gunicorn)
  run_prod.ps1            # Production launcher (Waitress)
  run_dev.ps1             # Development launcher (Flask dev server)
  requirements.txt        # Python dependencies
  .env.example            # Environment variable template
  src/
    billing.py            # Credit store — thread-safe JSON billing ledger
    captions.py           # Word-timed caption frame generation
    ffmpeg_tools.py       # FFmpeg subprocess wrappers
    job_manager.py        # Threaded job queue + SSE event streaming
    models.py             # RenderSettings / ClipInput dataclasses
    narration.py          # ElevenLabs TTS + timestamp sync
    overlays.py           # Pillow-based number reveal + title animation frames
    pipeline_engine.py    # Full render pipeline orchestrator
    token_service.py      # Access token creation / validation
    utils.py              # Shared helpers
  static/
    app.js                # Frontend JS (fetch API, SSE progress, UI state)
    styles.css            # UI stylesheet
    knightlogics-logo.png # Brand asset
  templates/
    index.html            # Single-page app shell
  workspace/              # Runtime data (gitignored)
    uploads/
    jobs/
    outputs/
```

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | App UI |
| `GET` | `/health` | Health check |
| `GET` | `/api/app-config` | App feature flags |
| `GET` | `/api/billing/config` | Billing + SMTP status |
| `POST` | `/api/token/claim` | Claim a token (get free trial credits) |
| `GET` | `/api/token/balance` | Check credit balance |
| `POST` | `/api/token/link-email` | Link recovery email to token |
| `POST` | `/api/token/send-recovery` | Send recovery email |
| `POST` | `/api/token/restore` | Restore token from email |
| `POST` | `/api/render/start` | Submit a render job |
| `GET` | `/api/render/status/<job_id>` | Job status |
| `GET` | `/api/render/stream/<job_id>` | SSE progress stream |
| `GET` | `/api/render/download/<job_id>` | Download rendered video |
| `POST` | `/api/payments/create-checkout-session` | Start Stripe checkout |
| `POST` | `/api/payments/webhook` | Stripe webhook handler |

---

## License

MIT — see [LICENSE](LICENSE)
