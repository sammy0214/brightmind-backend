"""Object storage abstraction. Local disk for dev; swap in S3/R2 (regional bucket) for prod."""
from pathlib import Path
from typing import Protocol

from app.config import get_settings


class Storage(Protocol):
    async def put(self, key: str, data: bytes) -> str: ...


class LocalStorage:
    def __init__(self, root: str | None = None):
        s = get_settings()
        self.root = Path(root or s.storage_dir) / s.region  # region-scoped, like the real buckets

    async def put(self, key: str, data: bytes) -> str:
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key


# TODO(prod): S3Storage using boto3/aioboto3 against a bucket in the SAME region as the DB.
