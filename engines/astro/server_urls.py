"""Resolve server URLs for LAN, local, and universal (public) access."""
from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.request
from typing import Any, Dict, Optional


def _ngrok_enabled() -> bool:
    flag = os.getenv("ASTRO_USE_NGROK", "").strip().lower()
    return flag in ("1", "true", "yes", "on")


def fetch_ngrok_public_url(timeout: float = 1.0) -> Optional[str]:
    """Read HTTPS URL from a local ngrok agent (default API: http://127.0.0.1:4040)."""
    api = os.getenv("NGROK_API_URL", "http://127.0.0.1:4040/api/tunnels").strip()
    try:
        with urllib.request.urlopen(api, timeout=timeout) as resp:
            data = json.loads(resp.read().decode())
        for tunnel in data.get("tunnels", []):
            url = str(tunnel.get("public_url", "")).strip().rstrip("/")
            if url.startswith("https://"):
                return url
        for tunnel in data.get("tunnels", []):
            url = str(tunnel.get("public_url", "")).strip().rstrip("/")
            if url.startswith("http://"):
                return url
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError, ValueError):
        pass
    return None


def detect_lan_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"


def get_server_urls(port: Optional[int] = None) -> Dict[str, Any]:
    """Return reachable server URLs.

    Public / mobile-data access:
      - ASTRO_PUBLIC_URL=https://your-domain.com  (fixed URL)
      - ASTRO_USE_NGROK=1 + `ngrok http <port>`   (auto-detect from ngrok API)
    """
    port = port or int(os.getenv("ASTRO_PORT", "8091"))
    public = os.getenv("ASTRO_PUBLIC_URL", "").strip().rstrip("/")
    ngrok_url: Optional[str] = None
    if not public and _ngrok_enabled():
        ngrok_url = fetch_ngrok_public_url()
        public = ngrok_url or ""

    lan = detect_lan_ip()
    local = f"http://localhost:{port}"
    lan_url = f"http://{lan}:{port}"

    recommended = public or lan_url
    return {
        "local": local,
        "lan": lan_url,
        "public": public or None,
        "ngrok": ngrok_url,
        "recommended": recommended,
        "universal": bool(public),
        "port": port,
    }
