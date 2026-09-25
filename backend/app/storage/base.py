from collections.abc import Iterator
from typing import BinaryIO, Protocol


class ObjectNotFound(Exception):
    """Raised by `open` when the key doesn't exist, before any bytes are streamed."""


class StorageBackend(Protocol):
    """Where resume files live. Business logic only sees this interface, so moving from MinIO to
    S3 (or anything else) is a configuration change."""

    def ensure_bucket(self) -> None:
        """Create the bucket if it doesn't exist. Safe to call on every startup."""

    def put(self, key: str, fileobj: BinaryIO, content_type: str) -> None: ...

    def open(self, key: str) -> Iterator[bytes]:
        """Stream the object in chunks, so large files never sit in memory whole.

        Must raise ObjectNotFound immediately (not on first read), so callers can return a 404
        before a streaming response has sent its headers."""
        ...

    def delete(self, key: str) -> None: ...
