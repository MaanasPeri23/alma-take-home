from typing import Protocol


class EmailSender(Protocol):
    """How the app sends email. Locally it's Mailpit over SMTP; a real provider (SES, Postmark)
    is a settings change, since they all accept SMTP."""

    def send(self, to: str, subject: str, body: str) -> None: ...
