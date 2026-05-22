from django.db import models


class Quartier(models.Model):
    organization = models.ForeignKey(
        "tenants.Organization",
        on_delete=models.CASCADE,
        related_name="quartiere",
        verbose_name="Organisation",
    )
    name = models.CharField("Quartiername", max_length=200)
    geom = models.JSONField(
        "Geometrie",
        help_text="GeoJSON-Geometrie des Quartiers. Erwartet Polygon oder MultiPolygon in LV95-Koordinaten.",
    )
    source = models.CharField("Quelle", max_length=500, blank=True)
    is_active = models.BooleanField("Aktiv", default=True)
    imported_at = models.DateTimeField("Importiert am", auto_now=True)

    class Meta:
        ordering = ["organization__name", "name"]
        unique_together = [("organization", "name")]
        verbose_name = "Quartier"
        verbose_name_plural = "Quartiere"

    def __str__(self):
        return f"{self.name} – {self.organization.name}"


class QuartierImport(models.Model):
    organization = models.ForeignKey(
        "tenants.Organization",
        on_delete=models.CASCADE,
        related_name="quartier_imports",
        verbose_name="Organisation",
    )
    geojson_file = models.FileField(
        "GeoJSON-Datei",
        upload_to="quartier_imports/",
        blank=True,
        help_text="Optional. Erwartet FeatureCollection mit Quartiername und Geometrie/geom.",
    )
    wfs_endpoint = models.URLField(
        "WFS-Endpoint",
        max_length=1000,
        blank=True,
        help_text="Optional. Zum Beispiel ein GetCapabilities-Endpoint eines WFS.",
    )
    replace_existing = models.BooleanField(
        "Bestehende Quartiere dieser Organisation vor Import deaktivieren",
        default=False,
    )
    last_import_message = models.TextField("Letzte Importmeldung", blank=True)
    created_at = models.DateTimeField("Erstellt am", auto_now_add=True)
    updated_at = models.DateTimeField("Aktualisiert am", auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        verbose_name = "Quartier-Import"
        verbose_name_plural = "Quartier-Importe"

    def __str__(self):
        return f"Quartier-Import – {self.organization.name}"
