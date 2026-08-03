"""
Gunicorn config for multi-worker Vedic Astrology Report Generator.

Usage:
    gunicorn astro_report_generator:app -c gunicorn_astro.conf.py

Worker count guidance:
    CPU-bound (PyJHora, MiniLM): 1 worker per CPU core
    Recommended starting point : (CPU_cores - 1) workers
    For 10k users with 30s/report: workers = (target_reports_per_min / 2)

Example machines:
    8-core laptop    → 6 workers  → 12 reports/min  → ~720/hour
    32-core cloud VM → 28 workers → 56 reports/min  → ~3,360/hour
    3x 32-core VMs  → 84 workers → 168 reports/min → ~10,000/hour
"""
import multiprocessing
import os

# ── Worker count ─────────────────────────────────────────────────────
# Override with: GUNICORN_WORKERS=8 gunicorn ...
_cpu = multiprocessing.cpu_count()
workers = int(os.getenv("GUNICORN_WORKERS", max(2, _cpu - 1)))

# ── Worker class (uvicorn for ASGI + WebSocket support) ──────────────
worker_class = "uvicorn.workers.UvicornWorker"

# ── Bind ─────────────────────────────────────────────────────────────
bind = f"0.0.0.0:{os.getenv('ASTRO_PORT', '8091')}"

# ── Timeouts (reports take up to 5 min each) ─────────────────────────
timeout         = 360   # worker killed if silent >6 min
graceful_timeout = 60
keepalive       = 5

# ── Logging ──────────────────────────────────────────────────────────
loglevel    = "warning"
accesslog   = "-"
errorlog    = "-"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s %(D)sµs'

# ── Process title ────────────────────────────────────────────────────
proc_name = "astro-report-server"
