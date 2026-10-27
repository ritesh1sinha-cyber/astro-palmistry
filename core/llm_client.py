"""OpenAI-compatible structured LLM client for the facts→prose layer.

Uses the process-wide Settings singleton. Every public call returns None on
failure so callers always fall back to deterministic templates.
"""

from __future__ import annotations

import json
import os
import threading
import time
from typing import Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

from .config import S

T = TypeVar("T", bound=BaseModel)

_client = None
_client_lock = threading.Lock()
_throttle_lock = threading.Lock()
_last_llm_call = 0.0
# Tests inject a stub here; production leaves it None.
_STUB_COMPLETE = None  # type: ignore[var-annotated]


def _throttle() -> None:
    """Space live LLM calls so a 20 RPM endpoint is not burst-overrun."""
    try:
        interval = float(os.environ.get("LLM_MIN_INTERVAL", "0") or 0)
    except (TypeError, ValueError):
        interval = 0.0
    if interval <= 0:
        return
    global _last_llm_call
    with _throttle_lock:
        wait = interval - (time.time() - _last_llm_call)
        if wait > 0:
            print(f"[llm] throttle {wait:.1f}s (LLM_MIN_INTERVAL={interval})",
                  flush=True)
            time.sleep(wait)
        _last_llm_call = time.time()


_LAST_ERROR: dict = {}


def _note_error(stage: str, exc) -> None:
    """Remember why the last model call failed (type + short message, no chart text)."""
    name = exc if isinstance(exc, str) else type(exc).__name__
    msg = "" if isinstance(exc, str) else str(exc)[:240]
    _LAST_ERROR.clear()
    _LAST_ERROR.update({"stage": stage, "error": name, "message": msg,
                        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})


def last_error() -> dict:
    return dict(_LAST_ERROR)


def health() -> dict:
    """One tiny live call, so an operator can see whether the endpoint answers.

    Reports the host (never the key), latency, HTTP-level failure type and the
    last error a real report run recorded.
    """
    from urllib.parse import urlparse
    host = urlparse(S.llm_base_url or "").netloc or "(unset)"
    out = {"enabled": bool(S.llm_enabled), "host": host,
           "scheme": urlparse(S.llm_base_url or "").scheme or "",
           "model": S.llm_model, "timeoutSec": float(S.llm_timeout or 20),
           "hasKey": bool(S.llm_api_key), "lastRunError": last_error()}
    client = _get_client()
    if client is None:
        out.update(ok=False, error="client not configured (key/base_url/openai package)")
        return out
    t0 = time.time()
    try:
        resp = client.chat.completions.create(
            model=S.llm_model or "Qwen/Qwen2.5-7B-Instruct-AWQ",
            messages=[{"role": "user", "content": 'Reply with the JSON {"ok": true}'}],
            max_tokens=20, temperature=0)
        choices = getattr(resp, "choices", None) or []
        text = (getattr(choices[0].message, "content", "") or "").strip() if choices else ""
        out.update(ok=bool(text), ms=int((time.time() - t0) * 1000),
                   reply_chars=len(text),
                   error=None if text else "200 but empty reply")
    except Exception as exc:  # noqa: BLE001
        out.update(ok=False, ms=int((time.time() - t0) * 1000),
                   error=type(exc).__name__, message=str(exc)[:240])
    return out


def set_stub(fn) -> None:
    """Install a test stub: ``fn(schema, system, user, **kw) -> BaseModel|None``."""
    global _STUB_COMPLETE
    _STUB_COMPLETE = fn


def clear_stub() -> None:
    global _STUB_COMPLETE
    _STUB_COMPLETE = None


def _get_client():
    global _client
    if _client is not None:
        return _client
    with _client_lock:
        if _client is not None:
            return _client
        if not S.llm_api_key or not S.llm_base_url:
            return None
        try:
            from openai import OpenAI
        except ImportError:
            print("[llm] openai package not installed", flush=True)
            return None
        _client = OpenAI(
            base_url=S.llm_base_url.rstrip("/"),
            api_key=S.llm_api_key,
            timeout=float(S.llm_timeout or 20),
            max_retries=0,  # we own the retry/repair loop
        )
        return _client


def _schema_payload(schema: Type[BaseModel]) -> dict:
    """JSON Schema for OpenAI response_format / vLLM guided_json."""
    try:
        js = schema.model_json_schema()
    except Exception:
        js = {"type": "object"}
    # Ensure $defs resolve cleanly for strict mode
    return {
        "name": schema.__name__,
        "strict": True,
        "schema": js,
    }


def _parse(schema: Type[T], raw: str) -> Optional[T]:
    text = (raw or "").strip()
    if not text:
        return None
    # Strip common markdown fences
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].lstrip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # salvage the outermost object
        start, end = text.find("{"), text.rfind("}")
        if start < 0 or end <= start:
            _log_parse_failure("no JSON object in reply", schema, text)
            return None
        try:
            data = json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            _log_parse_failure("unparseable JSON", schema, text)
            return None
    try:
        return schema.model_validate(data)
    except ValidationError as ve:
        first = (ve.errors() or [{}])[0]
        where = ".".join(str(x) for x in (first.get("loc") or ()))
        _log_parse_failure(f"schema: {where or '?'} {first.get('msg', '')}",
                           schema, text)
        return None


def _log_parse_failure(why: str, schema: Type[T], text: str) -> None:
    """Say why a reply was thrown away — never what it said.

    Without this the caller only reports "empty_or_model_failure", which reads
    the same for a dead endpoint, a truncated reply and prose that missed the
    schema by one field. The reply itself carries the reader's chart, so only
    its length is logged.
    """
    _note_error("parse", f"unusable: {why}"[:120])
    print(f"[llm] {schema.__name__} unusable ({why}); {len(text)} chars",
          flush=True)


def complete_model(
    schema: Type[T],
    system: str,
    user: str,
    *,
    temperature: float = 0.4,
) -> Optional[T]:
    """Structured call. Returns None on ANY failure — callers fall back.

    Strategy:
      1. response_format json_schema (OpenAI-compatible)
      2. on 400: extra_body guided_json (vLLM)
      3. on invalid JSON: one repair retry with the ValidationError text
    """
    if _STUB_COMPLETE is not None:
        try:
            return _STUB_COMPLETE(schema, system, user, temperature=temperature)
        except Exception as exc:  # noqa: BLE001
            print(f"[llm] stub failed: {type(exc).__name__}: {exc}", flush=True)
            return None

    if not S.llm_enabled:
        return None
    client = _get_client()
    if client is None:
        _note_error("client", "not_configured")
        return None
    _throttle()

    model = S.llm_model or "Qwen/Qwen2.5-7B-Instruct-AWQ"
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    schema_body = _schema_payload(schema)
    raw_text = ""

    def _content(resp) -> str:
        """Text of the first choice, or "" when the server sent none.

        A vLLM endpoint under load can answer 200 with ``choices: null``, and
        indexing that raises inside the repair pass — which then logs as a
        repair failure and hides the real cause.
        """
        choices = getattr(resp, "choices", None) or []
        if not choices:
            return ""
        return (getattr(choices[0].message, "content", "") or "").strip()

    def _create(**kwargs):
        """Create with one sleep-retry on HTTP 429 (endpoint is ~20/min)."""
        limit = int(getattr(S, "llm_max_tokens", 0) or 0)
        if limit > 0:
            kwargs.setdefault("max_tokens", limit)
        try:
            return client.chat.completions.create(**kwargs)
        except Exception as exc:  # noqa: BLE001
            err = str(exc).lower()
            if "429" in err or "rate limit" in err:
                print("[llm] rate-limited — sleeping 35s then retrying once",
                      flush=True)
                time.sleep(35)
                return client.chat.completions.create(**kwargs)
            # A configured ceiling that no longer fits behind this prompt is
            # refused, not truncated. Dropping it lets the endpoint give us
            # whatever the context has left instead of nothing at all.
            if "max" in err and "context" in err and "max_tokens" in kwargs:
                print("[llm] max_tokens does not fit the context — retrying "
                      "without a ceiling", flush=True)
                kwargs.pop("max_tokens", None)
                return client.chat.completions.create(**kwargs)
            raise

    # Pass 1: json_schema response_format
    try:
        resp = _create(
            model=model,
            messages=messages,
            temperature=temperature,
            response_format={
                "type": "json_schema",
                "json_schema": schema_body,
            },
        )
        raw_text = _content(resp)
        parsed = _parse(schema, raw_text)
        if parsed is not None:
            return parsed
    except Exception as exc:  # noqa: BLE001
        err = str(exc).lower()
        _note_error("chat", exc)
        # Pass 2: vLLM guided_json
        if "400" in err or "response_format" in err or "json_schema" in err:
            try:
                resp = _create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    extra_body={"guided_json": schema.model_json_schema()},
                )
                raw_text = _content(resp)
                parsed = _parse(schema, raw_text)
                if parsed is not None:
                    return parsed
            except Exception as exc2:  # noqa: BLE001
                _note_error("guided_json", exc2)
                print(f"[llm] guided_json failed: {type(exc2).__name__}: {exc2}",
                      flush=True)
        else:
            print(f"[llm] chat failed: {type(exc).__name__}: {exc}", flush=True)

    # Pass 3: repair retry
    if raw_text and S.llm_max_retries >= 1:
        try:
            # Diagnose why parse failed
            try:
                schema.model_validate_json(raw_text)
                err_txt = "invalid structure"
            except ValidationError as ve:
                err_txt = str(ve)[:800]
            except Exception:
                err_txt = "not valid JSON"
            repair_messages = messages + [
                {"role": "assistant", "content": raw_text},
                {
                    "role": "user",
                    "content": (
                        "Your previous reply failed schema validation:\n"
                        f"{err_txt}\n"
                        "Reply again with ONLY a JSON object that matches the "
                        "schema. No markdown, no commentary."
                    ),
                },
            ]
            resp = _create(
                model=model,
                messages=repair_messages,
                temperature=0.2,
                extra_body={"guided_json": schema.model_json_schema()},
            )
            repaired = _content(resp)
            return _parse(schema, repaired) if repaired else None
        except Exception as exc:  # noqa: BLE001
            _note_error("repair", exc)
            print(f"[llm] repair failed: {type(exc).__name__}: {exc}", flush=True)

    return None
