# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

from django.db import models


class Playground(models.Model):
    organization = models.ForeignKey(
        "tenants.Organization",
        on_delete=models.CASCADE,
        related_name="playgrounds",
    )

    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=100)

    address = models.CharField(max_length=300, blank=True)
    district = models.CharField(max_length=100, blank=True)

    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    description = models.TextField(blank=True)

    photo = models.ForeignKey(
        "media_assets.ImageAsset",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="playgrounds",
        verbose_name="Foto",
        help_text="Optionales Hauptfoto des Spielplatzes.",
    )

    is_active = models.BooleanField(default=True)
    public_visible = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("organization", "slug")]
        ordering = ["organization__name", "name"]
        verbose_name = "Spielplatz"
        verbose_name_plural = "Spielplätze"

    def __str__(self):
        return f"{self.name} – {self.organization.name}"
    
    def get_preview_photo(self):
        if self.photo_id:
            return self.photo
    
        equipment_with_photo = (
            self.equipment
            .filter(
                is_active=True,
                public_visible=True,
                photo__isnull=False,
            )
            .select_related("photo")
            .order_by("name")
            .first()
        )
    
        if equipment_with_photo:
            return equipment_with_photo.photo
    
        return None


class EquipmentType(models.Model):
    organization = models.ForeignKey(
        "tenants.Organization",
        on_delete=models.CASCADE,
        related_name="equipment_types",
        null=True,
        blank=True,
        help_text="Leer bedeutet: globaler Standard-Gerätetyp.",
    )

    name = models.CharField(max_length=200)
    code = models.CharField(max_length=80, blank=True)

    norm_reference = models.CharField(
        max_length=200,
        blank=True,
        help_text="Zum Beispiel: SN EN 1176, SN EN 1177 oder gerätespezifische Referenz.",
    )

    is_standard = models.BooleanField(
        default=False,
        help_text="Ja, wenn dieser Eintrag Teil des globalen App-Standardkatalogs ist.",
    )

    standard_version = models.CharField(
        max_length=80,
        blank=True,
        help_text="Version des Standardkatalogs, z. B. SN-EN-1176-1177-v1.",
    )

    source_note = models.TextField(
        blank=True,
        help_text="Interner Hinweis zur Quelle oder fachlichen Herleitung.",
    )

    is_locked = models.BooleanField(
        default=False,
        help_text="Gesperrte Standardwerte können nur durch Super-Admins geändert werden.",
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Spielgeräteart"
        verbose_name_plural = "Spielgerätearten"

    def __str__(self):
        if self.is_standard:
            return f"{self.name} (Standard)"
        return self.name


class PlayEquipment(models.Model):
    playground = models.ForeignKey(
        Playground,
        on_delete=models.CASCADE,
        related_name="equipment",
    )

    equipment_type = models.ForeignKey(
        EquipmentType,
        on_delete=models.PROTECT,
        related_name="equipment",
    )

    name = models.CharField(max_length=200)
    inventory_number = models.CharField(max_length=100, blank=True)

    manufacturer = models.CharField(max_length=150, blank=True)
    year_built = models.PositiveIntegerField(null=True, blank=True)

    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    public_visible = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    photo = models.ForeignKey(
        "media_assets.ImageAsset",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="play_equipment",
        verbose_name="Foto",
        help_text="Optionales Hauptfoto dieses Spielgeräts.",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["playground__name", "name"]
        verbose_name = "Spielgerät"
        verbose_name_plural = "Spielgeräte"

    def __str__(self):
        return f"{self.name} – {self.playground.name}"
    
class PlaygroundSurface(models.Model):
    SURFACE_TYPE_CHOICES = [
        ("sand", "Sand"),
        ("gravel", "Rundkies / Fallschutzkies"),
        ("wood_chips", "Holzschnitzel"),
        ("bark", "Rindenmulch"),
        ("rubber", "Fallschutzbelag"),
        ("grass", "Rasen"),
        ("other", "Sonstiger Belag"),
    ]

    playground = models.ForeignKey(
        Playground,
        on_delete=models.CASCADE,
        related_name="surfaces",
    )

    name = models.CharField(max_length=200)
    surface_type = models.CharField(
        max_length=50,
        choices=SURFACE_TYPE_CHOICES,
        default="other",
    )

    description = models.TextField(blank=True)

    public_visible = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["playground__name", "name"]
        verbose_name = "Fallschutzfläche / Boden"
        verbose_name_plural = "Fallschutzflächen / Böden"

    def __str__(self):
        return f"{self.name} – {self.playground.name}"


class PlaygroundAccessory(models.Model):
    ACCESSORY_TYPE_CHOICES = [
        ("bench", "Sitzbank"),
        ("waste_bin", "Abfalleimer"),
        ("fence", "Zaun"),
        ("gate", "Tor"),
        ("sign", "Beschilderung"),
        ("lighting", "Beleuchtung"),
        ("table", "Tisch"),
        ("shade", "Sonnenschutz"),
        ("other", "Sonstige Ausstattung"),
    ]

    playground = models.ForeignKey(
        Playground,
        on_delete=models.CASCADE,
        related_name="accessories",
    )

    name = models.CharField(max_length=200)
    accessory_type = models.CharField(
        max_length=50,
        choices=ACCESSORY_TYPE_CHOICES,
        default="other",
    )

    description = models.TextField(blank=True)

    public_visible = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["playground__name", "name"]
        verbose_name = "Zusatzausstattung"
        verbose_name_plural = "Zusatzausstattung"

    def __str__(self):
        return f"{self.name} – {self.playground.name}"