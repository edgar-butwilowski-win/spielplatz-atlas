from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "role",
                    models.CharField(
                        "Rolle",
                        choices=[
                            ("reader", "Lesender interner User"),
                            ("inspector", "Kontrolleur/in"),
                            ("org_admin", "Organisations-Admin"),
                        ],
                        default="reader",
                        help_text="Die Rolle ist die Quelle der fachlichen Berechtigungen.",
                        max_length=30,
                    ),
                ),
                ("is_active_for_organization", models.BooleanField("Aktiv für Organisation", default=True)),
                ("created_at", models.DateTimeField("Erstellt am", auto_now_add=True)),
                (
                    "organization",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="user_profiles",
                        to="tenants.organization",
                        verbose_name="Organisation",
                    ),
                ),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="profile",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="Benutzer",
                    ),
                ),
            ],
            options={"verbose_name": "Benutzerprofil", "verbose_name_plural": "Benutzerprofile"},
        ),
    ]
