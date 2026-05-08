# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

import hashlib

from django.db import models


class ImageAsset(models.Model):
    organization = models.ForeignKey(
        "tenants.Organization",
        on_delete=models.CASCADE,
        related_name="image_assets",
        null=True,
        blank=True,
    )

    original_filename = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=100)
    size_bytes = models.PositiveIntegerField()

    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)

    sha256 = models.CharField(max_length=64, db_index=True)

    data = models.BinaryField()
    thumbnail_data = models.BinaryField(null=True, blank=True)

    public_visible = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Bild"
        verbose_name_plural = "Bilder"

    def __str__(self):
        return self.original_filename

    @staticmethod
    def calculate_sha256(binary_data: bytes) -> str:
        return hashlib.sha256(binary_data).hexdigest()