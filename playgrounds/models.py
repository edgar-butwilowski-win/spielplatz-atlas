# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Playground(models.Model):
    organization = models.ForeignKey(
        "tenants.Organization",
        on_delete=models.CASCADE,
        related_name="playgrounds",
        verbose_name="Organisation",
    )

    uuid = models.UUIDField(
        "UUID",
        default=uuid.uuid4,
        unique=True,
        help_text="Eindeutige UUID des Spielplatzes. Beim Webservice-Abgleich wird darüber synchronisiert.",
    )

    name = models.CharField("Name", max_length=200)
    slug = models.SlugField("URL-Kürzel", max_length=100)
    number = models.IntegerField("Nummer", null=True, blank=True)

    address = models.CharField("Adresse", max_length=300, blank=True)
    street_name = models.CharField("Strassenname", max_length=200, blank=True)
    house_number = models.CharField("Hausnummer", max_length=40, blank=True)
    district = models.CharField("Quartier", max_length=100, blank=True)

    latitude = models.DecimalField("LV95 Y", max_digits=16, decimal_places=8, null=True, blank=True)
    longitude = models.DecimalField("LV95 X", max_digits=16, decimal_places=8, null=True, blank=True)

    description = models.TextField("Beschrieb", blank=True)
    construction_costs = models.FloatField("Erstellungskosten", null=True, blank=True)

    inspection_suspended_from = models.DateField(
        "Inspektion aussetzen von",
        null=True,
        blank=True,
    )
    inspection_suspended_until = models.DateField(
        "Inspektion aussetzen bis",
        null=True,
        blank=True,
    )

    photo = models.ForeignKey(
        "media_assets.ImageAsset",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="playgrounds",
        verbose_name="Foto",
        help_text="Optionales Hauptfoto des Spielplatzes.",
    )

    is_active = models.BooleanField("Aktiv", default=True)
    public_visible = models.BooleanField("Öffentlich", default=True)

    created_at = models.DateTimeField("Erstellt am", auto_now_add=True)

    class Meta:
        unique_together = [("organization", "slug")]
        ordering = ["organization__name", "name"]
        verbose_name = "Spielplatz"
        verbose_name_plural = "Spielplätze"

    def __str__(self):
        return f"{self.name} – {self.organization.name}"

    def clean(self):
        super().clean()

        if (
            self.inspection_suspended_from
            and self.inspection_suspended_until
            and self.inspection_suspended_until < self.inspection_suspended_from
        ):
            raise ValidationError({
                "inspection_suspended_until": "Das Enddatum darf nicht vor dem Startdatum liegen."
            })

        if bool(self.longitude) != bool(self.latitude):
            raise ValidationError(
                "Bitte immer ein vollständiges LV95-Koordinatenpaar mit X und Y erfassen."
            )

        if self.longitude and not (2400000 <= self.longitude <= 2900000):
            raise ValidationError({
                "longitude": "Bitte einen gültigen LV95-X-Wert erfassen."
            })

        if self.latitude and not (1000000 <= self.latitude <= 1350000):
            raise ValidationError({
                "latitude": "Bitte einen gültigen LV95-Y-Wert erfassen."
            })

    @property
    def is_inspection_suspended(self):
        today = timezone.localdate()

        if not self.inspection_suspended_from:
            return False

        if self.inspection_suspended_from > today:
            return False

        if self.inspection_suspended_until is None:
            return True

        return today <= self.inspection_suspended_until

    @property
    def lv95_x(self):
        return self.longitude

    @property
    def lv95_y(self):
        return self.latitude

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
        verbose_name="Organisation",
        help_text="Leer bedeutet: globale Standard-Spielgeräteart.",
    )

    name = models.CharField("Name", max_length=200)
    code = models.CharField("Code", max_length=80, blank=True)

    norm_reference = models.CharField(
        "Norm-/Quellenhinweis",
        max_length=200,
        blank=True,
        help_text="Zum Beispiel: SN EN 1176, SN EN 1177 oder gerätespezifische Referenz.",
    )

    is_standard = models.BooleanField(
        "Standardwert",
        default=False,
        help_text="Ja, wenn dieser Eintrag Teil des globalen App-Standardkatalogs ist.",
    )

    standard_version = models.CharField(
        "Standardversion",
        max_length=80,
        blank=True,
        help_text="Version des Standardkatalogs, z. B. SN-EN-1176-1177-v1.",
    )

    source_note = models.TextField(
        "Interner Quellen-/Bearbeitungshinweis",
        blank=True,
    )

    is_locked = models.BooleanField(
        "Gesperrt",
        default=False,
        help_text="Gesperrte Standardwerte können nur durch Super-Admins geändert werden.",
    )

    is_active = models.BooleanField("Aktiv", default=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Spielgeräteart"
        verbose_name_plural = "Spielgerätearten"

    def __str__(self):
        if self.is_standard:
            return f"{self.name} (Standard)"
        return self.name


class EquipmentSupplier(models.Model):
    organization = models.ForeignKey(
        "tenants.Organization",
        on_delete=models.CASCADE,
        related_name="equipment_suppliers",
        null=True,
        blank=True,
        verbose_name="Organisation",
        help_text="Leer bedeutet: global nutzbarer Lieferant.",
    )

    name = models.CharField("Name", max_length=200)
    is_active = models.BooleanField("Aktiv", default=True)
    created_at = models.DateTimeField("Erstellt am", auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Lieferant"
        verbose_name_plural = "Lieferanten"
        unique_together = [("organization", "name")]

    def __str__(self):
        if self.organization_id:
            return f"{self.name} – {self.organization.name}"

        return f"{self.name} (global)"


class PlayEquipment(models.Model):
    RENOVATION_TOTAL = "total"
    RENOVATION_PARTIAL = "partial"

    RENOVATION_TYPE_CHOICES = [
        (RENOVATION_TOTAL, "Totalsanierung"),
        (RENOVATION_PARTIAL, "Teilsanierung"),
    ]

    playground = models.ForeignKey(
        Playground,
        on_delete=models.CASCADE,
        related_name="equipment",
        verbose_name="Spielplatz",
    )

    equipment_type = models.ForeignKey(
        EquipmentType,
        on_delete=models.PROTECT,
        related_name="equipment",
        verbose_name="Spielgeräteart",
    )

    name = models.CharField("Name", max_length=200)
    sequence_number = models.PositiveIntegerField("Laufnummer", null=True, blank=True)
    inventory_number = models.CharField("Inventar-Nr.", max_length=100, blank=True)

    manufacturer = models.CharField("Hersteller", max_length=150, blank=True)
    supplier = models.ForeignKey(
        EquipmentSupplier,
        on_delete=models.SET_NULL,
        related_name="equipment",
        null=True,
        blank=True,
        verbose_name="Lieferant",
    )
    norm = models.CharField("Norm", max_length=200, blank=True)
    year_built = models.PositiveIntegerField("Baujahr", null=True, blank=True)
    build_date = models.DateField("Baudatum", null=True, blank=True)
    demolition_date = models.DateField("Abbruchdatum", null=True, blank=True)

    renovation_type = models.CharField(
        "Sanierungsart",
        max_length=20,
        choices=RENOVATION_TYPE_CHOICES,
        blank=True,
    )
    recommended_renovation_year = models.PositiveIntegerField(
        "Empfohlenes Sanierungsjahr",
        null=True,
        blank=True,
        help_text="Vierstellige Jahreszahl. Das Jahr darf nicht in der Vergangenheit liegen.",
    )
    renovation_comment = models.CharField("Kommentar zur Sanierung", max_length=500, blank=True)

    not_inspectable = models.BooleanField("Nicht prüfbar", default=False)
    not_inspectable_reason = models.CharField("Grund nicht prüfbar", max_length=500, blank=True)

    latitude = models.DecimalField("Breitengrad", max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField("Längengrad", max_digits=9, decimal_places=6, null=True, blank=True)

    public_visible = models.BooleanField("Öffentlich sichtbar", default=True)
    is_active = models.BooleanField("Aktiv", default=True)

    photo = models.ForeignKey(
        "media_assets.ImageAsset",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="play_equipment",
        verbose_name="Foto",
        help_text="Optionales Hauptfoto dieses Spielgeräts.",
    )

    created_at = models.DateTimeField("Erstellt am", auto_now_add=True)

    class Meta:
        ordering = ["playground__name", "sequence_number", "name"]
        verbose_name = "Spielgerät"
        verbose_name_plural = "Spielgeräte"

    def __str__(self):
        return f"{self.name} – {self.playground.name}"

    def clean(self):
        super().clean()

        if self.recommended_renovation_year is not None:
            current_year = timezone.localdate().year

            if self.recommended_renovation_year < current_year:
                raise ValidationError({
                    "recommended_renovation_year": "Das empfohlene Sanierungsjahr darf nicht in der Vergangenheit liegen."
                })

            if self.recommended_renovation_year < 1000 or self.recommended_renovation_year > 9999:
                raise ValidationError({
                    "recommended_renovation_year": "Bitte eine vierstellige Jahreszahl eingeben."
                })

        if self.not_inspectable and not self.not_inspectable_reason:
            raise ValidationError({
                "not_inspectable_reason": "Bitte einen Grund angeben, wenn das Spielgerät nicht prüfbar ist."
            })

    @property
    def has_pending_renovation(self):
        return self.recommended_renovation_year is not None

    @property
    def is_planned(self):
        return bool(self.build_date and self.build_date > timezone.localdate())

    @property
    def has_future_demolition(self):
        return bool(self.demolition_date and self.demolition_date > timezone.localdate())
    
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
        verbose_name="Spielplatz",
    )

    name = models.CharField("Name", max_length=200)
    surface_type = models.CharField(
        "Belagsart",
        max_length=50,
        choices=SURFACE_TYPE_CHOICES,
        default="other",
    )

    description = models.TextField("Beschreibung", blank=True)

    public_visible = models.BooleanField("Öffentlich sichtbar", default=True)
    is_active = models.BooleanField("Aktiv", default=True)

    created_at = models.DateTimeField("Erstellt am", auto_now_add=True)

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
        verbose_name="Spielplatz",
    )

    name = models.CharField("Name", max_length=200)
    accessory_type = models.CharField(
        "Ausstattungsart",
        max_length=50,
        choices=ACCESSORY_TYPE_CHOICES,
        default="other",
    )

    description = models.TextField("Beschreibung", blank=True)

    public_visible = models.BooleanField("Öffentlich sichtbar", default=True)
    is_active = models.BooleanField("Aktiv", default=True)

    created_at = models.DateTimeField("Erstellt am", auto_now_add=True)

    class Meta:
        ordering = ["playground__name", "name"]
        verbose_name = "Zusatzausstattung"
        verbose_name_plural = "Zusatzausstattung"

    def __str__(self):
        return f"{self.name} – {self.playground.name}"


from .document_models import PlaygroundDocument
