# Generated after migration history reset.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="ImageAsset",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("original_filename", models.CharField(max_length=255)),
                ("mime_type", models.CharField(max_length=100)),
                ("size_bytes", models.PositiveIntegerField()),
                ("width", models.PositiveIntegerField(blank=True, null=True)),
                ("height", models.PositiveIntegerField(blank=True, null=True)),
                ("sha256", models.CharField(db_index=True, max_length=64)),
                ("data", models.BinaryField()),
                ("thumbnail_data", models.BinaryField(blank=True, null=True)),
                ("public_visible", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("organization", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="image_assets", to="tenants.organization")),
            ],
            options={"ordering": ["-created_at"], "verbose_name": "Bild", "verbose_name_plural": "Bilder"},
        ),
    ]
