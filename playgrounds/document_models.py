# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

import hashlib

from django.db import models


class PlaygroundDocument(models.Model):
    DOCUMENT_TYPE_CERTIFICATE = "certificate"
    DOCUMENT_TYPE_ACCEPTANCE = "acceptance"

    DOCUMENT_TYPE_CHOICES = [
        (DOCUMENT_TYPE_CERTIFICATE, "Zertifikatsdokument"),
        (DOCUMENT_TYPE_ACCEPTANCE, "Abnahmedokument"),
    ]

    playground = models.ForeignKey(
        "playgrounds.Playground",
        on_delete=models.CASCADE,
        related_name="documents",
        verbose_name="Spielplatz",
    )
    document_type = models.CharField(
        "Dokumentart",
        max_length=20,
        choices=DOCUMENT_TYPE_CHOICES,
    )
    mime_type = models.CharField("MIME-Type", max_length=100, default="application/pdf")
    size_bytes = models.PositiveIntegerField("Dateigrösse in Bytes")
    sha256 = models.CharField("SHA-256", max_length=64, db_index=True)
    data = models.BinaryField("Dateidaten")
    created_at = models.DateTimeField("Erstellt am", auto_now_add=True)

    class Meta:
        ordering = ["document_type", "id"]
        verbose_name = "Spielplatz-Dokument"
        verbose_name_plural = "Spielplatz-Dokumente"

    def __str__(self):
        if self.pk:
            return f"{self.get_document_type_display()} #{self.pk}"

        return self.get_document_type_display()

    @staticmethod
    def calculate_sha256(binary_data: bytes) -> str:
        return hashlib.sha256(binary_data).hexdigest()

    @property
    def download_filename(self):
        if not self.pk:
            return "spielplatz-dokument.pdf"

        return f"spielplatz-dokument-{self.pk}.pdf"
