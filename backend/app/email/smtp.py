import smtplib
from email.message import EmailMessage

from app.config import Settings


class SmtpEmailSender:
    def __init__(self, settings: Settings) -> None:
        self.host = settings.smtp_host
        self.port = settings.smtp_port
        self.sender = settings.email_from

    def send(self, to: str, subject: str, body: str) -> None:
        message = EmailMessage()
        message["From"] = self.sender
        message["To"] = to
        message["Subject"] = subject
        message.set_content(body)

        with smtplib.SMTP(self.host, self.port, timeout=10) as smtp:
            smtp.send_message(message)
