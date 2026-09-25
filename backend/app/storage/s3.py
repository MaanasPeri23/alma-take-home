from collections.abc import Iterator
from typing import BinaryIO

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.config import Settings
from app.storage.base import ObjectNotFound

CHUNK_SIZE = 64 * 1024


class S3Storage:
    """StorageBackend for anything that speaks the S3 API. Locally that's MinIO; in production
    it would be S3 itself, with only the endpoint and credentials changing."""

    def __init__(self, settings: Settings) -> None:
        self.bucket = settings.s3_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            # MinIO needs path-style URLs (http://minio:9000/bucket/key).
            # Short timeouts: fail fast instead of hanging a request (or startup) for minutes.
            config=Config(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
                connect_timeout=3,
                read_timeout=10,
                retries={"max_attempts": 3},
            ),
            region_name="us-east-1",
        )

    def ensure_bucket(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError as exc:
            # Only a missing bucket is ours to fix; bad credentials (403) should surface as-is.
            if exc.response["Error"]["Code"] not in ("404", "NoSuchBucket"):
                raise
            self.client.create_bucket(Bucket=self.bucket)

    def put(self, key: str, fileobj: BinaryIO, content_type: str) -> None:
        self.client.upload_fileobj(
            fileobj, self.bucket, key, ExtraArgs={"ContentType": content_type}
        )

    def open(self, key: str) -> Iterator[bytes]:
        # Fetch eagerly (this is not a generator) so a missing key raises here, not mid-stream.
        try:
            body = self.client.get_object(Bucket=self.bucket, Key=key)["Body"]
        except ClientError as exc:
            if exc.response["Error"]["Code"] in ("404", "NoSuchKey"):
                raise ObjectNotFound(key) from exc
            raise

        def chunks() -> Iterator[bytes]:
            try:
                yield from body.iter_chunks(CHUNK_SIZE)
            finally:
                body.close()

        return chunks()

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)
