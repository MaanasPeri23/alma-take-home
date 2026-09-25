"""Manual check for B1: one file into MinIO, one email into Mailpit. Run with `make smoke`."""

import io

from app.config import get_settings
from app.deps import get_email_sender, get_storage

storage = get_storage()
storage.ensure_bucket()
storage.put("smoke/hello.txt", io.BytesIO(b"Hello from make smoke\n"), "text/plain")
print(f"Stored smoke/hello.txt in bucket '{get_settings().s3_bucket}' (MinIO console :9001)")

get_email_sender().send(get_settings().attorney_email, "Smoke test", "Email is wired up.\n")
print("Sent 'Smoke test' email (Mailpit :8025)")
