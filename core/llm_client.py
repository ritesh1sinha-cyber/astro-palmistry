"""OpenAI-compatible structured LLM client for the facts→prose layer.

Uses the process-wide Settings singleton. Every public call returns None on
failure so callers always fall back to deterministic templates.
"""

from __future__ import annotations

import json
import threading
import time
from typing import Optional, Type, TypeVar

from pydantic import BaseModel, ValidationError

from .config import S

T = TypeVar("T", bound=BaseModel)

_client = None
_client_lock = threading.Lock()
# Tests inject a stub here; production leaves it None.
_STUB_COMPLETE = None  # type: ignore[var-annotated]


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
            return None
        try:
            data = json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return None
    try:
        return schema.model_validate(data)
    except ValidationError:
        return None


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
        return None

    model = S.llm_model or "Qwen/Qwen2.5-7B-Instruct-AWQ"
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    schema_body = _schema_payload(schema)
    raw_text = ""

    def _create(**kwargs):
        """Create with one sleep-retry on HTTP 429 (endpoint is ~20/min)."""
        try:
            return client.chat.completions.create(**kwargs)
        except Exception as exc:  # noqa: BLE001
            err = str(exc).lower()
            if "429" in err or "rate limit" in err:
                print("[llm] rate-limited — sleeping 35s then retrying once",
                      flush=True)
                time.sleep(35)
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
        raw_text = (resp.choices[0].message.content or "").strip()
        parsed = _parse(schema, raw_text)
        if parsed is not None:
            return parsed
    except Exception as exc:  # noqa: BLE001
        err = str(exc).lower()
        # Pass 2: vLLM guided_json
        if "400" in err or "response_format" in err or "json_schema" in err:
            try:
                resp = _create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    extra_body={"guided_json": schema.model_json_schema()},
                )
                raw_text = (resp.choices[0].message.content or "").strip()
                parsed = _parse(schema, raw_text)
                if parsed is not None:
                    return parsed
            except Exception as exc2:  # noqa: BLE001
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
            repaired = (resp.choices[0].message.content or "").strip()
            return _parse(schema, repaired)
        except Exception as exc:  # noqa: BLE001
            print(f"[llm] repair failed: {type(exc).__name__}: {exc}", flush=True)

    return None
