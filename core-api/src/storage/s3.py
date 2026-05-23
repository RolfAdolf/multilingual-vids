from __future__ import annotations

import re
import uuid
from pathlib import Path

import boto3
from botocore.client import Config
from django.conf import settings


def s3_client():
    session = boto3.session.Session()
    return session.client(
        service_name="s3",
        endpoint_url=settings.YANDEX_S3_ENDPOINT,
        aws_access_key_id=settings.YANDEX_S3_ACCESS_KEY_ID,
        aws_secret_access_key=settings.YANDEX_S3_SECRET_ACCESS_KEY,
        region_name=settings.YANDEX_S3_REGION,
        config=Config(signature_version="s3v4"),
    )


def _safe_filename(filename: str) -> str:
    name = Path(filename).name
    name = re.sub(r"[^\w.\-]", "_", name)
    return name or "source.mp4"


def _safe_ext(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext in (".mp4", ".webm", ".mov", ".mkv"):
        return ext
    return ".mp4"


def upload_object_key(video_id: uuid.UUID, filename: str) -> str:
    ext = _safe_ext(filename)
    return f"uploads/{video_id}/source{ext}"


def task_prefix(video_id: uuid.UUID) -> str:
    return f"tasks/{video_id}"


def result_object_key(video_id: uuid.UUID) -> str:
    return f"tasks/{video_id}/translated.mp4"


def put_bucket_cors(bucket: str, allowed_origins: list[str]) -> None:
    """Allow browser PUT/GET to this bucket from listed origins (presigned upload)."""
    s3_client().put_bucket_cors(
        Bucket=bucket,
        CORSConfiguration={
            "CORSRules": [
                {
                    "AllowedOrigins": allowed_origins,
                    "AllowedMethods": ["GET", "PUT", "HEAD"],
                    "AllowedHeaders": ["*"],
                    "ExposeHeaders": ["ETag"],
                    "MaxAgeSeconds": 3600,
                }
            ]
        },
    )


def presigned_put_url(object_key: str, content_type: str, *, content_length: int) -> str:
    return s3_client().generate_presigned_url(
        ClientMethod="put_object",
        Params={
            "Bucket": settings.YANDEX_S3_BUCKET_UPLOADS,
            "Key": object_key,
            "ContentType": content_type,
            "ContentLength": content_length,
        },
        ExpiresIn=settings.S3_PRESIGNED_TTL_SECONDS,
    )


def presigned_get_url(object_key: str, *, bucket: str | None = None) -> str:
    bucket = bucket or settings.YANDEX_S3_BUCKET_RESULTS
    return s3_client().generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": bucket, "Key": object_key},
        ExpiresIn=settings.S3_PRESIGNED_TTL_SECONDS,
    )


def head_object(object_key: str, *, bucket: str | None = None) -> dict:
    bucket = bucket or settings.YANDEX_S3_BUCKET_UPLOADS
    return s3_client().head_object(Bucket=bucket, Key=object_key)


def download_prefix(
    prefix: str,
    dest_dir: Path,
    *,
    bucket: str | None = None,
) -> list[Path]:
    """Download all objects under an S3 prefix into dest_dir (keeps relative paths)."""
    bucket = bucket or settings.YANDEX_S3_BUCKET_UPLOADS
    normalized = prefix.strip().strip("/")
    if not normalized:
        raise ValueError("S3 prefix must be non-empty")
    s3_prefix = f"{normalized}/"

    client = s3_client()
    dest_dir = dest_dir.resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)

    downloaded: list[Path] = []
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=s3_prefix):
        for item in page.get("Contents", []):
            key = item["Key"]
            if key.endswith("/"):
                continue
            relative = key[len(s3_prefix) :]
            if not relative:
                continue
            local_path = dest_dir / relative
            local_path.parent.mkdir(parents=True, exist_ok=True)
            client.download_file(bucket, key, str(local_path))
            downloaded.append(local_path)

    if not downloaded:
        raise FileNotFoundError(
            f"No objects found under s3://{bucket}/{s3_prefix}"
        )
    return downloaded
