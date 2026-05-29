# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

from datetime import timedelta

from django.core.validators import RegexValidator
from django.db import models


hex_color_validator = RegexValidator(
    regex=r"^#([A-Fa-f0-9]{6})$",
    message="Bitte eine gültige HEX-Farbe verwenden, z. B. #0F766E.",
)


class Organization(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=80, unique=True)

    is_active = models.BooleanField(default=False)
    is_public = models.BooleanField(default=True)

    primary_color = models.CharField(
        max_length=7,
        default="#0F766E",
        validators=[hex_color_validator],
    )
    secondary_color = models.CharField(
        max_length=7,
        default="#F59E0B",
        validators=[hex_color_validator],
    )

    logo = models.ForeignKey(
        "media_assets.ImageAsset",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="organization_logos",
    )

    workday_monday = models.BooleanField("Montag", default=True)
    workday_tuesday = models.BooleanField("Dienstag", default=True)
    workday_wednesday = models.BooleanField("Mittwoch", default=True)
    workday_thursday = models.BooleanField("Donnerstag", default=True)
    workday_friday = models.BooleanField("Freitag", default=True)
    workday_saturday = models.BooleanField("Samstag", default=False)
    workday_sunday = models.BooleanField("Sonntag", default=False)
    planning_lead_time_workdays = models.PositiveSmallIntegerField(
        "Planungsdatum: Arbeitstage vor Fälligkeit",
        default=7,
        help_text="Anzahl Arbeitstage, die das Planungsdatum standardmässig vor dem Fälligkeitsdatum liegen soll.",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Organisation"
        verbose_name_plural = "Organisationen"

    def __str__(self):
        return self.name

    def get_workday_numbers(self):
        workdays = []
        if self.workday_monday:
            workdays.append(0)
        if self.workday_tuesday:
            workdays.append(1)
        if self.workday_wednesday:
            workdays.append(2)
        if self.workday_thursday:
            workdays.append(3)
        if self.workday_friday:
            workdays.append(4)
        if self.workday_saturday:
            workdays.append(5)
        if self.workday_sunday:
            workdays.append(6)
        return workdays

    def calculate_planned_date_from_due_date(self, due_date):
        lead_time = self.planning_lead_time_workdays or 0

        if lead_time <= 0:
            return due_date

        workdays = self.get_workday_numbers()

        if not workdays:
            return due_date

        planned_date = due_date
        remaining_days = lead_time

        while remaining_days > 0:
            planned_date -= timedelta(days=1)

            if planned_date.weekday() in workdays:
                remaining_days -= 1

        return planned_date


class OrganizationRegistrationRequest(models.Model):
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Ausstehend"),
        (STATUS_APPROVED, "Genehmigt"),
        (STATUS_REJECTED, "Abgelehnt"),
    ]

    organization_name = models.CharField(max_length=200)
    organization_slug = models.SlugField(max_length=80)

    admin_first_name = models.CharField(max_length=100)
    admin_last_name = models.CharField(max_length=100)
    admin_email = models.EmailField()

    message = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )

    reviewed_at = models.DateTimeField(null=True, blank=True)
    review_note = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Organisationsanfrage"
        verbose_name_plural = "Organisationsanfragen"

    def __str__(self):
        return f"{self.organization_name} ({self.get_status_display()})"
