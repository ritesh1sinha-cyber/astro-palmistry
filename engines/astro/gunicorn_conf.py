import multiprocessing
import os

bind = f"{os.getenv('HOST', '0.0.0.0')}:{os.getenv('PORT', '8000')}"
workers = int(os.getenv("WEB_CONCURRENCY", "4"))
worker_class = "uvicorn.workers.UvicornWorker"
timeout = 60
keepalive = 5
max_requests = 2000
max_requests_jitter = 200

# Recommended for 10k concurrent submissions: WEB_CONCURRENCY=4-8 per VM, scale VMs horizontally
print(f"gunicorn: {workers} workers on {bind}")
