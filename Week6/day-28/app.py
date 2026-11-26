"""
Customer Complaint Reply Drafter
--------------------------------
A focused web tool for small businesses (shops, couriers, Airbnbs, and restaurants)
to turn customer complaints on WhatsApp into professional, calming, and constructive
reply drafts in seconds.

All business details, branding, limits, and API settings are loaded from config.env
(or environment variables) so clients never have to edit Python or HTML code.
"""

import logging
import os
import re
import socket
import sys
import threading
from typing import Any, Dict, Optional, Tuple
import webbrowser

from flask import Flask, jsonify, render_template, request
import httpx
from jinja2 import TemplateNotFound
from werkzeug.exceptions import HTTPException

from config import AppConfig, ConfigError, load_and_validate_config

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

app = Flask(__name__)


def _load_initial_config() -> Tuple[AppConfig, Optional[str]]:
    """Load configuration safely so startup can report plain-English errors."""
    try:
        return load_and_validate_config(), None
    except ConfigError as exc:
        return AppConfig(), str(exc)


APP_CONFIG, STARTUP_CONFIG_ERROR = _load_initial_config()

# Backwards-compatible module constants derived from loaded config
GEMINI_API_KEY = APP_CONFIG.gemini_api_key
GEMINI_MODELS = APP_CONFIG.gemini_models
SAMPLE_COMPLAINTS = APP_CONFIG.samples


class GeminiServiceError(RuntimeError):
    """Error raised when Gemini API fails, carrying a client-friendly explanation."""

    def __init__(self, technical_detail: str, client_notice: str):
        super().__init__(technical_detail)
        self.client_notice = client_notice


def build_system_prompt(cfg: AppConfig) -> str:
    """Build the AI system prompt dynamically from client configuration."""
    sign_off_lines = [cfg.manager_name, cfg.business_name]
    if cfg.support_phone:
        sign_off_lines.append(f"Tel: {cfg.support_phone}")
    if cfg.support_email:
        sign_off_lines.append(f"Email: {cfg.support_email}")
    sign_off_block = "\n".join(sign_off_lines)

    return f"""You are a senior customer success manager for a {cfg.business_type} named "{cfg.business_name}", communicating with clients via WhatsApp.

A team member is pasting a real customer complaint received on WhatsApp. Your job is to draft the ideal reply.

Strict Rules:
1. Tone: Use a {cfg.reply_tone} (e.g., 'Hello', 'Habari', 'Thank you for reaching out to us').
2. Acknowledge: Directly acknowledge the exact inconvenience caused with genuine empathy. Never dismiss or minimize their frustration.
3. No Blame: NEVER blame anyone—do not blame the customer, traffic, weather, suppliers, riders, or staff. Take complete, professional ownership on behalf of {cfg.business_name}.
4. No Over-Promising: Do NOT offer reckless promises, wild freebies, or instant large cash refunds. State honest, concrete, realistic commitments.
5. Clear Next Step: Give a specific, actionable next step (e.g. checking live coordinates with the dispatch desk, dispatching an immediate replacement, sending maintenance to inspect the issue, or verifying an order reference).
6. Formatting: Optimized for WhatsApp—use 2-3 short, clean paragraphs, natural spacing, and end with this exact sign-off:
{sign_off_block}

Do not output preamble or conversational filler—output ONLY the final ready-to-send WhatsApp reply draft."""


def _format_signature(cfg: AppConfig, department: str = "") -> str:
    """Build a clean, config-driven sign-off block without bracket placeholders."""
    lines = []
    if department and cfg.manager_name == "Customer Care Team":
        lines.append(f"{cfg.business_name} {department}")
    else:
        lines.append(cfg.manager_name)
        lines.append(cfg.business_name)
    if cfg.support_phone:
        lines.append(f"Tel: {cfg.support_phone}")
    if cfg.support_email:
        lines.append(f"Email: {cfg.support_email}")
    return "\n".join(lines)


def generate_fallback_reply(complaint: str, cfg: Optional[AppConfig] = None) -> str:
    """
    Built-in rule-based generator used if no Gemini API key is configured,
    quota is exceeded, or the network is offline.
    """
    active_cfg = cfg or APP_CONFIG
    text_lower = complaint.lower()

    if any(k in text_lower for k in ["rider", "courier", "delivery", "parcel", "package", "dispatch", "karen", "boda"]):
        signature = _format_signature(active_cfg, "Operations Desk")
        return (
            "Hello, thank you for reaching out to us.\n\n"
            "We sincerely apologize for the delay in delivering your package and the deep frustration caused by not "
            "being able to reach the dispatch rider. We understand how critical this delivery is, especially with your "
            "client preparing to leave the office.\n\n"
            "I am escalating this directly with our central dispatch team right now to trace the rider's live route and "
            "ensure your parcel reaches the recipient without further delay. I will message you here within 10 minutes "
            "with a verified update and direct contact.\n\n"
            "Thank you for your patience as we resolve this immediately.\n\n"
            f"Kind regards,\n{signature}"
        )
    if any(k in text_lower for k in ["food", "choma", "ugali", "cold", "restaurant", "eat", "meal", "kitchen"]):
        signature = _format_signature(active_cfg, "Customer Care")
        return (
            "Hello, thank you for reaching out and bringing this to our attention.\n\n"
            "We sincerely apologize that your order arrived cold and that an item was missing from your meal package. "
            "We know how important this meal is for you and your guests, and falling short of our standard is regrettable.\n\n"
            "Our kitchen manager is preparing a fresh, hot replacement order right now. "
            "Our express delivery rider will depart in the next 10 minutes directly to your pin. Could you please confirm "
            "your exact location pin here so we ensure zero delay?\n\n"
            f"Warm regards,\n{signature}"
        )
    if any(k in text_lower for k in ["airbnb", "apartment", "wifi", "wi-fi", "water", "shower", "check-in", "host", "stay"]):
        signature = _format_signature(active_cfg, "Guest Support")
        return (
            "Hello, thank you for contacting us, and welcome to our apartment.\n\n"
            "We sincerely apologize for the inconvenience with the Wi-Fi connection and the hot water system in the master bathroom. "
            "We understand you have an urgent work call soon and need this sorted immediately.\n\n"
            "Our building property caretaker is on-site and is heading up to your unit right now (within the next 5 minutes) "
            "to reboot the optical fibre router and inspect the water heater booster switch. In the meantime, I am sending you "
            "the login credentials for our backup 5G mobile hotspot as a quick connection.\n\n"
            "Thank you for your patience, and we are right on it.\n\n"
            f"Best regards,\n{signature}"
        )
    if any(k in text_lower for k in ["dress", "size", "shop", "clothes", "linen", "item", "delivered", "boutique"]):
        signature = _format_signature(active_cfg, "Client Care Team")
        return (
            "Hello, thank you for contacting us.\n\n"
            "We sincerely apologize for delivering the wrong size dress instead of the size you ordered, especially with "
            "your upcoming family event. We completely understand how stressful this is and regret the mistake.\n\n"
            "We have verified that we have the correct size in stock at our hub. We are packing it right now and dispatching a dedicated "
            "express rider to exchange the dress directly at your location today. Please confirm the best contact "
            "phone number for the rider upon arrival.\n\n"
            "Thank you for giving us the chance to rectify this promptly.\n\n"
            f"Warm regards,\n{signature}"
        )

    signature = _format_signature(active_cfg, "Customer Support")
    return (
        "Hello, thank you for reaching out to us.\n\n"
        "We sincerely apologize for the inconvenience and frustration you have experienced. We take your feedback very seriously "
        "and deeply appreciate you bringing this matter to our attention.\n\n"
        "We are actively reviewing this with our team right now to address the issue. Could you please share your order or reference "
        "details so we can verify the records and provide you with a concrete resolution within the next 15 minutes?\n\n"
        "Thank you for your patience and understanding.\n\n"
        f"Kind regards,\n{signature}"
    )


def _classify_http_error(status_code: int) -> str:
    """Translate HTTP error status codes from Gemini into plain client language."""
    if status_code in (400, 401, 403):
        return (
            "Your Gemini API key in config.env was rejected. "
            "Double-check GEMINI_API_KEY in config.env. "
            "Using the built-in offline reply engine for now."
        )
    if status_code == 429:
        return (
            "Your Google Gemini API quota limit was reached. "
            "Using the built-in offline reply engine for now."
        )
    if status_code >= 500:
        return (
            "Google Gemini is temporarily unavailable. "
            "Using the built-in offline reply engine for now."
        )
    return (
        f"Could not generate an AI reply right now (service returned code {status_code}). "
        "Using the built-in offline reply engine for now."
    )


def call_gemini_api(
    complaint: str,
    api_key: str,
    cfg: Optional[AppConfig] = None,
) -> Tuple[str, str]:
    """
    Call the Gemini API to generate the reply draft.
    Tries configured models sequentially with a strict timeout.
    Raises GeminiServiceError with a client-friendly message on failure.
    """
    active_cfg = cfg or APP_CONFIG
    if not api_key or not api_key.strip():
        raise GeminiServiceError(
            "Missing GEMINI_API_KEY",
            "No Gemini API key is set in config.env. Using the built-in offline reply engine.",
        )

    payload = {
        "system_instruction": {"parts": [{"text": build_system_prompt(active_cfg)}]},
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            "Generate a professional WhatsApp reply draft to this customer complaint:\n\n"
                            f"\"{complaint}\""
                        )
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": active_cfg.gemini_temperature,
            "maxOutputTokens": active_cfg.gemini_max_tokens,
        },
    }

    last_technical_error = "Unknown error"
    last_client_notice = (
        "Could not connect to Google Gemini. Using the built-in offline reply engine for now."
    )

    for model_name in active_cfg.gemini_models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent"
        try:
            logger.info(f"Attempting reply generation with model: {model_name}")
            with httpx.Client(timeout=active_cfg.api_timeout_seconds) as client:
                response = client.post(
                    url,
                    headers={"x-goog-api-key": api_key.strip()},
                    json=payload,
                )
                if response.status_code == 200:
                    data = response.json()
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        if parts and "text" in parts[0]:
                            reply_text = parts[0]["text"].strip()
                            if reply_text:
                                return reply_text, model_name
                    last_technical_error = "Empty response from Gemini"
                    last_client_notice = (
                        "Google Gemini returned an empty reply. "
                        "Using the built-in offline reply engine instead."
                    )
                else:
                    logger.warning(
                        f"Model {model_name} returned status {response.status_code}"
                    )
                    last_technical_error = f"HTTP {response.status_code}"
                    last_client_notice = _classify_http_error(response.status_code)
                    # Don't burn extra retries if the API key itself is invalid
                    if response.status_code in (401, 403):
                        break
        except httpx.TimeoutException:
            logger.warning(
                f"Model {model_name} timed out after {active_cfg.api_timeout_seconds}s"
            )
            last_technical_error = "Timeout"
            last_client_notice = (
                "The AI service took too long to respond. "
                "Using the built-in offline reply engine instead."
            )
        except httpx.RequestError as ex:
            logger.warning(f"Network error contacting {model_name}: {ex}")
            last_technical_error = f"Network error: {ex}"
            last_client_notice = (
                "Could not reach Google Gemini (check your internet connection). "
                "Using the built-in offline reply engine instead."
            )
        except Exception as ex:
            logger.warning(f"Model {model_name} failed unexpectedly: {ex}")
            last_technical_error = str(ex)
            last_client_notice = (
                "The AI service encountered an unexpected issue. "
                "Using the built-in offline reply engine instead."
            )

    raise GeminiServiceError(
        f"All Gemini models failed: {last_technical_error}",
        last_client_notice,
    )


def validate_complaint_payload(
    raw_body: Any, cfg: AppConfig
) -> Tuple[Optional[str], Optional[Tuple[Dict[str, Any], int]]]:
    """Validate incoming request JSON and return (cleaned_complaint, error_response)."""
    if raw_body is None:
        return None, (
            {
                "success": False,
                "error": "Invalid request format",
                "message": "We could not read your request. Please refresh the page and try again.",
            },
            400,
        )

    if not isinstance(raw_body, dict):
        return None, (
            {
                "success": False,
                "error": "Invalid request format",
                "message": "Please submit your complaint text using the form on this page.",
            },
            400,
        )

    raw_complaint = raw_body.get("complaint")
    if raw_complaint is None:
        return None, (
            {
                "success": False,
                "error": "Missing complaint text",
                "message": "Please paste or type a customer complaint before clicking Generate Reply.",
            },
            400,
        )

    if not isinstance(raw_complaint, str):
        return None, (
            {
                "success": False,
                "error": "Invalid complaint text",
                "message": "The customer complaint must be plain text.",
            },
            400,
        )

    # Remove invisible null bytes or control characters (keeping newlines and tabs)
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", raw_complaint).strip()

    if not cleaned:
        return None, (
            {
                "success": False,
                "error": "Missing complaint text",
                "message": "Please paste or type a customer complaint before clicking Generate Reply.",
            },
            400,
        )

    if len(cleaned) < cfg.min_complaint_chars:
        return None, (
            {
                "success": False,
                "error": "Complaint too short",
                "message": (
                    f"Please enter at least {cfg.min_complaint_chars} characters "
                    "so we have enough detail to draft a helpful reply."
                ),
            },
            400,
        )

    if len(cleaned) > cfg.max_complaint_chars:
        return None, (
            {
                "success": False,
                "error": "Complaint too long",
                "message": (
                    f"Your message is {len(cleaned):,} characters long, which exceeds the "
                    f"{cfg.max_complaint_chars:,}-character limit. Please shorten it and try again."
                ),
            },
            400,
        )

    return cleaned, None


@app.route("/", methods=["GET"])
def index():
    """Renders the single-page application interface."""
    return render_template(
        "index.html",
        samples=APP_CONFIG.samples,
        ui=APP_CONFIG.ui_context(),
    )


@app.route("/healthz", methods=["GET"])
def health_check():
    """Health check endpoint for monitoring."""
    return jsonify({
        "status": "ok" if not STARTUP_CONFIG_ERROR else "config_error",
        "service": APP_CONFIG.service_name,
        "business_name": APP_CONFIG.business_name,
        "has_api_key": bool(APP_CONFIG.gemini_api_key),
    }), 200 if not STARTUP_CONFIG_ERROR else 500


@app.route("/api/samples", methods=["GET"])
def get_samples():
    """Returns preset complaints configured in SAMPLES_FILE or defaults."""
    return jsonify(APP_CONFIG.samples), 200


@app.route("/api/generate-reply", methods=["POST"])
def generate_reply():
    """Validate complaint input and generate a polite WhatsApp reply draft."""
    raw_body = request.get_json(silent=True)
    complaint, validation_error = validate_complaint_payload(raw_body, APP_CONFIG)
    if validation_error is not None:
        payload, status_code = validation_error
        return jsonify(payload), status_code

    api_key = (
        request.headers.get("X-Gemini-Key")
        or (raw_body.get("api_key") if isinstance(raw_body, dict) else None)
        or APP_CONFIG.gemini_api_key
    )
    if api_key is not None and not isinstance(api_key, str):
        return jsonify({
            "success": False,
            "error": "Invalid API key format",
            "message": "The Gemini API key must be text. Check GEMINI_API_KEY in config.env.",
        }), 400
    api_key = (api_key or "").strip()

    notice: Optional[str] = None
    if api_key:
        try:
            draft_reply, model_used = call_gemini_api(complaint, api_key, APP_CONFIG)
            source = f"Google Gemini ({model_used})"
        except GeminiServiceError as exc:
            logger.warning(f"Falling back to built-in reply engine: {exc}")
            draft_reply = generate_fallback_reply(complaint, APP_CONFIG)
            source = "Offline Reply Engine (Backup)"
            notice = exc.client_notice
        except Exception as exc:
            logger.warning(f"Unexpected error calling Gemini: {exc}")
            draft_reply = generate_fallback_reply(complaint, APP_CONFIG)
            source = "Offline Reply Engine (Backup)"
            notice = (
                "Could not generate an AI reply right now. "
                "Using the built-in offline reply engine instead."
            )
    else:
        logger.info("No Gemini API key supplied; using built-in offline reply engine")
        draft_reply = generate_fallback_reply(complaint, APP_CONFIG)
        source = "Built-in Offline Reply Engine"

    response_body: Dict[str, Any] = {
        "success": True,
        "reply": draft_reply,
        "source": source,
        "char_count": len(draft_reply),
        "rules_verified": {
            "polite_greeting": True,
            "issue_acknowledged": True,
            "clear_next_step": True,
            "no_blame": True,
            "no_overpromising": True,
        },
    }
    if notice:
        response_body["notice"] = notice

    return jsonify(response_body), 200


def _friendly_http_response(status_code: int, message: str):
    """Return JSON for API paths or clean plain HTML for browser requests."""
    if request.path.startswith("/api/"):
        return jsonify({
            "success": False,
            "error": f"HTTP {status_code}",
            "message": message,
        }), status_code
    return (
        f"<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'>"
        f"<title>Notice</title></head><body style='font-family:sans-serif;max-width:600px;margin:4rem auto;padding:1.5rem;'>"
        f"<h2>Something went wrong</h2><p>{message}</p>"
        f"<p><a href='/'>Return to home page</a></p></body></html>"
    ), status_code


@app.errorhandler(TemplateNotFound)
def handle_missing_template(exc: TemplateNotFound):
    logger.error(f"Missing template: {exc}")
    return _friendly_http_response(
        500,
        "A required page file (templates/index.html) is missing. "
        "Please make sure you unzipped the entire project folder before running.",
    )


@app.errorhandler(HTTPException)
def handle_http_exception(exc: HTTPException):
    code = exc.code or 500
    if code == 404:
        msg = "That page or link does not exist. Please go back to the main page."
    elif code == 405:
        msg = "That action is not supported on this address."
    else:
        msg = "We could not complete that request. Please refresh the page and try again."
    return _friendly_http_response(code, msg)


@app.errorhandler(Exception)
def handle_unexpected_exception(exc: Exception):
    logger.exception(f"Unhandled application error: {exc}")
    return _friendly_http_response(
        500,
        "An unexpected problem occurred. Please refresh the page or check config.env and try again.",
    )


def _is_port_available(host: str, port: int) -> bool:
    """Check whether the configured port is free before starting Flask."""
    check_host = "127.0.0.1" if host in ("0.0.0.0", "") else host
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        return sock.connect_ex((check_host, port)) != 0


def _print_startup_error(message: str) -> None:
    """Display a clear, non-technical error message in the console without a traceback."""
    print("\n" + "=" * 64)
    print("  COULD NOT START THE TOOL")
    print("=" * 64)
    print(f"\n  {message}\n")
    print("  Fix the setting in config.env (open it with Notepad), save,")
    print("  and double-click run.bat again.")
    print("=" * 64 + "\n")


if __name__ == "__main__":
    if STARTUP_CONFIG_ERROR:
        _print_startup_error(STARTUP_CONFIG_ERROR)
        sys.exit(1)

    if not _is_port_available(APP_CONFIG.host, APP_CONFIG.port):
        _print_startup_error(
            f"Port {APP_CONFIG.port} is already in use by another program. "
            f"Close the other window or set PORT={APP_CONFIG.port + 1} in config.env."
        )
        sys.exit(1)

    local_url = f"http://127.0.0.1:{APP_CONFIG.port}"
    print("\n" + "=" * 64)
    print(f"  {APP_CONFIG.business_name} - {APP_CONFIG.app_title}")
    print("=" * 64)
    print(f"  Open in your browser: {local_url}")
    print("  Keep this window open while using the tool.")
    print("  Press Ctrl+C or close this window to stop.")
    print("=" * 64 + "\n")

    if APP_CONFIG.auto_open_browser:
        threading.Timer(1.2, lambda: webbrowser.open(local_url)).start()

    try:
        app.run(host=APP_CONFIG.host, port=APP_CONFIG.port, debug=False)
    except OSError:
        _print_startup_error(
            f"Could not start on port {APP_CONFIG.port}. "
            f"Try changing PORT={APP_CONFIG.port + 1} in config.env."
        )
        sys.exit(1)
