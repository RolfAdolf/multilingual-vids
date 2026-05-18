import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="TranslationModel",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("slug", models.CharField(choices=[("seamless_m4t", "SeamlessM4T"), ("zeroswot", "ZeroSwot"), ("zeroshot", "Zeroshot pipeline")], max_length=32, unique=True)),
                ("display_name", models.CharField(max_length=256)),
                ("description", models.TextField(blank=True)),
                ("worker_queue", models.CharField(max_length=64)),
                ("is_active", models.BooleanField(default=True)),
                ("config", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"db_table": "model", "ordering": ["display_name"]},
        ),
        migrations.CreateModel(
            name="ModelLanguage",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("source_language_code", models.CharField(max_length=8)),
                ("target_language_code", models.CharField(max_length=8)),
                ("source_model_lang_code", models.CharField(max_length=32)),
                ("target_model_lang_code", models.CharField(max_length=32)),
                ("source_name_en", models.CharField(blank=True, max_length=128)),
                ("source_name_ru", models.CharField(blank=True, max_length=128)),
                ("target_name_en", models.CharField(blank=True, max_length=128)),
                ("target_name_ru", models.CharField(blank=True, max_length=128)),
                ("bleu", models.FloatField(blank=True, null=True)),
                ("nist", models.FloatField(blank=True, null=True)),
                ("dataset_name", models.CharField(blank=True, default="default", max_length=128)),
                ("measured_at", models.DateTimeField(blank=True, null=True)),
                ("notes", models.TextField(blank=True)),
                ("model", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="languages", to="translation_models.translationmodel")),
            ],
            options={"db_table": "model_language"},
        ),
        migrations.AddIndex(
            model_name="modellanguage",
            index=models.Index(fields=["source_language_code", "target_language_code"], name="idx_model_language_pair"),
        ),
        migrations.AddConstraint(
            model_name="modellanguage",
            constraint=models.UniqueConstraint(fields=("model", "source_language_code", "target_language_code"), name="uniq_model_language_pair"),
        ),
    ]
