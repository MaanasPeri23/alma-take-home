import os

# Settings has no defaults for secrets. Inside the api container they come from .env; for host-side
# unit tests (`make test-fast`) fill in throwaway values before anything imports app.config.
for key, value in {
    "JWT_SECRET": "test-secret",
    "S3_ACCESS_KEY": "test",
    "S3_SECRET_KEY": "test",
}.items():
    os.environ.setdefault(key, value)
