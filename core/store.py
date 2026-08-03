"""
Object storage for generated reports and cached precomputes.

Local disk for a laptop, S3-compatible (AWS / R2 / Spaces / MinIO) in
production. Reports must NOT be served as static files — delivery goes through
the signed, ownership-checked endpoint in api.py.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Optional, Protocol

from .config import S


class Store(Protocol):
    def put(self, key: str, data: bytes, content_type: str = "text/html") -> str: ...
    def get(self, key: str) -> bytes: ...
    def delete(self, key: str) -> None: ...
    def exists(self, key: str) -> bool: ...


class LocalStore:
    def __init__(self, root: str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _p(self, key: str) -> Path:
        p = (self.root / key).resolve()
        if not str(p).startswith(str(self.root.resolve())):
            raise ValueError("path traversal blocked")
        return p

    def put(self, key: str, data: bytes, content_type: str = "text/html") -> str:
        p = self._p(key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        return key

    def get(self, key: str) -> bytes:
        return self._p(key).read_bytes()

    def delete(self, key: str) -> None:
        try:
            self._p(key).unlink()
        except FileNotFoundError:
            pass

    def exists(self, key: str) -> bool:
        return self._p(key).is_file()

    def usage_bytes(self) -> int:
        return sum(f.stat().st_size for f in self.root.rglob("*") if f.is_file())


class S3Store:
    def __init__(self) -> None:
        import boto3                                   # imported lazily
        kw = {"region_name": S.s3_region}
        if S.s3_endpoint:
            kw["endpoint_url"] = S.s3_endpoint
        self.s3 = boto3.client("s3", **kw)
        self.bucket = S.s3_bucket

    def put(self, key: str, data: bytes, content_type: str = "text/html") -> str:
        self.s3.put_object(Bucket=self.bucket, Key=key, Body=data,
                           ContentType=content_type,
                           # reports are private; we serve them ourselves
                           ACL="private")
        return key

    def get(self, key: str) -> bytes:
        return self.s3.get_object(Bucket=self.bucket, Key=key)["Body"].read()

    def delete(self, key: str) -> None:
        self.s3.delete_object(Bucket=self.bucket, Key=key)

    def exists(self, key: str) -> bool:
        from botocore.exceptions import ClientError
        try:
            self.s3.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError:
            return False


_store: Optional[Store] = None


def store() -> Store:
    global _store
    if _store is None:
        _store = S3Store() if S.s3_bucket else LocalStore(S.local_store)
    return _store


def report_keys(report_id: str) -> tuple[str, str]:
    """Deterministic keys, sharded by id prefix to keep prefixes small."""
    shard = report_id[:2]
    return (f"reports/{shard}/{report_id}/free.html",
            f"reports/{shard}/{report_id}/paid.html")
