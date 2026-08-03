"""Sandbox launcher: applies the py3.9 shim, then serves astro_server."""
import _py39_shim  # noqa: F401  (must precede engine imports)
import uvicorn
if __name__ == "__main__":
    uvicorn.run("astro_server:app", host="127.0.0.1", port=8100, log_level="warning")
