# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

from django.db import models
from django.core.validators import RegexValidator


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

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Organisation"
        verbose_name_plural = "Organisationen"

    def __str__(self):
        return self.name


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