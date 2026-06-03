# Generated after migration history reset.

from datetime import timedelta

from django.core.validators import RegexValidator
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Organization",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200)),
                ("slug", models.SlugField(max_length=80, unique=True)),
                ("is_active", models.BooleanField(default=False)),
                ("is_public", models.BooleanField(default=True)),
                ("primary_color", models.CharField(default="#0F766E", max_length=7, validators=[RegexValidator(message="Bitte eine gültige HEX-Farbe verwenden, z. B. #0F766E.", regex="^#([A-Fa-f0-9]{6})$")])),
                ("secondary_color", models.CharField(default="#F59E0B", max_length=7, validators=[RegexValidator(message="Bitte eine gültige HEX-Farbe verwenden, z. B. #0F766E.", regex="^#([A-Fa-f0-9]{6})$")])),
                ("workday_monday", models.BooleanField(default=True, verbose_name="Montag")),
                ("workday_tuesday", models.BooleanField(default=True, verbose_name="Dienstag")),
                ("workday_wednesday", models.BooleanField(default=True, verbose_name="Mittwoch")),
                ("workday_thursday", models.BooleanField(default=True, verbose_name="Donnerstag")),
                ("workday_friday", models.BooleanField(default=True, verbose_name="Freitag")),
                ("workday_saturday", models.BooleanField(default=False, verbose_name="Samstag")),
                ("workday_sunday", models.BooleanField(default=False, verbose_name="Sonntag")),
                ("planning_lead_time_workdays", models.PositiveSmallIntegerField(default=7, help_text="Anzahl Arbeitstage, die das Planungsdatum standardmässig vor dem Fälligkeitsdatum liegen soll.", verbose_name="Planungsdatum: Arbeitstage vor Fälligkeit")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["name"], "verbose_name": "Organisation", "verbose_name_plural": "Organisationen"},
        ),
        migrations.CreateModel(
            name="OrganizationRegistrationRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("organization_name", models.CharField(max_length=200)),
                ("organization_slug", models.SlugField(max_length=80)),
                ("admin_first_name", models.CharField(max_length=100)),
                ("admin_last_name", models.CharField(max_length=100)),
                ("admin_email", models.EmailField(max_length=254)),
                ("message", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("pending", "Ausstehend"), ("approved", "Genehmigt"), ("rejected", "Abgelehnt")], default="pending", max_length=20)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("review_note", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["-created_at"], "verbose_name": "Organisationsanfrage", "verbose_name_plural": "Organisationsanfragen"},
        ),
    ]
