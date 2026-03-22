from __future__ import annotations

import json
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request, send_from_directory
import stripe
from werkzeug.utils import secure_filename

from src.billing import BillingStore
from src.job_manager import JobManager
from src.models import ClipInput, RenderSettings
from src.token_service import create_paid_access_token, is_valid_paid_access_token

load_dotenv()

APP_ROOT = Path(__file__).parent
WORKSPACE = APP_ROOT / "workspace"
UPLOADS = WORKSPACE / "uploads"
OUTPUTS = WORKSPACE / "outputs"
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "4096"))
MAX_OUTPUT_DIMENSION = int(os.environ.get("MAX_OUTPUT_DIMENSION", "4096"))
ALLOW_SHARED_ELEVENLABS_KEY = os.environ.get("ALLOW_SHARED_ELEVENLABS_KEY", "false").lower() == "true"
REQUIRE_PAYMENT_FOR_SHARED_KEY = os.environ.get("REQUIRE_PAYMENT_FOR_SHARED_KEY", "true").lower() == "true"
SHARED_KEY_RENDER_PRICE_CREDITS = int(os.environ.get("SHARED_KEY_RENDER_PRICE_CREDITS", "1"))
ADMIN_BILLING_KEY = os.environ.get("ADMIN_BILLING_KEY", "")
BILLING_TOKENS_FILE = Path(os.environ.get("BILLING_TOKENS_FILE", str(WORKSPACE / "billing_tokens.json")))
BILLING_AUDIT_FILE = Path(os.environ.get("BILLING_AUDIT_FILE", str(WORKSPACE / "billing_audit.jsonl")))
STRIPE_SECRET_KEY = os.environ.get("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
STRIPE_SUCCESS_URL = os.environ.get("STRIPE_SUCCESS_URL", "http://127.0.0.1:5050/?payment=success")
STRIPE_CANCEL_URL = os.environ.get("STRIPE_CANCEL_URL", "http://127.0.0.1:5050/?payment=cancel")
STRIPE_CURRENCY = os.environ.get("STRIPE_CURRENCY", "usd")
STRIPE_PRICE_1_CREDIT_CENTS = int(os.environ.get("STRIPE_PRICE_1_CREDIT_CENTS", "100"))
FREE_TRIAL_CREDITS = max(0, int(os.environ.get("FREE_TRIAL_CREDITS", "3")))

SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
SMTP_FROM = os.environ.get("SMTP_FROM", "")
APP_NAME = os.environ.get("APP_NAME", "VideoForge Studio")
APP_BASE_URL = os.environ.get("APP_BASE_URL", "http://127.0.0.1:5050")
APP_HOST = os.environ.get("APP_HOST", "127.0.0.1")
APP_PORT = int(os.environ.get("APP_PORT", os.environ.get("PORT", "5050")))
APP_DEBUG = os.environ.get("APP_DEBUG", "false").lower() == "true"
SMTP_CONFIGURED = bool(SMTP_HOST and SMTP_USER and SMTP_PASS and SMTP_FROM)

VIDEO_RENDER_PRICE_CREDITS = max(1, int(os.environ.get("VIDEO_RENDER_PRICE_CREDITS", "1")))
NARRATION_CHARS_PER_CREDIT = max(1, int(os.environ.get("NARRATION_CHARS_PER_CREDIT", "1000")))
ALLOWED_VIDEO_EXTENSIONS = {"mp4", "mov", "mkv", "webm"}
ALLOWED_AUDIO_EXTENSIONS = {"mp3", "wav", "m4a", "aac"}
CLIP_MIN = int(os.environ.get("CLIP_MIN", "3"))
CLIP_MAX = int(os.environ.get("CLIP_MAX", "10"))

job_manager = JobManager(WORKSPACE)
billing_store = BillingStore(BILLING_TOKENS_FILE, BILLING_AUDIT_FILE)

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY


def _allowed(filename: str, allowed: set[str]) -> bool:
    if "." not in filename:
        return False
    return filename.rsplit(".", 1)[1].lower() in allowed


def _save_upload(file_storage, target_dir: Path, prefix: str) -> Path:
    safe = secure_filename(file_storage.filename)
    name = f"{prefix}_{safe}"
    target_dir.mkdir(parents=True, exist_ok=True)
    dst = target_dir / name
    file_storage.save(dst)
    return dst


def _get_client_ip() -> str:
    forwarded = (request.headers.get("X-Forwarded-For") or "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip() or "unknown"
    return (request.remote_addr or "unknown").strip()


def _get_claim_key() -> str:
    return f"ip:{_get_client_ip()}"


def _send_recovery_email(to_email: str, token: str) -> bool:
    if not SMTP_CONFIGURED:
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Your {APP_NAME} Access Code"
        msg["From"] = SMTP_FROM
        msg["To"] = to_email
        body = (
            f"Here is your {APP_NAME} access code:\n\n"
            f"  {token}\n\n"
            f"To restore your access:\n"
            f"1. Visit {APP_BASE_URL}\n"
            f"2. Click \"Restore Access\" in the app\n"
            f"3. Enter this code\n\n"
            f"If you didn't request this email, you can ignore it.\n"
        )
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        return True
    except Exception:
        return False


def _send_confirmation_email(to_email: str, token: str) -> bool:
    """Send confirmation after email is linked to token."""
    if not SMTP_CONFIGURED:
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"{APP_NAME} — Email Secured"
        msg["From"] = SMTP_FROM
        msg["To"] = to_email
        body = (
            f"Your email has been linked to your {APP_NAME} access code.\n\n"
            f"You can now recover this code at any time by:\n"
            f"1. Opening {APP_BASE_URL}\n"
            f"2. Clicking \"Lost access or switching devices? Recover by email\"\n"
            f"3. Entering this email address\n\n"
            f"We'll send you your access code so you can restore your account from any device.\n\n"
            f"Your access code (keep this safe):\n"
            f"  {token}\n\n"
            f"If you didn't link this email, please reply to this message.\n"
        )
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        return True
    except Exception:
        return False


def _build_checkout_success_url() -> str:
    if "{CHECKOUT_SESSION_ID}" in STRIPE_SUCCESS_URL:
        return STRIPE_SUCCESS_URL
    separator = "&" if "?" in STRIPE_SUCCESS_URL else "?"
    return f"{STRIPE_SUCCESS_URL}{separator}session_id={{CHECKOUT_SESSION_ID}}"


def _require_admin_billing_key() -> Response | tuple[Response, int] | None:
    if not ADMIN_BILLING_KEY:
        return jsonify({"error": "ADMIN_BILLING_KEY is not configured on the server"}), 403

    provided = (request.headers.get("X-Admin-Billing-Key") or request.form.get("admin_key") or request.args.get("admin_key") or "").strip()
    if provided != ADMIN_BILLING_KEY:
        return jsonify({"error": "Unauthorized"}), 401

    return None


def _serialize_stripe_session(session) -> dict:
    metadata = session.get("metadata") or {}
    customer_details = session.get("customer_details") or {}
    purchase_id = str(session.get("id") or "").strip()
    token = str(metadata.get("token") or session.get("client_reference_id") or "").strip()
    credits_raw = metadata.get("credits") or "1"
    try:
        credits = int(credits_raw)
    except ValueError:
        credits = 0

    return {
        "session_id": purchase_id,
        "created": session.get("created"),
        "amount_total": session.get("amount_total"),
        "currency": session.get("currency"),
        "payment_status": session.get("payment_status"),
        "customer_email": customer_details.get("email") or session.get("customer_email") or "",
        "token": token,
        "credits": credits,
        "already_processed": bool(purchase_id and billing_store.is_purchase_processed(purchase_id)),
        "status": billing_store.get_status(token) if token and is_valid_paid_access_token(token) else None,
    }


def _finalize_paid_checkout_session(session) -> tuple[str, int, bool]:
    purchase_id = str(session.get("id") or "").strip()
    metadata = session.get("metadata") or {}
    token = str(metadata.get("token") or session.get("client_reference_id") or "").strip()
    credits_raw = metadata.get("credits") or "1"
    try:
        credits = int(credits_raw)
    except ValueError:
        credits = 0

    already_processed = bool(purchase_id and billing_store.is_purchase_processed(purchase_id))

    if purchase_id and not already_processed:
        if session.get("payment_status") == "paid" and token and credits > 0:
            billing_store.add_credits(token, credits, source="stripe_checkout")
        billing_store.mark_purchase_processed(purchase_id)

    return token, credits, already_processed


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")

    @app.errorhandler(413)
    def too_large(_error):
        return jsonify({"error": f"Upload too large. MAX_UPLOAD_MB is currently {MAX_UPLOAD_MB} MB."}), 413

    @app.get("/")
    def index() -> str:
        return render_template("index.html")

    @app.post("/api/render")
    def start_render():
        title_line_1 = (request.form.get("title_line_1") or "Top 5 Funniest").strip()
        title_line_2 = (request.form.get("title_line_2") or "Moments").strip()
        enable_narration = (request.form.get("enable_narration") or "").lower() == "true"
        include_music = (request.form.get("include_music") or "").lower() == "true"
        background_music_level_raw = (request.form.get("background_music_level") or "0.15").strip()
        use_intermissions = (request.form.get("use_intermissions") or "").lower() != "false"
        output_width_raw = (request.form.get("output_width") or "1440").strip()
        output_height_raw = (request.form.get("output_height") or "2560").strip()
        title_font_family = (request.form.get("title_font_family") or "gill-sans-ultra-bold").strip() or "gill-sans-ultra-bold"
        list_font_family = (request.form.get("list_font_family") or "gill-sans-ultra-bold").strip() or "gill-sans-ultra-bold"
        title_font_size_raw = (request.form.get("title_font_size") or "96").strip()
        list_font_size_raw = (request.form.get("list_font_size") or "56").strip()
        intermission_opacity_raw = (request.form.get("intermission_opacity") or "100").strip()

        try:
            output_width = int(output_width_raw)
            output_height = int(output_height_raw)
            title_font_size = int(title_font_size_raw)
            list_font_size = int(list_font_size_raw)
            intermission_opacity = float(intermission_opacity_raw)
            background_music_level = float(background_music_level_raw)
        except ValueError:
            return jsonify({"error": "output_width, output_height, title_font_size, list_font_size, intermission_opacity, and background_music_level must be numeric"}), 400

        if output_width < 360 or output_height < 360:
            return jsonify({"error": "output dimensions must be at least 360 pixels"}), 400
        if output_width > MAX_OUTPUT_DIMENSION or output_height > MAX_OUTPUT_DIMENSION:
            return jsonify({"error": f"output dimensions cannot exceed {MAX_OUTPUT_DIMENSION}px"}), 400
        if title_font_size < 24 or title_font_size > 240:
            return jsonify({"error": "title_font_size must be between 24 and 240"}), 400
        if list_font_size < 20 or list_font_size > 180:
            return jsonify({"error": "list_font_size must be between 20 and 180"}), 400

        clip_files = request.files.getlist("clips")
        captions_json = request.form.get("captions_json")
        captions = request.form.getlist("captions")
        if captions_json:
            try:
                captions = json.loads(captions_json)
            except json.JSONDecodeError:
                return jsonify({"error": "Invalid captions JSON"}), 400

        if len(clip_files) < CLIP_MIN or len(clip_files) > CLIP_MAX:
            return jsonify({"error": f"Clip count must be between {CLIP_MIN} and {CLIP_MAX}"}), 400

        if len(captions) != len(clip_files):
            return jsonify({"error": "The number of captions must match the number of clips"}), 400

        clip_inputs: list[ClipInput] = []
        clip_upload_root = UPLOADS / "pending"

        for index, file_storage in enumerate(clip_files, start=1):
            if not file_storage.filename or not _allowed(file_storage.filename, ALLOWED_VIDEO_EXTENSIONS):
                return jsonify({"error": f"Clip {index} has an invalid extension"}), 400

            saved = _save_upload(file_storage, clip_upload_root, f"clip{index}")
            caption_text = str(captions[index - 1]).strip()
            if not caption_text:
                return jsonify({"error": f"Caption {index} cannot be empty"}), 400
            clip_inputs.append(ClipInput(file_path=saved, caption=caption_text))

        background_music = None
        music_file = request.files.get("background_music")
        if include_music and music_file and music_file.filename:
            if not _allowed(music_file.filename, ALLOWED_AUDIO_EXTENSIONS):
                return jsonify({"error": "Background music has an invalid extension"}), 400
            background_music = _save_upload(music_file, clip_upload_root, "music")

        settings = RenderSettings(
            title_line_1=title_line_1,
            title_line_2=title_line_2,
            clips=clip_inputs,
            output_width=output_width,
            output_height=output_height,
            title_font_family=title_font_family,
            list_font_family=list_font_family,
            title_font_size=title_font_size,
            list_font_size=list_font_size,
            include_music=include_music,
            background_music=background_music,
            background_music_level=background_music_level,
            enable_narration=enable_narration,
            use_intermissions=use_intermissions,
            intermission_opacity=intermission_opacity,
            elevenlabs_api_key=(request.form.get("elevenlabs_api_key") or "").strip() or None,
            elevenlabs_voice_id=(request.form.get("elevenlabs_voice_id") or "").strip() or None,
        )

        charged_token = None
        consumed_free_trial_token = None
        if settings.enable_narration:
            has_user_key = bool(settings.elevenlabs_api_key)
            has_server_key = bool(os.environ.get("ELEVENLABS_API_KEY", ""))
            if not has_user_key and not (ALLOW_SHARED_ELEVENLABS_KEY and has_server_key):
                return jsonify(
                    {
                        "error": "Narration requires an ElevenLabs API key. Provide elevenlabs_api_key per request, or explicitly enable ALLOW_SHARED_ELEVENLABS_KEY on your own private server."
                    }
                ), 400

            if not has_user_key and ALLOW_SHARED_ELEVENLABS_KEY and has_server_key and REQUIRE_PAYMENT_FOR_SHARED_KEY:
                paid_token = (request.form.get("paid_access_token") or "").strip()
                if not paid_token:
                    return jsonify(
                        {
                            "error": "A paid_access_token is required for server-key narration."
                        }
                    ), 402

                if not is_valid_paid_access_token(paid_token):
                    return jsonify({"error": "Invalid paid_access_token format."}), 400

                consumed, remaining = billing_store.consume_credits(
                    token=paid_token,
                    cost=SHARED_KEY_RENDER_PRICE_CREDITS,
                    source="shared_key_render",
                )
                if not consumed:
                    return jsonify(
                        {
                            "error": "Insufficient token credits for narration.",
                            "required_credits": SHARED_KEY_RENDER_PRICE_CREDITS,
                            "remaining_credits": remaining,
                        }
                    ), 402
                charged_token = paid_token
        else:
            access_token = (request.form.get("paid_access_token") or "").strip()
            if access_token and is_valid_paid_access_token(access_token):
                consumed, _remaining = billing_store.consume_free_trial_use(
                    token=access_token,
                    count=1,
                    source="final_render_free_trial",
                )
                if consumed:
                    consumed_free_trial_token = access_token

        try:
            job = job_manager.create_job(settings)
        except Exception as exc:
            if charged_token:
                billing_store.add_credits(
                    token=charged_token,
                    credits=SHARED_KEY_RENDER_PRICE_CREDITS,
                    source="shared_key_render_refund_enqueue_failure",
                )
            if consumed_free_trial_token:
                billing_store.restore_free_trial_use(
                    token=consumed_free_trial_token,
                    count=1,
                    source="final_render_free_trial_refund_enqueue_failure",
                )
            return jsonify({"error": str(exc)}), 500

        return jsonify({"job_id": job.job_id})

    @app.post("/api/preview")
    def generate_preview():
        title_line_1 = (request.form.get("title_line_1") or "Top 5 Funniest").strip()
        title_line_2 = (request.form.get("title_line_2") or "Moments").strip()
        output_width_raw = (request.form.get("output_width") or "1440").strip()
        output_height_raw = (request.form.get("output_height") or "2560").strip()
        title_font_family = (request.form.get("title_font_family") or "gill-sans-ultra-bold").strip() or "gill-sans-ultra-bold"
        list_font_family = (request.form.get("list_font_family") or "gill-sans-ultra-bold").strip() or "gill-sans-ultra-bold"
        title_font_size_raw = (request.form.get("title_font_size") or "96").strip()
        list_font_size_raw = (request.form.get("list_font_size") or "56").strip()
        use_intermissions = (request.form.get("use_intermissions") or "").lower() != "false"
        intermission_opacity_raw = (request.form.get("intermission_opacity") or "100").strip()

        try:
            output_width = int(output_width_raw)
            output_height = int(output_height_raw)
            title_font_size = int(title_font_size_raw)
            list_font_size = int(list_font_size_raw)
            intermission_opacity = float(intermission_opacity_raw)
        except ValueError:
            return jsonify({"error": "Dimension, font, and opacity values must be numeric"}), 400

        if output_width < 360 or output_height < 360:
            return jsonify({"error": "output dimensions must be at least 360 pixels"}), 400
        if output_width > MAX_OUTPUT_DIMENSION or output_height > MAX_OUTPUT_DIMENSION:
            return jsonify({"error": f"output dimensions cannot exceed {MAX_OUTPUT_DIMENSION}px"}), 400

        clip_files = request.files.getlist("clips")
        captions_json = request.form.get("captions_json")
        captions = request.form.getlist("captions")
        if captions_json:
            try:
                captions = json.loads(captions_json)
            except json.JSONDecodeError:
                return jsonify({"error": "Invalid captions JSON"}), 400

        if len(clip_files) < 1:
            return jsonify({"error": "At least 1 clip is required for preview"}), 400
        if len(clip_files) > CLIP_MAX:
            return jsonify({"error": f"Preview supports up to {CLIP_MAX} clips"}), 400

        clip_inputs: list[ClipInput] = []
        clip_upload_root = UPLOADS / "preview"

        for index, file_storage in enumerate(clip_files, start=1):
            if not file_storage.filename or not _allowed(file_storage.filename, ALLOWED_VIDEO_EXTENSIONS):
                return jsonify({"error": f"Clip {index} has an invalid extension"}), 400

            saved = _save_upload(file_storage, clip_upload_root, f"clip{index}")
            caption_text = str(captions[index - 1]).strip() if index <= len(captions) else f"Clip {index}"
            clip_inputs.append(ClipInput(file_path=saved, caption=caption_text))

        settings = RenderSettings(
            title_line_1=title_line_1,
            title_line_2=title_line_2,
            clips=clip_inputs,
            output_width=output_width,
            output_height=output_height,
            title_font_family=title_font_family,
            list_font_family=list_font_family,
            title_font_size=title_font_size,
            list_font_size=list_font_size,
            fps=30,
            include_music=False,
            background_music=None,
            enable_narration=False,
            use_intermissions=use_intermissions,
            intermission_opacity=intermission_opacity,
            elevenlabs_api_key=None,
            elevenlabs_voice_id=None,
        )

        try:
            job = job_manager.create_job(settings)
        except Exception as exc:
            return jsonify({"error": f"Could not queue preview: {str(exc)}"}), 500

        return jsonify({"job_id": job.job_id})

    @app.get("/api/app-config")
    def app_config():
        return jsonify(
            {
                "max_upload_mb": MAX_UPLOAD_MB,
                "max_output_dimension": MAX_OUTPUT_DIMENSION,
                "clip_count": {
                    "min": CLIP_MIN,
                    "max": CLIP_MAX,
                    "default": 5,
                },
                "font_options": [
                    {"id": "gill-sans-ultra-bold", "label": "Gill Sans Ultra Bold"},
                    {"id": "impact", "label": "Impact"},
                    {"id": "arial-bold", "label": "Arial Bold"},
                    {"id": "bahnschrift-semi", "label": "Bahnschrift SemiBold"},
                    {"id": "segoe-ui-bold", "label": "Segoe UI Bold"},
                ],
                "output_presets": [
                    {"label": "16:9 YouTube HD (1920x1080)", "width": 1920, "height": 1080},
                    {"label": "16:9 YouTube 1440p (2560x1440)", "width": 2560, "height": 1440},
                    {"label": "16:9 YouTube 4K (3840x2160)", "width": 3840, "height": 2160},
                    {"label": "9:16 (1080x1920)", "width": 1080, "height": 1920},
                    {"label": "9:16 HQ (1440x2560)", "width": 1440, "height": 2560},
                    {"label": "1440x1600", "width": 1440, "height": 1600},
                    {"label": "16:19 (1440x1710)", "width": 1440, "height": 1710},
                    {"label": "4:5 (1440x1800)", "width": 1440, "height": 1800},
                ],
            }
        )

    @app.get("/api/jobs/<job_id>")
    def get_job(job_id: str):
        job = job_manager.get_job(job_id)
        if not job:
            return jsonify({"error": "Job not found"}), 404

        return jsonify(
            {
                "job_id": job.job_id,
                "status": job.status,
                "progress": job.progress,
                "message": job.message,
                "output_file": job.output_file,
                "error": job.error,
                "created_at": job.created_at,
            }
        )

    @app.get("/api/jobs/<job_id>/events")
    def stream_job_events(job_id: str):
        def event_stream():
            for event in job_manager.stream_events(job_id):
                yield f"event: {event.event}\n"
                yield f"data: {json.dumps(event.payload)}\n\n"

        return Response(event_stream(), mimetype="text/event-stream")

    @app.get("/outputs/<filename>")
    def download_output(filename: str):
        safe = secure_filename(filename)
        return send_from_directory(OUTPUTS, safe, as_attachment=True)

    @app.get("/health")
    def health():
        return jsonify({"ok": True, "app": "AutoTop5 Showcase App", "stripe_configured": bool(STRIPE_SECRET_KEY)})

    @app.get("/api/billing/config")
    def billing_config():
        return jsonify(
            {
                "shared_key_enabled": ALLOW_SHARED_ELEVENLABS_KEY,
                "shared_key_requires_payment": REQUIRE_PAYMENT_FOR_SHARED_KEY,
                "shared_key_render_price_credits": SHARED_KEY_RENDER_PRICE_CREDITS,
                "video_render_price_credits": VIDEO_RENDER_PRICE_CREDITS,
                "narration_chars_per_credit": NARRATION_CHARS_PER_CREDIT,
                "free_trial_credits": FREE_TRIAL_CREDITS,
                "free_trial_claim_scope": "ip",
                "stripe_configured": bool(STRIPE_SECRET_KEY),
                "price_per_credit_cents": STRIPE_PRICE_1_CREDIT_CENTS,
                "currency": STRIPE_CURRENCY,
                "email_recovery_configured": SMTP_CONFIGURED,
            }
        )

    @app.get("/api/billing/status")
    def billing_status():
        token = (request.args.get("token") or "").strip()
        claim = billing_store.get_free_trial_claim(_get_claim_key())

        if token:
            if not is_valid_paid_access_token(token):
                return jsonify({"error": "invalid token format"}), 400
            status = billing_store.get_status(token)
        elif claim and claim.get("token"):
            status = billing_store.get_status(str(claim.get("token") or ""))
        else:
            status = {
                "credits": 0,
                "paid_credits": 0,
                "free_trial_total": 0,
                "free_trial_remaining": 0,
            }

        return jsonify(
            {
                **status,
                "token": token or (claim.get("token") if claim else ""),
                "free_trial_claimed": bool(claim),
                "free_trial_claim_scope": "ip",
            }
        )

    @app.post("/api/billing/link-email")
    def billing_link_email():
        token = (request.form.get("token") or "").strip()
        email = (request.form.get("email") or "").strip().lower()

        if not token:
            return jsonify({"error": "token is required"}), 400
        if not is_valid_paid_access_token(token):
            return jsonify({"error": "invalid token format"}), 400
        if not email or "@" not in email or len(email) > 254:
            return jsonify({"error": "A valid email address is required."}), 400

        success, message = billing_store.link_email(token, email)
        if not success:
            return jsonify({"error": message}), 409

        # Send confirmation email immediately after successful link
        confirmation_sent = _send_confirmation_email(email, token)

        return jsonify({"ok": True, "linked_email": email, "confirmation_email_sent": confirmation_sent})

    @app.post("/api/billing/recover")
    def billing_recover():
        from datetime import datetime, timezone

        email = (request.form.get("email") or "").strip().lower()
        if not email or "@" not in email or len(email) > 254:
            return jsonify({"error": "A valid email address is required."}), 400

        # Always the same message to prevent email enumeration
        generic_ok = {"ok": True, "message": "If that email is on file, you'll receive your access code shortly."}

        if not SMTP_CONFIGURED:
            return jsonify({"error": "Email recovery is not configured on this server. Contact support."}), 503

        stored_token = billing_store.get_token_by_email(email)
        if not stored_token:
            return jsonify(generic_ok)

        # Rate limit: 1 recovery email per hour per address
        last_sent = billing_store.get_last_recovery_sent(email)
        if last_sent:
            try:
                last_dt = datetime.fromisoformat(last_sent.replace("Z", "+00:00"))
                elapsed = (datetime.now(timezone.utc) - last_dt).total_seconds()
                if elapsed < 3600:
                    return jsonify(generic_ok)
            except Exception:
                pass

        if _send_recovery_email(email, stored_token):
            billing_store.record_recovery_sent(email)

        return jsonify(generic_ok)

    @app.post("/api/admin/test-email-recovery")
    def admin_test_email_recovery():
        """Admin endpoint to test email recovery delivery (requires ADMIN_BILLING_KEY)."""
        admin_key = (request.form.get("admin_key") or "").strip()
        test_email = (request.form.get("test_email") or "").strip().lower()

        if not ADMIN_BILLING_KEY or admin_key != ADMIN_BILLING_KEY:
            return jsonify({"error": "Invalid or missing admin key."}), 403

        if not test_email or "@" not in test_email or len(test_email) > 254:
            return jsonify({"error": "A valid test email address is required."}), 400

        if not SMTP_CONFIGURED:
            return jsonify({"error": "SMTP is not configured on this server.", "smtp_configured": False}), 503

        # Generate a test token for demonstration
        test_token = "vf_test_" + ("abc123" * 4)[:24]

        # Try sending confirmation email
        confirmation_sent = _send_confirmation_email(test_email, test_token)
        # Try sending recovery email
        recovery_sent = _send_recovery_email(test_email, test_token)

        return jsonify(
            {
                "ok": confirmation_sent or recovery_sent,
                "confirmation_email_sent": confirmation_sent,
                "recovery_email_sent": recovery_sent,
                "smtp_configured": SMTP_CONFIGURED,
                "smtp_host": SMTP_HOST,
                "message": "Check your inbox (or spam folder) for test emails.",
            }
        )

    @app.post("/api/billing/create-token")
    def create_token():
        token = create_paid_access_token()
        free_trial_granted = False
        status = billing_store.get_status(token)

        if FREE_TRIAL_CREDITS > 0:
            free_trial_granted, _remaining = billing_store.claim_free_trial(
                token=token,
                claim_key=_get_claim_key(),
                credits=FREE_TRIAL_CREDITS,
                source="create_token_free_trial",
            )
            status = billing_store.get_status(token)

        return jsonify(
            {
                "token": token,
                "free_trial_granted": free_trial_granted,
                "free_trial_credits": FREE_TRIAL_CREDITS if free_trial_granted else 0,
                "credits": status["credits"],
                "paid_credits": status["paid_credits"],
                "free_trial_total": status["free_trial_total"],
                "free_trial_remaining": status["free_trial_remaining"],
            }
        )

    @app.post("/api/payments/create-checkout-session")
    def create_checkout_session():
        if not STRIPE_SECRET_KEY:
            return jsonify({"error": "Stripe is not configured on server"}), 503

        token = (request.form.get("token") or "").strip()
        credits_raw = (request.form.get("credits") or "1").strip()
        try:
            credits = int(credits_raw)
        except ValueError:
            return jsonify({"error": "credits must be an integer"}), 400

        if not token:
            return jsonify({"error": "token is required"}), 400
        if not is_valid_paid_access_token(token):
            return jsonify({"error": "invalid token format"}), 400
        if credits <= 0:
            return jsonify({"error": "credits must be > 0"}), 400

        unit_amount = STRIPE_PRICE_1_CREDIT_CENTS

        session = stripe.checkout.Session.create(
            mode="payment",
            success_url=_build_checkout_success_url(),
            cancel_url=STRIPE_CANCEL_URL,
            client_reference_id=token[:200],
            line_items=[
                {
                    "price_data": {
                        "currency": STRIPE_CURRENCY,
                        "product_data": {
                            "name": "VideoForge Narration Credit",
                            "description": "One shared ElevenLabs narration credit",
                        },
                        "unit_amount": unit_amount,
                    },
                    "quantity": credits,
                }
            ],
            metadata={
                "token": token,
                "credits": str(credits),
                "kind": "shared_narration_credit",
            },
        )

        return jsonify({"url": session.url, "session_id": session.id})

    @app.post("/api/payments/confirm-session")
    def confirm_checkout_session():
        if not STRIPE_SECRET_KEY:
            return jsonify({"error": "Stripe is not configured on server"}), 503

        session_id = (request.form.get("session_id") or "").strip()
        if not session_id:
            return jsonify({"error": "session_id is required"}), 400

        try:
            session = stripe.checkout.Session.retrieve(session_id)
        except Exception as exc:
            return jsonify({"error": f"Could not verify checkout session: {str(exc)}"}), 400

        if session.get("payment_status") != "paid":
            return jsonify({"error": "Checkout session is not paid yet."}), 409

        token, credits, already_processed = _finalize_paid_checkout_session(session)
        status = billing_store.get_status(token) if token and is_valid_paid_access_token(token) else None

        return jsonify(
            {
                "ok": True,
                "session_id": session_id,
                "token": token,
                "credited_credits": credits,
                "already_processed": already_processed,
                "status": status,
            }
        )

    @app.post("/api/payments/stripe-webhook")
    def stripe_webhook():
        if not STRIPE_WEBHOOK_SECRET:
            return jsonify({"error": "STRIPE_WEBHOOK_SECRET is not configured"}), 503

        payload = request.get_data(as_text=False)
        signature = request.headers.get("Stripe-Signature", "")

        try:
            event = stripe.Webhook.construct_event(payload, signature, STRIPE_WEBHOOK_SECRET)
        except ValueError:
            return jsonify({"error": "Invalid payload"}), 400
        except Exception:
            return jsonify({"error": "Invalid signature"}), 400

        if event.get("type") == "checkout.session.completed":
            session = event["data"]["object"]
            _finalize_paid_checkout_session(session)

        return jsonify({"received": True})

    @app.post("/api/admin/billing/credit")
    def admin_billing_credit():
        failure = _require_admin_billing_key()
        if failure is not None:
            return failure

        token = (request.form.get("token") or "").strip()
        credits_raw = (request.form.get("credits") or "").strip()
        if not token:
            return jsonify({"error": "token is required"}), 400
        if not is_valid_paid_access_token(token):
            return jsonify({"error": "invalid token format"}), 400

        try:
            credits = int(credits_raw)
        except ValueError:
            return jsonify({"error": "credits must be an integer"}), 400

        if credits <= 0:
            return jsonify({"error": "credits must be > 0"}), 400

        updated = billing_store.add_credits(token, credits, source="admin_credit")
        return jsonify({"token": token, "credits": updated})

    @app.get("/api/admin/payments/recent")
    def admin_recent_payments():
        failure = _require_admin_billing_key()
        if failure is not None:
            return failure

        if not STRIPE_SECRET_KEY:
            return jsonify({"error": "Stripe is not configured on server"}), 503

        try:
            limit = int((request.args.get("limit") or "10").strip())
        except ValueError:
            return jsonify({"error": "limit must be an integer"}), 400

        limit = max(1, min(limit, 25))

        try:
            sessions = stripe.checkout.Session.list(limit=limit)
        except Exception as exc:
            return jsonify({"error": f"Could not fetch Stripe sessions: {str(exc)}"}), 500

        items = []
        for session in sessions.auto_paging_iter():
            items.append(_serialize_stripe_session(session))
            if len(items) >= limit:
                break

        return jsonify({"ok": True, "sessions": items})

    @app.post("/api/admin/payments/reconcile-session")
    def admin_reconcile_session():
        failure = _require_admin_billing_key()
        if failure is not None:
            return failure

        if not STRIPE_SECRET_KEY:
            return jsonify({"error": "Stripe is not configured on server"}), 503

        session_id = (request.form.get("session_id") or "").strip()
        if not session_id:
            return jsonify({"error": "session_id is required"}), 400

        try:
            session = stripe.checkout.Session.retrieve(session_id)
        except Exception as exc:
            return jsonify({"error": f"Could not retrieve Stripe session: {str(exc)}"}), 400

        if session.get("payment_status") != "paid":
            return jsonify({"error": "Stripe session is not paid."}), 409

        token, credits, already_processed = _finalize_paid_checkout_session(session)
        status = billing_store.get_status(token) if token and is_valid_paid_access_token(token) else None

        return jsonify(
            {
                "ok": True,
                "session": _serialize_stripe_session(session),
                "credited_credits": credits,
                "already_processed": already_processed,
                "status": status,
            }
        )

    @app.post("/api/billing/token/balance")
    def get_token_balance():
        token = (request.form.get("token") or "").strip()
        if not token:
            return jsonify({"error": "token is required"}), 400
        if not is_valid_paid_access_token(token):
            return jsonify({"error": "invalid token format"}), 400

        status = billing_store.get_status(token)
        return jsonify({"token": token, **status})

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host=APP_HOST, port=APP_PORT, debug=APP_DEBUG)
