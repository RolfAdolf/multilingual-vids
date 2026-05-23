from django.conf import settings
from django.core.management.base import BaseCommand

from storage import s3


class Command(BaseCommand):
    help = "Apply CORS rules on Yandex Object Storage buckets (required for browser presigned PUT)."

    def handle(self, *args, **options):
        origins = settings.S3_CORS_ALLOWED_ORIGINS
        buckets = {
            settings.YANDEX_S3_BUCKET_UPLOADS,
            settings.YANDEX_S3_BUCKET_RESULTS,
            settings.YANDEX_S3_BUCKET_TEMP,
        }
        for bucket in buckets:
            s3.put_bucket_cors(bucket, origins)
            self.stdout.write(
                self.style.SUCCESS(f"CORS updated for bucket {bucket}: {origins}")
            )
