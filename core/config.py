"""Settings. Everything is env-driven so one image runs dev and prod."""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _int(k: str, d: int) -> int:
    try:
        return int(os.getenv(k, d))
    except ValueError:
        return d


def _bool(k: str, d: bool = False) -> bool:
    return os.getenv(k, str(d)).strip().lower() in ("1", "true", "yes", "on")


@dataclass
class Settings:
    env: str = os.getenv("ENV", "dev")

    # --- storage -----------------------------------------------------------
    # Postgres in production; SQLite only for a laptop.
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./astro.db")
    redis_url: str = os.getenv("REDIS_URL", "")           # "" → in-process fake

    # object storage for generated reports (S3 / R2 / MinIO), else local dir
    s3_bucket: str = os.getenv("S3_BUCKET", "")
    s3_endpoint: str = os.getenv("S3_ENDPOINT", "")
    s3_region: str = os.getenv("S3_REGION", "auto")
    local_store: str = os.getenv("LOCAL_STORE", "./storage")

    # --- security ----------------------------------------------------------
    secret: str = os.getenv("APP_SECRET", "dev-only-change-me")
    google_client_id: str = os.getenv("GOOGLE_CLIENT_ID", "")
    dev_login: bool = _bool("DEV_LOGIN", False)
    session_days: int = _int("SESSION_DAYS", 30)
    link_ttl_seconds: int = _int("LINK_TTL_SECONDS", 3600)
    allowed_origins: list = field(default_factory=lambda: [
        o.strip() for o in os.getenv("ALLOWED_ORIGINS", "*").split(",") if o.strip()])

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
        "palm_full":      _int("PRICE_PALM", 49900),
        "full_report":    _int("PRICE_REPORT", 149900),
        "horary":         _int("PRICE_HORARY", 9900),
        "future_event":   _int("PRICE_TIMING", 19900),
        "kundali_match":  _int("PRICE_MATCH", 29900),
        "muhurat":        _int("PRICE_MUHURAT", 4900),
        "btr":            _int("PRICE_BTR", 99900),
        "subscription":   _int("PRICE_SUB", 19900),
        # Everything, one payment. Separately these come to Rs 4,544, so the
        # bundle is priced to be the obvious choice rather than a token
        # discount — and it front-loads the rectification, which every other
        # reading depends on.
        "bundle_all":     _int("PRICE_BUNDLE", 210000),
    })
    free_daily_readings: int = _int("FREE_DAILY", 3)
    sub_horary_per_month: int = _int("SUB_HORARY", 3)

    # --- payments ----------------------------------------------------------
    gateway: str = os.getenv("PAYMENT_GATEWAY", "razorpay")
    razorpay_key_id: str = os.getenv("RAZORPAY_KEY_ID", "")
    razorpay_key_secret: str = os.getenv("RAZORPAY_KEY_SECRET", "")
    razorpay_webhook_secret: str = os.getenv("RAZORPAY_WEBHOOK_SECRET", "")
    upi_id: str = os.getenv("UPI_ID", "")
    payee_name: str = os.getenv("PAYEE_NAME", "Astro Palmistry")

    # --- retention ---------------------------------------------------------
    report_retention_days: int = _int("REPORT_RETENTION_DAYS", 365)
    job_retention_days: int = _int("JOB_RETENTION_DAYS", 90)

    engine_version: str = os.getenv("ENGINE_VERSION", "2026.08")

    def __post_init__(self) -> None:
        # Managed hosts (Railway, Render, Heroku, Neon) hand out URLs starting
        # `postgres://` or `postgresql://`. SQLAlchemy maps those to psycopg2,
        # which is not in our image — psycopg3 is. Normalise it here so nobody
        # has to remember a driver suffix in a dashboard.
        u = self.database_url
        if u.startswith("postgres://"):
            u = "postgresql://" + u[len("postgres://"):]
        if u.startswith("postgresql://"):
            u = "postgresql+psycopg://" + u[len("postgresql://"):]
        self.database_url = u

    @property
    def is_postgres(self) -> bool:
        return self.database_url.startswith("postgres")

    def price(self, item: str) -> int:
        if item not in self.prices:
            raise KeyError(f"unknown item {item!r}")
        return self.prices[item]


S = Settings()
