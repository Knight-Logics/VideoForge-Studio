from __future__ import annotations

import json
import logging
import math
import os
import smtplib
import sys
from collections import deque
from datetime import datetime
from hmac import compare_digest
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, Response, jsonify, render_template, request, send_from_directory, stream_with_context
import requests
import stripe
from werkzeug.utils import secure_filename

from src.billing import BillingStore
from src.job_manager import JobManager
from src.models import ClipInput, RenderSettings
from src.render_history import RenderHistory
from src.token_service import create_paid_access_token, is_valid_paid_access_token
from src.utils import get_resource_root, get_runtime_root

load_dotenv()

logging.basicConfig(
    level=os.environ.get("APP_LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("videoforge.app")

RESOURCE_ROOT = get_resource_root()
RUNTIME_ROOT = get_runtime_root()
APP_ROOT = RESOURCE_ROOT
WORKSPACE = RUNTIME_ROOT / "workspace"
UPLOADS = WORKSPACE / "uploads"
OUTPUTS = WORKSPACE / "outputs"
APP_LOG_FILE = Path(os.environ.get("APP_LOG_FILE", str(WORKSPACE / "logs" / "videoforge.log")))
RENDER_HISTORY_FILE = Path(os.environ.get("RENDER_HISTORY_FILE", str(WORKSPACE / "render_history.json")))
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "4096"))
MAX_OUTPUT_DIMENSION = int(os.environ.get("MAX_OUTPUT_DIMENSION", "4096"))
ALLOW_SHARED_ELEVENLABS_KEY = os.environ.get("ALLOW_SHARED_ELEVENLABS_KEY", "true").lower() == "true"
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
MAX_CHECKOUT_CREDITS = max(1, int(os.environ.get("MAX_CHECKOUT_CREDITS", "250")))
MAX_TITLE_LENGTH = max(32, int(os.environ.get("MAX_TITLE_LENGTH", "120")))
MAX_CAPTION_LENGTH = max(32, int(os.environ.get("MAX_CAPTION_LENGTH", "240")))

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
APP_VERSION = (os.environ.get("APP_VERSION") or "0.4.3").strip()
APP_UPDATE_ENABLED = os.environ.get("APP_UPDATE_ENABLED", "true").lower() == "true"
APP_UPDATE_REPO = (os.environ.get("APP_UPDATE_REPO") or "Knight-Logics/VideoForge-Studio").strip()
SMTP_CONFIGURED = bool(SMTP_HOST and SMTP_USER and SMTP_PASS and SMTP_FROM)

VIDEO_RENDER_PRICE_CREDITS = max(1, int(os.environ.get("VIDEO_RENDER_PRICE_CREDITS", "1")))
NARRATION_WORDS_PER_CREDIT = max(1, int(os.environ.get("NARRATION_WORDS_PER_CREDIT", "30")))
ALLOWED_VIDEO_EXTENSIONS = {"mp4", "mov", "mkv", "webm"}
ALLOWED_AUDIO_EXTENSIONS = {"mp3", "wav", "m4a", "aac"}
CLIP_MIN = int(os.environ.get("CLIP_MIN", "3"))
CLIP_MAX = int(os.environ.get("CLIP_MAX", "10"))
DEFAULT_ELEVENLABS_VOICE_ID = (os.environ.get("ELEVENLABS_VOICE_ID") or "").strip()
ELEVENLABS_VOICE_OPTIONS_JSON = (os.environ.get("ELEVENLABS_VOICE_OPTIONS_JSON") or "").strip()

DEFAULT_ELEVENLABS_VOICE_OPTIONS = [
    {"id": "JBFqnCBsd6RMkjVDRZzb", "label": "George"},
    {"id": "9BWtsMINqrJLrRacOk9x", "label": "Aria"},
    {"id": "EXAVITQu4vr4xnSDxMaL", "label": "Sarah"},
    {"id": "TX3LPaxmHKxFdv7VOQHJ", "label": "Liam"},
]

job_manager = JobManager(WORKSPACE)
render_history = RenderHistory(RENDER_HISTORY_FILE)
billing_store = BillingStore(BILLING_TOKENS_FILE, BILLING_AUDIT_FILE)
CLIENT_DIAGNOSTIC_EVENTS = deque(maxlen=400)

if STRIPE_SECRET_KEY:
    stripe.api_key = STRIPE_SECRET_KEY


def _configure_file_logging() -> None:
    APP_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    root_logger = logging.getLogger()
    target_file = str(APP_LOG_FILE.resolve()).lower()

    for handler in root_logger.handlers:
        if isinstance(handler, logging.FileHandler) and str(Path(handler.baseFilename).resolve()).lower() == target_file:
            return

    file_handler = logging.FileHandler(APP_LOG_FILE, encoding="utf-8")
    file_handler.setLevel(os.environ.get("APP_LOG_LEVEL", "INFO").upper())
    file_handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    root_logger.addHandler(file_handler)


def _read_log_tail(line_count: int = 250, max_bytes: int = 512000) -> list[str]:
    if not APP_LOG_FILE.exists():
        return []

    try:
        with APP_LOG_FILE.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            file_size = handle.tell()
            read_size = min(file_size, max_bytes)
            if read_size > 0:
                handle.seek(-read_size, os.SEEK_END)
            chunk = handle.read(read_size)
    except OSError:
        return []

    text = chunk.decode("utf-8", errors="replace")
    return text.splitlines()[-line_count:]


_configure_file_logging()


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


def _count_words(text: str) -> int:
    return len([token for token in text.strip().split() if token])


def _sanitize_user_text(value: str, field_name: str, max_length: int) -> str:
    sanitized = (value or "").replace("\x00", "").strip()
    if not sanitized:
        raise ValueError(f"{field_name} cannot be empty")
    if len(sanitized) > max_length:
        raise ValueError(f"{field_name} must be <= {max_length} characters")
    return sanitized


def _calculate_narration_credit_cost(captions: list[str]) -> tuple[int, int]:
    words = sum(_count_words(caption) for caption in captions)
    billable_words = max(1, words)
    credits = max(1, math.ceil(billable_words / NARRATION_WORDS_PER_CREDIT))
    return words, credits


def _get_voice_options() -> list[dict]:
    if not ELEVENLABS_VOICE_OPTIONS_JSON:
        return DEFAULT_ELEVENLABS_VOICE_OPTIONS

    try:
        parsed = json.loads(ELEVENLABS_VOICE_OPTIONS_JSON)
    except json.JSONDecodeError:
        return DEFAULT_ELEVENLABS_VOICE_OPTIONS

    if not isinstance(parsed, list):
        return DEFAULT_ELEVENLABS_VOICE_OPTIONS

    options: list[dict] = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        voice_id = str(item.get("id") or "").strip()
        label = str(item.get("label") or voice_id).strip()
        if voice_id:
            options.append({"id": voice_id, "label": label})

    return options or DEFAULT_ELEVENLABS_VOICE_OPTIONS


def _get_client_ip() -> str:
    forwarded = (request.headers.get("X-Forwarded-For") or "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip() or "unknown"
    return (request.remote_addr or "unknown").strip()


def _parse_version(version: str) -> tuple[int, ...]:
    cleaned = (version or "").strip().lower().lstrip("v")
    if not cleaned:
        return (0,)

    parts: list[int] = []
    for segment in cleaned.split("."):
        digits = "".join(ch for ch in segment if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts) if parts else (0,)


def _is_newer_version(latest: str, current: str) -> bool:
    latest_parts = list(_parse_version(latest))
    current_parts = list(_parse_version(current))
    length = max(len(latest_parts), len(current_parts))
    latest_parts.extend([0] * (length - len(latest_parts)))
    current_parts.extend([0] * (length - len(current_parts)))
    return tuple(latest_parts) > tuple(current_parts)


def _get_latest_release_payload() -> tuple[dict | None, str | None]:
    latest_url = f"https://api.github.com/repos/{APP_UPDATE_REPO}/releases/latest"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{APP_NAME}/{APP_VERSION}",
    }

    try:
        response = requests.get(latest_url, headers=headers, timeout=8)
    except requests.RequestException as exc:
        return None, f"Update check failed: {str(exc)}"

    if response.status_code != 200:
        return None, f"Update check returned HTTP {response.status_code}"

    payload = response.json() if response.content else {}
    return payload, None


def _pick_release_asset(payload: dict) -> tuple[str, str]:
    selected_url = ""
    selected_name = ""
    for asset in payload.get("assets") or []:
        asset_url = str(asset.get("browser_download_url") or "").strip()
        asset_name = str(asset.get("name") or "").strip()
        if not asset_url:
            continue
        if asset_name.lower().endswith(".exe"):
            return asset_url, asset_name
        if not selected_url:
            selected_url = asset_url
            selected_name = asset_name
    return selected_url, selected_name


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
    if not compare_digest(provided, ADMIN_BILLING_KEY):
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

    if purchase_id and session.get("payment_status") == "paid" and token and credits > 0:
        already_processed, balance = billing_store.apply_purchase_once(
            purchase_id=purchase_id,
            token=token,
            credits=credits,
            source="stripe_checkout",
        )
        if already_processed:
            logger.info("Stripe purchase already processed", extra={"purchase_id": purchase_id})
        else:
            logger.info(
                "Stripe purchase credited",
                extra={"purchase_id": purchase_id, "credits": credits, "balance": balance},
            )
    elif purchase_id and not already_processed:
        is_paid = bool(session.get("payment_status") == "paid")
        if not is_paid:
            billing_store.mark_purchase_processed(purchase_id)
            logger.info("Stripe unpaid session marked processed", extra={"purchase_id": purchase_id})
        else:
            logger.error(
                "Stripe paid session not credited due to invalid metadata",
                extra={"purchase_id": purchase_id, "has_token": bool(token), "credits": credits},
            )

    return token, credits, already_processed


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=str(RESOURCE_ROOT / "templates"),
        static_folder=str(RESOURCE_ROOT / "static"),
    )
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")

    @app.errorhandler(413)
    def too_large(_error):
        return jsonify({"error": f"Upload too large. MAX_UPLOAD_MB is currently {MAX_UPLOAD_MB} MB."}), 413

    @app.get("/")
    def index() -> str:
        return render_template("index.html")

    @app.get("/diagnostics")
    def diagnostics() -> str:
        return render_template("diagnostics.html")

    @app.get("/api/diagnostics/logs")
    def diagnostics_logs():
        try:
            lines = int((request.args.get("lines") or "250").strip())
        except ValueError:
            lines = 250

        lines = max(50, min(lines, 1000))
        return jsonify(
            {
                "ok": True,
                "app_version": APP_VERSION,
                "desktop_shell": os.environ.get("VIDEOFORGE_DESKTOP_SHELL", "") or "browser",
                "log_file": str(APP_LOG_FILE),
                "lines": _read_log_tail(line_count=lines),
            }
        )

    @app.post("/api/diagnostics/client-event")
    def diagnostics_client_event():
        payload = request.get_json(silent=True) or {}
        event = str(payload.get("event") or "unknown").strip()
        component = str(payload.get("component") or "ui").strip()
        details = payload.get("details") if isinstance(payload.get("details"), dict) else {}
        shell = os.environ.get("VIDEOFORGE_DESKTOP_SHELL", "") or "browser"
        event_payload = {
            "ts": datetime.utcnow().isoformat() + "Z",
            "event": event,
            "component": component,
            "shell": shell,
            "details": details,
        }
        CLIENT_DIAGNOSTIC_EVENTS.append(event_payload)
        logger.info("Client diagnostic event | %s", json.dumps(event_payload, ensure_ascii=False, sort_keys=True))
        return jsonify({"ok": True})

    @app.get("/api/diagnostics/client-events")
    def diagnostics_client_events():
        try:
            limit = int((request.args.get("limit") or "80").strip())
        except ValueError:
            limit = 80

        limit = max(10, min(limit, 400))
        events = list(CLIENT_DIAGNOSTIC_EVENTS)[-limit:]
        return jsonify({"ok": True, "count": len(events), "events": events})

    @app.post("/api/render")
    def start_render():
        try:
            title_line_1 = _sanitize_user_text(
                (request.form.get("title_line_1") or "Top 5 Funniest"),
                "title_line_1",
                MAX_TITLE_LENGTH,
            )
            title_line_2 = _sanitize_user_text(
                (request.form.get("title_line_2") or "Moments"),
                "title_line_2",
                MAX_TITLE_LENGTH,
            )
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

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
            try:
                caption_text = _sanitize_user_text(
                    str(captions[index - 1]),
                    f"Caption {index}",
                    MAX_CAPTION_LENGTH,
                )
            except ValueError as exc:
                return jsonify({"error": str(exc)}), 400
            clip_inputs.append(ClipInput(file_path=saved, caption=caption_text))

        narration_word_count, narration_credit_cost = _calculate_narration_credit_cost([clip.caption for clip in clip_inputs])

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
            elevenlabs_api_key=None,
            elevenlabs_voice_id=(request.form.get("elevenlabs_voice_id") or "").strip() or None,
        )

        charged_token = None
        charged_credits = 0
        consumed_free_trial_token = None
        if settings.enable_narration:
            has_server_key = bool(os.environ.get("ELEVENLABS_API_KEY", ""))
            if not (ALLOW_SHARED_ELEVENLABS_KEY and has_server_key):
                return jsonify(
                    {
                        "error": "Narration is currently unavailable because the server-hosted ElevenLabs key is not configured."
                    }
                ), 400

            if REQUIRE_PAYMENT_FOR_SHARED_KEY:
                paid_token = (request.form.get("paid_access_token") or "").strip()
                if not paid_token:
                    return jsonify(
                        {
                            "error": "A paid_access_token is required for narration."
                        }
                    ), 402

                if not is_valid_paid_access_token(paid_token):
                    return jsonify({"error": "Invalid paid_access_token format."}), 400

                consumed, remaining = billing_store.consume_credits(
                    token=paid_token,
                    cost=narration_credit_cost,
                    source="shared_key_narration_words",
                )
                if not consumed:
                    return jsonify(
                        {
                            "error": "Insufficient token credits for narration.",
                            "required_credits": narration_credit_cost,
                            "remaining_credits": remaining,
                            "narration_words": narration_word_count,
                        }
                    ), 402
                charged_token = paid_token
                charged_credits = narration_credit_cost
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
                    credits=charged_credits,
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
        include_music = (request.form.get("include_music") or "").lower() == "true"
        background_music_level_raw = (request.form.get("background_music_level") or "0.15").strip()
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
            background_music_level = float(background_music_level_raw)
        except ValueError:
            return jsonify({"error": "Dimension, font, opacity, and music values must be numeric"}), 400

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
            fps=30,
            include_music=include_music,
            background_music=background_music,
            background_music_level=background_music_level,
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
                "voice_options": _get_voice_options(),
                "default_voice_id": DEFAULT_ELEVENLABS_VOICE_ID,
                "desktop_shell": os.environ.get("VIDEOFORGE_DESKTOP_SHELL", "") or None,
            }
        )

    @app.get("/api/app-update")
    def app_update_status():
        if not APP_UPDATE_ENABLED:
            return jsonify(
                {
                    "enabled": False,
                    "current_version": APP_VERSION,
                    "update_available": False,
                }
            )

        payload, error = _get_latest_release_payload()
        if error:
            return jsonify(
                {
                    "enabled": True,
                    "current_version": APP_VERSION,
                    "update_available": False,
                    "error": error,
                }
            ), 200

        latest_version = str(payload.get("tag_name") or "").strip()
        release_url = str(payload.get("html_url") or "").strip()
        download_url, _download_name = _pick_release_asset(payload)

        update_available = bool(latest_version) and _is_newer_version(latest_version, APP_VERSION)
        return jsonify(
            {
                "enabled": True,
                "repo": APP_UPDATE_REPO,
                "current_version": APP_VERSION,
                "latest_version": latest_version or APP_VERSION,
                "update_available": update_available,
                "release_url": release_url,
                "download_url": download_url,
                "published_at": payload.get("published_at"),
            }
        )

    @app.get("/api/app-update/download")
    def app_update_download():
        if not APP_UPDATE_ENABLED:
            return jsonify({"error": "App updates are disabled on this server."}), 404

        payload, error = _get_latest_release_payload()
        if error:
            return jsonify({"error": error}), 502

        asset_url, asset_name = _pick_release_asset(payload)
        if not asset_url:
            release_url = str(payload.get("html_url") or "").strip()
            return jsonify(
                {
                    "error": "No downloadable assets were found for the latest release.",
                    "release_url": release_url,
                }
            ), 404

        request_headers = {
            "Accept": "application/octet-stream",
            "User-Agent": f"{APP_NAME}/{APP_VERSION}",
        }

        try:
            upstream = requests.get(asset_url, headers=request_headers, stream=True, timeout=(8, 300))
        except requests.RequestException as exc:
            return jsonify({"error": f"Could not start update download: {str(exc)}"}), 502

        if upstream.status_code != 200:
            upstream.close()
            return jsonify({"error": f"Download source returned HTTP {upstream.status_code}"}), 502

        safe_name = secure_filename(asset_name) or "VideoForge-Studio-Update.bin"

        def _iter_chunks():
            try:
                for chunk in upstream.iter_content(chunk_size=262144):
                    if chunk:
                        yield chunk
            finally:
                upstream.close()

        headers = {
            "Content-Disposition": f'attachment; filename="{safe_name}"',
            "Cache-Control": "no-store",
        }
        content_length = upstream.headers.get("Content-Length")
        if content_length:
            headers["Content-Length"] = content_length

        return Response(
            stream_with_context(_iter_chunks()),
            headers=headers,
            content_type=upstream.headers.get("Content-Type", "application/octet-stream"),
        )

    @app.get("/api/voice-preview/<voice_id>")
    def voice_preview(voice_id: str):
        """Serve a pre-generated static voice preview MP3. No API call at runtime."""
        voice_id = secure_filename(voice_id.strip())
        if not voice_id:
            return jsonify({"error": "voice_id is required"}), 400

        preview_dir = RESOURCE_ROOT / "static" / "voice-previews"
        preview_file = preview_dir / f"{voice_id}.mp3"

        if not preview_file.exists():
            return jsonify({"error": "Preview not available for this voice. Run generate_voice_previews.py to create it."}), 404

        return send_from_directory(preview_dir, f"{voice_id}.mp3", mimetype="audio/mpeg")

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
        return send_from_directory(OUTPUTS, safe, as_attachment=False)

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
                "narration_words_per_credit": NARRATION_WORDS_PER_CREDIT,
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
        if credits > MAX_CHECKOUT_CREDITS:
            return jsonify({"error": f"credits must be <= {MAX_CHECKOUT_CREDITS}"}), 400

        unit_amount = STRIPE_PRICE_1_CREDIT_CENTS

        try:
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
        except Exception as exc:
            logger.exception("Stripe checkout session creation failed")
            return jsonify({"error": f"Could not start checkout: {str(exc)}"}), 502

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
        logger.info(
            "Stripe session confirmed",
            extra={"session_id": session_id, "already_processed": already_processed, "credited_credits": credits},
        )
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
            logger.warning("Stripe webhook rejected: invalid payload")
            return jsonify({"error": "Invalid payload"}), 400
        except Exception:
            logger.warning("Stripe webhook rejected: invalid signature or verification error")
            return jsonify({"error": "Invalid signature"}), 400

        if event.get("type") == "checkout.session.completed":
            session = event["data"]["object"]
            token, credits, already_processed = _finalize_paid_checkout_session(session)
            logger.info(
                "Stripe webhook checkout.session.completed processed",
                extra={"already_processed": already_processed, "credited_credits": credits, "has_token": bool(token)},
            )
        else:
            logger.info("Stripe webhook ignored event type", extra={"event_type": str(event.get("type") or "")})

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

    @app.post("/api/renders/save")
    def save_render_to_history():
        """Save a completed render to the user's render history by access code."""
        payload = request.get_json(silent=True) or {}

        def _value(name: str, default: str = "") -> str:
            if name in payload and payload.get(name) is not None:
                return str(payload.get(name)).strip()
            return (request.form.get(name) or default).strip()

        token = _value("token")
        output_filename = _value("output_filename")
        title_line_1 = _value("title_line_1", "Render")
        title_line_2 = _value("title_line_2")
        used_narration_raw = payload.get("used_narration") if "used_narration" in payload else request.form.get("used_narration")
        used_narration = str(used_narration_raw or "").lower() == "true"

        width_raw = payload.get("output_width") if "output_width" in payload else request.form.get("output_width", "1920")
        height_raw = payload.get("output_height") if "output_height" in payload else request.form.get("output_height", "1080")

        try:
            output_width = int(str(width_raw or "1920"))
            output_height = int(str(height_raw or "1080"))
        except (TypeError, ValueError):
            return jsonify({"error": "output_width and output_height must be integers"}), 400

        if not token or not is_valid_paid_access_token(token):
            return jsonify({"error": "valid token is required"}), 400
        if not output_filename:
            return jsonify({"error": "output_filename is required"}), 400

        try:
            render_history.save_render(
                access_code=token,
                output_filename=output_filename,
                title_line_1=title_line_1,
                title_line_2=title_line_2,
                used_narration=used_narration,
                output_width=output_width,
                output_height=output_height,
            )
            return jsonify({"ok": True, "message": "Render saved to history"})
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    @app.get("/api/renders/list")
    def list_user_renders():
        """Retrieve all renders for an access code."""
        token = (request.args.get("token") or "").strip()
        if not token or not is_valid_paid_access_token(token):
            return jsonify({"error": "valid token is required"}), 400

        try:
            renders = render_history.get_renders(token)
            return jsonify({"renders": renders, "count": len(renders)})
        except Exception as exc:
            return jsonify({"error": str(exc)}), 500

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host=APP_HOST, port=APP_PORT, debug=APP_DEBUG)
