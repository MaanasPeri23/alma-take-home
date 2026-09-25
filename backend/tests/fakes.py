"""In-memory stand-ins for storage and email, used by unit tests via dependency overrides."""

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import BinaryIO

from app.storage.base import ObjectNotFound


class InMemoryStorage:
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, str]] = {}

    def ensure_bucket(self) -> None:
        pass

    def put(self, key: str, fileobj: BinaryIO, content_type: str) -> None:
        self.objects[key] = (fileobj.read(), content_type)

    def open(self, key: str) -> Iterator[bytes]:
        if key not in self.objects:
            raise ObjectNotFound(key)
        return iter([self.objects[key][0]])

    def delete(self, key: str) -> None:
        self.objects.pop(key, None)


@dataclass
class SentEmail:
    to: str
    subject: str
    body: str


@dataclass
class RecordingEmailSender:
    sent: list[SentEmail] = field(default_factory=list)
    fail: bool = False

    def send(self, to: str, subject: str, body: str) -> None:
        if self.fail:
            raise ConnectionError("SMTP server unavailable")
        self.sent.append(SentEmail(to, subject, body))
