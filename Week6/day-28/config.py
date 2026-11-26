"""
Configuration loader and validator for the Complaint Reply Drafter.

Loads settings from OS environment variables, config.env, and .env (in that
precedence order) and validates every field with plain-English error messages
so non-technical users never see raw Python tracebacks.
"""

from dataclasses import dataclass, field
from datetime import datetime
import json
import os
import re
from typing import Dict, List, Optional


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PLACEHOLDER_VALUES = {
    "",
    "your_gemini_api_key_here",
    "your-gemini-api-key",
    "your_email@example.com",
    "your-business-name",
}

DEFAULT_SAMPLES: List[Dict[str, str]] = [
    {
        "category": "Courier Service",
        "title": "Boda Boda Delay (Westlands to Karen)",
        "text": (
            "Your rider picked up my package in Westlands at 11 AM promising delivery "
            "to Karen by 1 PM. It is now 4:30 PM, the client is leaving the office, "
            "and the rider's phone is switched off! Explain this!"
        ),
    },
    {
        "category": "Restaurant / Food",
        "title": "Cold Nyama Choma & Missing Ugali",
        "text": (
            "I placed an order on WhatsApp for 1kg wet fry nyama choma and ugali an hour "
            "and a half ago. The food just arrived completely cold and the ugali was "
            "missing from the bag! My guests are waiting!"
        ),
    },
    {
        "category": "Airbnb Host",
        "title": "Kilimani Apartment Wi-Fi & Shower Issue",
        "text": (
            "Hi, we checked into the Kilimani apartment 2 hours ago. The Wi-Fi is not "
            "working at all and there is no hot water in the master shower. We have a "
            "video call in 30 minutes. Please fix this immediately."
        ),
    },
    {
        "category": "Retail Boutique",
        "title": "Wrong Dress Size Before Ruracio",
        "text": (
            "I ordered the emerald green linen dress in size M, but you delivered size XL "
            "to my office in Upper Hill, and tomorrow morning is my sister's ruracio. "
            "This is totally unacceptable!"
        ),
    },
]

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
HEX_COLOR_RE = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
PHONE_CHARS_RE = re.compile(r"^[+\d\s().-]+$")


class ConfigError(Exception):
    """Raised when configuration in config.env or environment variables is invalid."""


@dataclass
class AppConfig:
    """Validated runtime configuration for the application."""

    business_name: str = "Our Business"
    manager_name: str = "Customer Care Team"
    business_type: str = "small Kenyan business (shop, courier service, Airbnb, or restaurant)"
    reply_tone: str = "warm, polite, calm, and respectful Kenyan business tone"
    support_email: str = ""
    support_phone: str = ""
    app_title: str = "Customer Complaint Reply Drafter"
    app_subtitle: str = (
        "Paste a customer complaint message below to instantly generate a polite, "
        "professional reply draft."
    )
    copyright_owner: str = "Our Business"
    copyright_year: str = str(datetime.now().year)
    brand_primary_color: str = "#059669"
    brand_accent_color: str = "#25D366"
    gemini_api_key: str = ""
    gemini_models: List[str] = field(
        default_factory=lambda: [
            "gemini-3.5-flash-lite",
            "gemini-3.1-flash-lite",
            "gemini-3.8-flash",
        ]
    )
    gemini_temperature: float = 0.4
    gemini_max_tokens: int = 600
    api_timeout_seconds: float = 12.0
    min_complaint_chars: int = 3
    max_complaint_chars: int = 3000
    samples_file: str = "samples.json"
    samples: List[Dict[str, str]] = field(default_factory=lambda: list(DEFAULT_SAMPLES))
    service_name: str = "nairobi-complaint-reply-tool"
    host: str = "0.0.0.0"
    port: int = 5000
    auto_open_browser: bool = True

    def ui_context(self) -> Dict[str, object]:
        """Return safe, public display fields for HTML templates (never API keys)."""
        return {
            "business_name": self.business_name,
            "manager_name": self.manager_name,
            "support_email": self.support_email,
            "support_phone": self.support_phone,
            "app_title": self.app_title,
            "app_subtitle": self.app_subtitle,
            "copyright_owner": self.copyright_owner,
            "copyright_year": self.copyright_year,
            "brand_primary_color": self.brand_primary_color,
            "brand_accent_color": self.brand_accent_color,
            "max_complaint_chars": self.max_complaint_chars,
        }


def _parse_env_file(path: str) -> Dict[str, str]:
    """Read key=value pairs from an env file without mutating os.environ."""
    values: Dict[str, str] = {}
    if not path or not os.path.isfile(path):
        return values

    try:
        from dotenv import dotenv_values  # type: ignore

        raw = dotenv_values(path)
        for key, val in raw.items():
            if key and val is not None:
                values[key.strip()] = str(val).strip()
        return values
    except ImportError:
        pass
    except OSError as exc:
        raise ConfigError(
            f"Could not read configuration file '{os.path.basename(path)}'. "
            f"Check that it is saved as plain text and not open in another program ({exc})."
        ) from exc

    try:
        with open(path, "r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                values[k.strip()] = v.strip().strip('"').strip("'")
    except OSError as exc:
        raise ConfigError(
            f"Could not read configuration file '{os.path.basename(path)}'. "
            f"Check file permissions and try again ({exc})."
        ) from exc
    return values


def _clean_value(raw: Optional[str]) -> str:
    """Return stripped value or empty string if it is a known template placeholder."""
    if raw is None:
        return ""
    text = str(raw).strip()
    if text.lower() in PLACEHOLDER_VALUES:
        return ""
    return text


def _collect_raw_settings(base_dir: str = BASE_DIR) -> Dict[str, str]:
    """Merge settings: OS environment > config.env > .env."""
    config_file = os.environ.get("CONFIG_FILE", "").strip()
    config_env_path = (
        config_file
        if os.path.isabs(config_file)
        else os.path.join(base_dir, config_file or "config.env")
    )
    dotenv_path = os.path.join(base_dir, ".env")

    merged: Dict[str, str] = {}
    for source in (_parse_env_file(dotenv_path), _parse_env_file(config_env_path)):
        for key, val in source.items():
            cleaned = _clean_value(val)
            if cleaned:
                merged[key] = cleaned

    for key, val in os.environ.items():
        cleaned = _clean_value(val)
        if cleaned:
            merged[key] = cleaned

    return merged


def _parse_int(raw: str, name: str, minimum: int, maximum: int, default: int) -> int:
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(
            f"Invalid {name} setting in config.env ('{raw}'). "
            f"Please enter a whole number between {minimum} and {maximum} (for example, {default})."
        ) from exc
    if value < minimum or value > maximum:
        raise ConfigError(
            f"Invalid {name} setting in config.env ({value}). "
            f"Please choose a number between {minimum} and {maximum}."
        )
    return value


def _parse_float(raw: str, name: str, minimum: float, maximum: float, default: float) -> float:
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError as exc:
        raise ConfigError(
            f"Invalid {name} setting in config.env ('{raw}'). "
            f"Please enter a number between {minimum} and {maximum} (for example, {default})."
        ) from exc
    if value < minimum or value > maximum:
        raise ConfigError(
            f"Invalid {name} setting in config.env ({value}). "
            f"Please choose a number between {minimum} and {maximum}."
        )
    return value


def _parse_bool(raw: str, default: bool) -> bool:
    if not raw:
        return default
    lowered = raw.strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    return default


def _load_samples(samples_file: str, base_dir: str) -> List[Dict[str, str]]:
    if not samples_file:
        return list(DEFAULT_SAMPLES)

    resolved = (
        samples_file
        if os.path.isabs(samples_file)
        else os.path.join(base_dir, samples_file)
    )
    if not os.path.isfile(resolved):
        raise ConfigError(
            f"Could not find your samples file ('{samples_file}'). "
            f"Check that SAMPLES_FILE in config.env points to an existing file, "
            f"or leave SAMPLES_FILE blank to use built-in examples."
        )

    try:
        with open(resolved, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ConfigError(
            f"Your samples file ('{samples_file}') is not valid JSON (line {exc.lineno}). "
            f"Fix the formatting or leave SAMPLES_FILE blank in config.env."
        ) from exc
    except OSError as exc:
        raise ConfigError(
            f"Could not open your samples file ('{samples_file}'): {exc}"
        ) from exc

    if not isinstance(data, list):
        raise ConfigError(
            f"Your samples file ('{samples_file}') must contain a JSON list of sample complaints."
        )
    return data


def load_and_validate_config(base_dir: str = BASE_DIR) -> AppConfig:
    """Load settings from config.env / .env / environment and validate every field."""
    settings = _collect_raw_settings(base_dir)

    business_name = settings.get("BUSINESS_NAME", "Our Business")
    manager_name = settings.get("MANAGER_NAME", "Customer Care Team")
    business_type = settings.get(
        "BUSINESS_TYPE",
        "small Kenyan business (shop, courier service, Airbnb, or restaurant)",
    )
    reply_tone = settings.get(
        "REPLY_TONE",
        "warm, polite, calm, and respectful Kenyan business tone",
    )

    support_email = settings.get("SUPPORT_EMAIL", "")
    if support_email and not EMAIL_RE.match(support_email):
        raise ConfigError(
            f"The SUPPORT_EMAIL in config.env ('{support_email}') does not look like a valid email address. "
            f"Please enter an email like support@yourbusiness.co.ke or leave it blank."
        )

    support_phone = settings.get("SUPPORT_PHONE", "")
    if support_phone:
        digits_only = re.sub(r"\D", "", support_phone)
        if not PHONE_CHARS_RE.match(support_phone) or len(digits_only) < 7:
            raise ConfigError(
                f"The SUPPORT_PHONE in config.env ('{support_phone}') does not look like a valid phone number. "
                f"Use a number like +254 700 123 456 or leave it blank."
            )

    brand_primary = settings.get("BRAND_PRIMARY_COLOR", "#059669")
    if not HEX_COLOR_RE.match(brand_primary):
        raise ConfigError(
            f"Invalid BRAND_PRIMARY_COLOR in config.env ('{brand_primary}'). "
            f"Please use a hex color code like #059669."
        )

    brand_accent = settings.get("BRAND_ACCENT_COLOR", "#25D366")
    if not HEX_COLOR_RE.match(brand_accent):
        raise ConfigError(
            f"Invalid BRAND_ACCENT_COLOR in config.env ('{brand_accent}'). "
            f"Please use a hex color code like #25D366."
        )

    models_raw = settings.get(
        "GEMINI_MODELS",
        "gemini-3.5-flash-lite,gemini-3.1-flash-lite,gemini-3.8-flash",
    )
    gemini_models = [m.strip() for m in models_raw.split(",") if m.strip()]
    if not gemini_models:
        raise ConfigError(
            "GEMINI_MODELS in config.env cannot be empty. "
            "Use the default: gemini-3.5-flash-lite,gemini-3.1-flash-lite,gemini-3.8-flash."
        )

    port = _parse_int(settings.get("PORT", ""), "PORT", 1, 65535, 5000)
    min_chars = _parse_int(
        settings.get("MIN_COMPLAINT_CHARS", ""), "MIN_COMPLAINT_CHARS", 1, 500, 3
    )
    max_chars = _parse_int(
        settings.get("MAX_COMPLAINT_CHARS", ""), "MAX_COMPLAINT_CHARS", 100, 20000, 3000
    )
    if min_chars >= max_chars:
        raise ConfigError(
            "MIN_COMPLAINT_CHARS must be smaller than MAX_COMPLAINT_CHARS in config.env."
        )

    gemini_max_tokens = _parse_int(
        settings.get("GEMINI_MAX_TOKENS", ""), "GEMINI_MAX_TOKENS", 50, 4096, 600
    )
    gemini_temperature = _parse_float(
        settings.get("GEMINI_TEMPERATURE", ""), "GEMINI_TEMPERATURE", 0.0, 2.0, 0.4
    )
    api_timeout = _parse_float(
        settings.get("API_TIMEOUT_SECONDS", ""), "API_TIMEOUT_SECONDS", 1.0, 60.0, 12.0
    )

    samples_file = settings.get("SAMPLES_FILE", "")
    if not samples_file and os.path.isfile(os.path.join(base_dir, "samples.json")):
        samples_file = "samples.json"
    samples = _load_samples(samples_file, base_dir)

    copyright_owner = settings.get("COPYRIGHT_OWNER", "") or business_name
    copyright_year = settings.get("COPYRIGHT_YEAR", "") or str(datetime.now().year)

    return AppConfig(
        business_name=business_name,
        manager_name=manager_name,
        business_type=business_type,
        reply_tone=reply_tone,
        support_email=support_email,
        support_phone=support_phone,
        app_title=settings.get("APP_TITLE", "Customer Complaint Reply Drafter"),
        app_subtitle=settings.get(
            "APP_SUBTITLE",
            "Paste a customer complaint message below to instantly generate a polite, professional reply draft.",
        ),
        copyright_owner=copyright_owner,
        copyright_year=copyright_year,
        brand_primary_color=brand_primary,
        brand_accent_color=brand_accent,
        gemini_api_key=settings.get("GEMINI_API_KEY", ""),
        gemini_models=gemini_models,
        gemini_temperature=gemini_temperature,
        gemini_max_tokens=gemini_max_tokens,
        api_timeout_seconds=api_timeout,
        min_complaint_chars=min_chars,
        max_complaint_chars=max_chars,
        samples_file=samples_file,
        samples=samples,
        service_name=settings.get("SERVICE_NAME", "nairobi-complaint-reply-tool"),
        host=settings.get("HOST", "0.0.0.0"),
        port=port,
        auto_open_browser=_parse_bool(settings.get("AUTO_OPEN_BROWSER", ""), True),
    )
