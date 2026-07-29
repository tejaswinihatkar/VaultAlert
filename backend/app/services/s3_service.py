"""
VaultAlert — AWS S3 Storage Service
Handles snapshot uploads, pre-signed URL generation, and lifecycle management.
Gracefully stubs out if AWS credentials are not configured.
"""

import io
import uuid
from datetime import datetime, timezone
from typing import Optional

from loguru import logger

from app.core.config import settings


class S3Service:
    """
    AWS S3 service for media storage.
    When AWS credentials are not set, all operations return stub URLs and log warnings.
    """

    def __init__(self) -> None:
        self._enabled = bool(
            settings.AWS_ACCESS_KEY_ID
            and settings.AWS_SECRET_ACCESS_KEY
            and settings.AWS_S3_BUCKET
        )
        self._client = None
        if self._enabled:
            try:
                import boto3
                self._client = boto3.client(
                    "s3",
                    region_name=settings.AWS_REGION,
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                )
                logger.info(f"S3 Service: Connected to bucket '{settings.AWS_S3_BUCKET}'.")
            except ImportError:
                logger.warning("S3 Service: boto3 not installed. Using stub mode.")
                self._enabled = False
        else:
            logger.info("S3 Service: AWS credentials not configured — running in stub mode.")

    def _stub_url(self, key: str) -> str:
        """Return a placeholder URL when S3 is not configured."""
        return f"https://placeholder.vaultalert.io/{key}"

    async def upload_snapshot(
        self,
        data: bytes,
        locker_id: str,
        event_id: str,
        content_type: str = "image/jpeg",
        suffix: str = "before",
    ) -> str:
        """
        Upload a surveillance snapshot to S3.
        Returns the public or pre-signed URL.
        """
        timestamp = datetime.now(timezone.utc).strftime("%Y/%m/%d")
        key = f"snapshots/{locker_id}/{timestamp}/{event_id}_{suffix}.jpg"

        if not self._enabled:
            logger.debug(f"S3 stub: would upload snapshot to s3://{settings.AWS_S3_BUCKET}/{key}")
            return self._stub_url(key)

        try:
            self._client.put_object(
                Bucket=settings.AWS_S3_BUCKET,
                Key=key,
                Body=data,
                ContentType=content_type,
                ServerSideEncryption="AES256",
            )
            logger.info(f"S3: Uploaded snapshot {key}")
            return f"https://{settings.AWS_S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"
        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            return self._stub_url(key)

    async def upload_video_clip(
        self,
        data: bytes,
        locker_id: str,
        event_id: str,
    ) -> str:
        """Upload a video clip recording to S3."""
        timestamp = datetime.now(timezone.utc).strftime("%Y/%m/%d")
        key = f"videos/{locker_id}/{timestamp}/{event_id}.mp4"

        if not self._enabled:
            logger.debug(f"S3 stub: would upload video to s3://{settings.AWS_S3_BUCKET}/{key}")
            return self._stub_url(key)

        try:
            self._client.put_object(
                Bucket=settings.AWS_S3_BUCKET,
                Key=key,
                Body=data,
                ContentType="video/mp4",
                ServerSideEncryption="AES256",
            )
            return f"https://{settings.AWS_S3_BUCKET}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"
        except Exception as e:
            logger.error(f"S3 video upload failed: {e}")
            return self._stub_url(key)

    async def generate_presigned_url(self, key: str, expires: int = 3600) -> str:
        """
        Generate a time-limited pre-signed URL for private S3 objects.
        Returns stub URL if S3 not configured.
        """
        if not self._enabled:
            return self._stub_url(key)

        try:
            url = self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": settings.AWS_S3_BUCKET, "Key": key},
                ExpiresIn=expires,
            )
            return url
        except Exception as e:
            logger.error(f"S3 presign failed: {e}")
            return self._stub_url(key)

    async def delete_file(self, key: str) -> bool:
        """Delete a file from S3. Returns True on success."""
        if not self._enabled:
            logger.debug(f"S3 stub: would delete s3://{settings.AWS_S3_BUCKET}/{key}")
            return True

        try:
            self._client.delete_object(Bucket=settings.AWS_S3_BUCKET, Key=key)
            logger.info(f"S3: Deleted {key}")
            return True
        except Exception as e:
            logger.error(f"S3 delete failed: {e}")
            return False

    async def apply_retention_policy(self, locker_id: str, retention_days: int = 30) -> int:
        """
        Delete snapshots older than retention_days for a locker.
        Returns count of deleted objects.
        """
        if not self._enabled:
            logger.debug("S3 stub: skipping retention policy.")
            return 0

        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
        prefix = f"snapshots/{locker_id}/"
        deleted = 0

        try:
            paginator = self._client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=settings.AWS_S3_BUCKET, Prefix=prefix):
                for obj in page.get("Contents", []):
                    if obj["LastModified"] < cutoff:
                        self._client.delete_object(
                            Bucket=settings.AWS_S3_BUCKET, Key=obj["Key"]
                        )
                        deleted += 1
        except Exception as e:
            logger.error(f"S3 retention policy error: {e}")

        logger.info(f"S3: Retention cleanup removed {deleted} objects for locker {locker_id}.")
        return deleted


# Module-level singleton
s3_service = S3Service()
