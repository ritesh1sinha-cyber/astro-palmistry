"""Settings. Everything is env-driven so one image runs dev and prod.

Local credentials also load from the repo-root `.config` JSON file (guest
passcode, admin username/password, Google Client ID). Environment variables
always win over `.config` when set.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import quote

# Flip to False before public launch (real Google OAuth + live payments).
# Not read from Railway — change here only when testing is complete.
_CODE_DEV_LOGIN = True
# Until Razorpay keys are configured, orders auto-complete so half → pay → full
# can be tested on localhost and on Vercel→Railway (ENV may still be "prod").
# Flip to False before live payments go live.
_CODE_DEV_AUTO_PAY = False


def _int(k: str, d: int) -> int:
    try:
        return int(os.getenv(k, d))
    except ValueError:
        return d


def _bool(k: str, d: bool = False) -> bool:
    return os.getenv(k, str(d)).strip().lower() in ("1", "true", "yes", "on")


def _load_dot_config() -> dict:
    """Read optional `.config` JSON next to the project root /app."""
    candidates = []
    env_path = (os.getenv("AUTH_CONFIG") or "").strip()
    if env_path:
        candidates.append(Path(env_path))
    candidates.append(Path(__file__).resolve().parents[1] / ".config")
    candidates.append(Path("/app/.config"))
    for path in candidates:
        try:
            if path.is_file():
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
        except Exception as exc:                                     # noqa: BLE001
            print(f"[config] could not read {path}: {exc}", flush=True)
    return {}


_CFG = _load_dot_config()


def _cfg(key: str, env: str, default: str = "") -> str:
    """Env overrides `.config`, which overrides the hardcoded default."""
    if env in os.environ and os.environ[env] != "":
        return os.environ[env]
    val = _CFG.get(key)
    if val is None or val == "":
        return default
    return str(val)


def _build_database_url() -> str:
    """Assemble a Postgres URL from the individual PG* variables that managed
    hosts (Railway, Neon, Render) inject, falling back to SQLite."""
    host = os.getenv("PGHOST")
    if not host:
        return "sqlite:///./astro.db"
    user = quote(os.getenv("PGUSER", "postgres"), safe="")
    password = quote(os.getenv("PGPASSWORD", ""), safe="")
    db = quote(os.getenv("PGDATABASE", "postgres"), safe="")
    port = os.getenv("PGPORT", "5432")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"


def _allowed_origins() -> list:
    """CORS origins. Never default to * with credentials — browsers reject it."""
    raw = os.getenv("ALLOWED_ORIGINS", "").strip()
    if raw:
        return [o.strip() for o in raw.split(",") if o.strip()]
    if os.getenv("ENV", "dev") != "prod":
        return [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5500",
            "http://127.0.0.1:5500",
            "http://localhost:8123",
            "http://127.0.0.1:8123",
            "http://localhost:8080",
            "http://127.0.0.1:8080",
        ]
    return [
        "https://www.graharekha.co.in",
        "https://graharekha.co.in",
    ]


@dataclass
class Settings:
    env: str = os.getenv("ENV", "dev")

    # --- storage -----------------------------------------------------------
    # Postgres in production; SQLite only for a laptop.
    database_url: str = os.getenv("DATABASE_URL", "")
    redis_url: str = os.getenv("REDIS_URL", "")           # "" → in-process fake

    # object storage for generated reports (S3 / R2 / MinIO), else local dir
    s3_bucket: str = os.getenv("S3_BUCKET", "")
    s3_endpoint: str = os.getenv("S3_ENDPOINT", "")
    s3_region: str = os.getenv("S3_REGION", "auto")
    local_store: str = os.getenv("LOCAL_STORE", "./storage")

    # --- security ----------------------------------------------------------
    secret: str = os.getenv("APP_SECRET", "dev-only-change-me")
    google_client_id: str = field(default_factory=lambda: _cfg(
        "google_client_id", "GOOGLE_CLIENT_ID", ""))
    # Cloudflare Turnstile (I'm-not-a-robot). Site key is public; secret is
    # server-only. Empty secret = check disabled (local / e2e).
    turnstile_site_key: str = field(default_factory=lambda: _cfg(
        "turnstile_site_key", "TURNSTILE_SITE_KEY", ""))
    turnstile_secret: str = field(default_factory=lambda: _cfg(
        "turnstile_secret", "TURNSTILE_SECRET", ""))
    # Guest / admin test logins (passcode + password). Off when False.
    dev_login: bool = _CODE_DEV_LOGIN
    dev_auto_pay: bool = _CODE_DEV_AUTO_PAY
    guest_passcode: str = field(default_factory=lambda: _cfg(
        "guest_passcode", "GUEST_PASSCODE", "graharekha"))
    admin_username: str = field(default_factory=lambda: _cfg(
        "admin_username", "ADMIN_USERNAME", "graharekha"))
    admin_email: str = field(default_factory=lambda: _cfg(
        "admin_email", "ADMIN_EMAIL", "graharekha@graharekha.local"))
    admin_password: str = field(default_factory=lambda: _cfg(
        "admin_password", "ADMIN_PASSWORD", "graharekha123"))
    session_days: int = _int("SESSION_DAYS", 30)
    link_ttl_seconds: int = _int("LINK_TTL_SECONDS", 3600)
    allowed_origins: list = field(default_factory=lambda: _allowed_origins())

    # --- capacity ----------------------------------------------------------
    # Each worker process handles ONE job at a time (the engines are CPU-bound),
    # so total concurrency == number of worker replicas. Set per-kind caps to
    # stop one slow kind from starving the rest.
    kind_caps: dict = field(default_factory=lambda: {
        "full_report": _int("CAP_FULL_REPORT", 4),
        "btr":         _int("CAP_BTR", 2),
        "palm":        _int("CAP_PALM", 6),
        "*":           _int("CAP_DEFAULT", 12),
    })
    rate_per_min: int = _int("RATE_PER_MIN", 60)
    max_queue_depth: int = _int("MAX_QUEUE_DEPTH", 5000)
    job_ttl_seconds: int = _int("JOB_TTL_SECONDS", 86400)

    # --- pricing (paise) ---------------------------------------------------
    prices: dict = field(default_factory=lambda: {
        # All paid unlocks are ₹298 to match the fixed Razorpay payment button.
        "palm_full":      _int("PRICE_PALM", 29800),
        "full_report":    _int("PRICE_REPORT", 29800),
        "classical_report": _int("PRICE_CLASSICAL_REPORT", 29800),
        "horary":         _int("PRICE_HORARY", 29800),
        "user_question":  _int("PRICE_QUESTION", 29800),
        "future_event":   _int("PRICE_TIMING", 29800),
        "kundali_match":  _int("PRICE_MATCH", 29800),
        "muhurat":        _int("PRICE_MUHURAT", 29800),
        "btr":            _int("PRICE_BTR", 29800),
        "subscription":   _int("PRICE_SUB", 29800),
        "numerology_full": _int("PRICE_NUMEROLOGY", 29800),
        # Full-family / everything package is quote-only — see contact CTA.
        "bundle_all":     _int("PRICE_BUNDLE", 29800),
    })
    sub_horary_per_month: int = _int("SUB_HORARY", 3)

    # --- launch offer ------------------------------------------------------
    # A public promise with a hard number in it. Set PROMO_CODE="" to withdraw
    # the offer without a code change; the cap itself is enforced in the
    # database, not here.
    promo_code: str = os.getenv("PROMO_CODE", "FIRST500")
    promo_item: str = os.getenv("PROMO_ITEM", "bundle_all")
    promo_max: int = _int("PROMO_MAX", 500)

    # --- payments ----------------------------------------------------------
    gateway: str = os.getenv("PAYMENT_GATEWAY", "razorpay")
    razorpay_key_id: str = os.getenv("RAZORPAY_KEY_ID", "")
    razorpay_key_secret: str = os.getenv("RAZORPAY_KEY_SECRET", "")
    razorpay_webhook_secret: str = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
    razorpay_payment_button_id: str = field(default_factory=lambda: _cfg(
        "razorpay_payment_button_id", "RAZORPAY_PAYMENT_BUTTON_ID",
        "pl_TMzAWfueT93HPY"))
    upi_id: str = os.getenv("UPI_ID", "")
    payee_name: str = os.getenv("PAYEE_NAME", "GrahaRekha")

    # --- retention ---------------------------------------------------------
    report_retention_days: int = _int("REPORT_RETENTION_DAYS", 365)
    job_retention_days: int = _int("JOB_RETENTION_DAYS", 90)

    engine_version: str = os.getenv("ENGINE_VERSION", "2026.08")

    # --- LLM prose layer (facts in, prose out; off by default) -------------
    # Keys live in env / `.config` only — never hardcode. Default off so
    # deterministic templates remain the ship path until explicitly enabled.
    llm_enabled: bool = field(default_factory=lambda: _bool("LLM_ENABLED", False))
    llm_base_url: str = field(default_factory=lambda: _cfg(
        "llm_base_url", "LLM_BASE_URL", ""))
    llm_api_key: str = field(default_factory=lambda: _cfg(
        "llm_api_key", "LLM_API_KEY", ""))
    llm_model: str = field(default_factory=lambda: _cfg(
        "llm_model", "LLM_MODEL", "Qwen/Qwen2.5-7B-Instruct-AWQ"))
    llm_timeout: int = field(default_factory=lambda: _int("LLM_TIMEOUT", 20))
    llm_max_retries: int = field(default_factory=lambda: _int("LLM_MAX_RETRIES", 2))
    llm_concurrency: int = field(default_factory=lambda: _int("LLM_CONCURRENCY", 4))
    llm_cache_ttl: int = field(default_factory=lambda: _int("LLM_CACHE_TTL", 86400))
    # 0 leaves the reply length to the endpoint, which caps it at whatever the
    # context has left after the prompt. Setting a ceiling here is only safe
    # when it is known to fit that remainder: a request for more than the
    # model can still hold is refused outright rather than truncated.
    llm_max_tokens: int = field(default_factory=lambda: _int("LLM_MAX_TOKENS", 0))
    # Comma-separated tab kinds that may call the LLM when enabled.
    llm_tabs: str = field(default_factory=lambda: _cfg(
        "llm_tabs", "LLM_TABS",
        "full_report,user_question,horary,palm,chat"))

    def llm_tab_enabled(self, kind: str) -> bool:
        """True when the LLM layer is on and ``kind`` is in the allow-list."""
        if not self.llm_enabled or not self.llm_api_key or not self.llm_base_url:
            return False
        allowed = {t.strip() for t in (self.llm_tabs or "").split(",") if t.strip()}
        return (kind or "").strip() in allowed

    def __post_init__(self) -> None:
        # Managed hosts (Railway, Render, Heroku, Neon) hand out URLs starting
        # `postgres://` or `postgresql://`. SQLAlchemy maps those to psycopg2,
        # which is not in our image — psycopg3 is. Normalise it here so nobody
        # has to remember a driver suffix in a dashboard.
        u = (self.database_url or "").strip()
        if not u or "{{" in u or "}}" in u:
            # Empty, or an unresolved `{{Service.VAR}}` template reference from
            # a managed host whose link never expanded. Treat as unset and
            # rebuild from the individual PG* variables (or fall back to
            # SQLite) instead of crashing create_engine() with a literal
            # `{{Postgres.DATABASE_URL}}`.
            u = _build_database_url()
        if u.startswith("postgres://"):
            u = "postgresql://" + u[len("postgres://"):]
        if u.startswith("postgresql://"):
            u = "postgresql+psycopg://" + u[len("postgresql://"):]
        self.database_url = u

        # Same template-reference problem as DATABASE_URL — Railway shows
        # ${{Redis.REDIS_URL}} literally until a Redis plugin is linked.
        ru = (self.redis_url or "").strip()
        if not ru or "{{" in ru or "}}" in ru:
            self.redis_url = ""

    @property
    def is_postgres(self) -> bool:
        return self.database_url.startswith("postgres")

    def price(self, item: str) -> int:
        if item not in self.prices:
            raise KeyError(f"unknown item {item!r}")
        return self.prices[item]


S = Settings()
