from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Language",
            fields=[
                ("code", models.CharField(max_length=16, primary_key=True, serialize=False)),
                ("api_code", models.CharField(db_index=True, max_length=16)),
                ("name_en", models.CharField(max_length=128)),
                ("name_ru", models.CharField(blank=True, max_length=128)),
                ("script", models.CharField(blank=True, max_length=16)),
                ("supports_source_speech", models.BooleanField(default=False)),
                ("supports_source_text", models.BooleanField(default=False)),
                ("supports_target_speech", models.BooleanField(default=False)),
                ("supports_target_text", models.BooleanField(default=False)),
            ],
            options={"db_table": "language", "ordering": ["name_en"]},
        ),
    ]
