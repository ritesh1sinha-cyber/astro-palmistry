"""
Entry point — runs the Vedic Astrology Report Generator.
Usage:  python run.py
        uvicorn astro_report_generator:app --host 0.0.0.0 --port 8091
"""
import os
import uvicorn

from server_urls import get_server_urls

PORT = int(os.getenv("ASTRO_PORT", "8091"))

if __name__ == "__main__":
    urls = get_server_urls(PORT)
    print(f"\n{'='*60}")
    print(f"  Vedic Astrology Report Generator")
    print(f"  Local  :  {urls['local']}")
    print(f"  Network:  {urls['lan']}")
    if urls.get("public"):
        print(f"  Universal (Wi-Fi + mobile data):  {urls['public']}")
        print(f"  Android APK server URL:  {urls['public']}")
    else:
        print(f"  Android (same Wi-Fi only):  {urls['lan']}")
        print(f"  For mobile data: ASTRO_PUBLIC_URL=... or ./scripts/run_with_ngrok.sh")
    print(f"{'='*60}\n")

    uvicorn.run(
        "astro_report_generator:app",
        host="0.0.0.0",
        port=PORT,
        log_level="warning",
        reload=False,
    )
