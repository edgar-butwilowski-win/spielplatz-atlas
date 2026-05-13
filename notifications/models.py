# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone


class SystemNotification(models.Model):
    TYPE_DEFECT_ASSIGNED = "defect_assigned"
    TYPE_GENERAL = "general"

    TYPE_CHOICES = [
        (TYPE_DEFECT_ASSIGNED, "Mangel zugewiesen"),
        (TYPE_GENERAL, "Allgemeine Systemnachricht"),
    ]

    STATUS_PENDING = "pending"
    STATUS_SENT = "sent"
    STATUS_FAILED = "failed"
    STATUS_NO_SUBSCRIPTION = "no_subscription"

    DELIVERY_STATUS_CHOICES = [
        (STATUS_PENDING, "Offen"),
        (STATUS_SENT, "Gesendet"),
        (STATUS_FAILED, "Fehlgeschlagen"),
        (STATUS_NO_SUBSCRIPTION, "Kein Gerät registriert"),
    ]

    organization = models.ForeignKey(
        "tenants.Organization",
        on_delete=models.CASCADE,
        related_name="system_notifications",
        verbose_name="Organisation",
    )

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="system_notifications",
        verbose_name="Empfängerin oder Empfänger",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_system_notifications",
        verbose_name="Erstellt durch",
    )

    title = models.CharField("Titel", max_length=160)
    message = models.TextField("Nachricht")

    notification_type = models.CharField(
        "Nachrichtentyp",
        max_length=50,
        choices=TYPE_CHOICES,
        default=TYPE_GENERAL,
    )

    related_defect = models.ForeignKey(
        "inspections.Defect",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="system_notifications",
        verbose_name="Zugehöriger Mangel",
    )

    url = models.CharField(
        "Zieladresse",
        max_length=500,
        blank=True,
        help_text="Interne Adresse, die beim Öffnen der Nachricht geladen wird.",
    )

    read_at = models.DateTimeField("Gelesen am", null=True, blank=True)
    sent_at = models.DateTimeField("Gesendet am", null=True, blank=True)

    delivery_status = models.CharField(
        "Zustellstatus",
        max_length=30,
        choices=DELIVERY_STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    delivery_error = models.TextField("Zustellfehler", blank=True)

    created_at = models.DateTimeField("Erstellt am", auto_now_add=True)
    updated_at = models.DateTimeField("Aktualisiert am", auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "recipient", "read_at"]),
            models.Index(fields=["recipient", "delivery_status", "created_at"]),
        ]
        verbose_name = "Systemnachricht"
        verbose_name_plural = "Systemnachrichten"

    def __str__(self):
        return f"{self.title} – {self.recipient}"

    @property
    def is_read(self):
        return self.read_at is not None

    def mark_as_read(self, save=True):
        if not self.read_at:
            self.read_at = timezone.now()
            if save:
                self.save(update_fields=["read_at", "updated_at"])

    @classmethod
    def build_defect_url(cls, defect):
        return reverse("internal:edit_defect", kwargs={"defect_id": defect.id})


class DefectAssignment(models.Model):
    defect = models.OneToOneField(
        "inspections.Defect",
        on_delete=models.CASCADE,
        related_name="assignment",
        verbose_name="Mangel",
    )

    organization = models.ForeignKey(
        "tenants.Organization",
        on_delete=models.CASCADE,
        related_name="defect_assignments",
        verbose_name="Organisation",
    )

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_defects",
        verbose_name="Zuständige Person",
    )

    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_defect_changes",
        verbose_name="Zugewiesen durch",
    )

    assigned_at = models.DateTimeField("Zugewiesen am", default=timezone.now)
    note = models.TextField("Interne Bemerkung zur Zuweisung", blank=True)

    class Meta:
        ordering = ["-assigned_at"]
        indexes = [
            models.Index(fields=["organization", "assigned_to", "assigned_at"]),
        ]
        verbose_name = "Mangel-Zuweisung"
        verbose_name_plural = "Mangel-Zuweisungen"

    def __str__(self):
        if self.assigned_to:
            return f"{self.defect} – {self.assigned_to}"
        return f"{self.defect} – keine Zuweisung"


class PushSubscription(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="push_subscriptions",
        verbose_name="Benutzer",
    )

    organization = models.ForeignKey(
        "tenants.Organization",
        on_delete=models.CASCADE,
        related_name="push_subscriptions",
        verbose_name="Organisation",
    )

    endpoint = models.URLField("Push-Endpunkt", max_length=1000, unique=True)
    p256dh_key = models.TextField("P256DH-Schlüssel")
    auth_key = models.TextField("Auth-Schlüssel")
    user_agent = models.TextField("Browser / Gerät", blank=True)

    is_active = models.BooleanField("Aktiv", default=True)
    created_at = models.DateTimeField("Erstellt am", auto_now_add=True)
    last_seen_at = models.DateTimeField("Zuletzt gesehen am", auto_now=True)

    class Meta:
        ordering = ["user__username", "-last_seen_at"]
        indexes = [
            models.Index(fields=["user", "organization", "is_active"]),
        ]
        verbose_name = "Push-Gerät"
        verbose_name_plural = "Push-Geräte"

    def __str__(self):
        return f"{self.user} – {self.organization}"
