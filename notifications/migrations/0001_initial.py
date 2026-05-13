# Generated for SpielplatzAtlas system notifications

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("inspections", "0001_initial"),
        ("tenants", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="SystemNotification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=160, verbose_name="Titel")),
                ("message", models.TextField(verbose_name="Nachricht")),
                ("notification_type", models.CharField(choices=[("defect_assigned", "Mangel zugewiesen"), ("general", "Allgemeine Systemnachricht")], default="general", max_length=50, verbose_name="Nachrichtentyp")),
                ("url", models.CharField(blank=True, help_text="Interne Adresse, die beim Öffnen der Nachricht geladen wird.", max_length=500, verbose_name="Zieladresse")),
                ("read_at", models.DateTimeField(blank=True, null=True, verbose_name="Gelesen am")),
                ("sent_at", models.DateTimeField(blank=True, null=True, verbose_name="Gesendet am")),
                ("delivery_status", models.CharField(choices=[("pending", "Offen"), ("sent", "Gesendet"), ("failed", "Fehlgeschlagen"), ("no_subscription", "Kein Gerät registriert")], default="pending", max_length=30, verbose_name="Zustellstatus")),
                ("delivery_error", models.TextField(blank=True, verbose_name="Zustellfehler")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Aktualisiert am")),
                ("created_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_system_notifications", to=settings.AUTH_USER_MODEL, verbose_name="Erstellt durch")),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="system_notifications", to="tenants.organization", verbose_name="Organisation")),
                ("recipient", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="system_notifications", to=settings.AUTH_USER_MODEL, verbose_name="Empfängerin oder Empfänger")),
                ("related_defect", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="system_notifications", to="inspections.defect", verbose_name="Zugehöriger Mangel")),
            ],
            options={
                "verbose_name": "Systemnachricht",
                "verbose_name_plural": "Systemnachrichten",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="DefectAssignment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("assigned_at", models.DateTimeField(default=django.utils.timezone.now, verbose_name="Zugewiesen am")),
                ("note", models.TextField(blank=True, verbose_name="Interne Bemerkung zur Zuweisung")),
                ("assigned_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="assigned_defect_changes", to=settings.AUTH_USER_MODEL, verbose_name="Zugewiesen durch")),
                ("assigned_to", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="assigned_defects", to=settings.AUTH_USER_MODEL, verbose_name="Zuständige Person")),
                ("defect", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="assignment", to="inspections.defect", verbose_name="Mangel")),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="defect_assignments", to="tenants.organization", verbose_name="Organisation")),
            ],
            options={
                "verbose_name": "Mangel-Zuweisung",
                "verbose_name_plural": "Mangel-Zuweisungen",
                "ordering": ["-assigned_at"],
            },
        ),
        migrations.CreateModel(
            name="PushSubscription",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("endpoint", models.URLField(max_length=1000, unique=True, verbose_name="Push-Endpunkt")),
                ("p256dh_key", models.TextField(verbose_name="P256DH-Schlüssel")),
                ("auth_key", models.TextField(verbose_name="Auth-Schlüssel")),
                ("user_agent", models.TextField(blank=True, verbose_name="Browser / Gerät")),
                ("is_active", models.BooleanField(default=True, verbose_name="Aktiv")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Erstellt am")),
                ("last_seen_at", models.DateTimeField(auto_now=True, verbose_name="Zuletzt gesehen am")),
                ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="push_subscriptions", to="tenants.organization", verbose_name="Organisation")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="push_subscriptions", to=settings.AUTH_USER_MODEL, verbose_name="Benutzer")),
            ],
            options={
                "verbose_name": "Push-Gerät",
                "verbose_name_plural": "Push-Geräte",
                "ordering": ["user__username", "-last_seen_at"],
            },
        ),
        migrations.AddIndex(
            model_name="systemnotification",
            index=models.Index(fields=["organization", "recipient", "read_at"], name="notificatio_organiz_a630a1_idx"),
        ),
        migrations.AddIndex(
            model_name="systemnotification",
            index=models.Index(fields=["recipient", "delivery_status", "created_at"], name="notificatio_recipie_0d6a5d_idx"),
        ),
        migrations.AddIndex(
            model_name="defectassignment",
            index=models.Index(fields=["organization", "assigned_to", "assigned_at"], name="notificatio_organiz_8d0483_idx"),
        ),
        migrations.AddIndex(
            model_name="pushsubscription",
            index=models.Index(fields=["user", "organization", "is_active"], name="notificatio_user_id_1754cd_idx"),
        ),
    ]
