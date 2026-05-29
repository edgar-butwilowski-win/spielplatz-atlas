import uuid

from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.contrib.gis.geos import Point
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from .geo_constants import LV95_SRID


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
    location = gis_models.PointField(
        "Lagegeometrie",
        srid=LV95_SRID,
        null=True,
        blank=True,
        help_text="Aus LV95 X/Y abgeleiteter Punkt für räumliche Abfragen mit SpatiaLite.",
    )
    description = models.TextField("Beschrieb", blank=True)
    construction_costs = models.FloatField("Erstellungskosten", null=True, blank=True)
    inspection_suspended_from = models.DateField("Inspektion aussetzen von", null=True, blank=True)
    inspection_suspended_until = models.DateField("Inspektion aussetzen bis", null=True, blank=True)
    default_visual_inspector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="default_visual_playgrounds",
        verbose_name="Default-Kontrolleur/in visuell",
        help_text="Wird bei neuen visuellen Kontrollaufträgen automatisch voreingestellt.",
    )
    default_operational_inspector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="default_operational_playgrounds",
        verbose_name="Default-Kontrolleur/in operativ",
        help_text="Wird bei neuen operativen Kontrollaufträgen automatisch voreingestellt.",
    )
    default_annual_inspector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="default_annual_playgrounds",
        verbose_name="Default-Kontrolleur/in jährlich",
        help_text="Wird bei neuen jährlichen Kontrollaufträgen automatisch voreingestellt.",
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
        if self.inspection_suspended_from and self.inspection_suspended_until and self.inspection_suspended_until < self.inspection_suspended_from:
            raise ValidationError({"inspection_suspended_until": "Das Enddatum darf nicht vor dem Startdatum liegen."})
        if bool(self.longitude) != bool(self.latitude):
            raise ValidationError("Bitte immer ein vollständiges LV95-Koordinatenpaar mit X und Y erfassen.")
        if self.longitude and not (2400000 <= self.longitude <= 2900000):
            raise ValidationError({"longitude": "Bitte einen gültigen LV95-X-Wert erfassen."})
        if self.latitude and not (1000000 <= self.latitude <= 1350000):
            raise ValidationError({"latitude": "Bitte einen gültigen LV95-Y-Wert erfassen."})

        inspector_fields = (
            "default_visual_inspector",
            "default_operational_inspector",
            "default_annual_inspector",
        )
        for field_name in inspector_fields:
            inspector = getattr(self, field_name)
            if inspector is None or inspector.is_superuser:
                continue
            profile = getattr(inspector, "profile", None)
            if not profile or profile.organization_id != self.organization_id or not profile.may_inspect:
                raise ValidationError({field_name: "Diese Person darf für diese Organisation keine Kontrollen durchführen."})

    def sync_location_from_lv95(self):
        if self.longitude is not None and self.latitude is not None:
            self.location = Point(float(self.longitude), float(self.latitude), srid=LV95_SRID)
        else:
            self.location = None

    def save(self, *args, **kwargs):
        self.sync_location_from_lv95()
        super().save(*args, **kwargs)

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
            .filter(is_active=True, public_visible=True, photo__isnull=False)
            .select_related("photo")
            .order_by("name")
            .first()
        )
        if equipment_with_photo:
            return equipment_with_photo.photo
        return None

    def get_default_inspector_for_inspection_type(self, inspection_type):
        if inspection_type == "visual":
            return self.default_visual_inspector
        if inspection_type == "operational":
            return self.default_operational_inspector
        if inspection_type == "annual":
            return self.default_annual_inspector
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
    source_note = models.TextField("Interner Quellen-/Bearbeitungshinweis", blank=True)
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
    tel_nr = models.CharField("Telefonnummer", max_length=80, blank=True)
    strasse = models.CharField("Strasse", max_length=80, blank=True)
    plz_ort = models.CharField("PLZ / Ort", max_length=80, blank=True)
    e_mail = models.EmailField("E-Mail", max_length=80, blank=True)
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
    supplier = models.ForeignKey(
        EquipmentSupplier,
        on_delete=models.SET_NULL,
        related_name="equipment",
        null=True,
        blank=True,
        verbose_name="Lieferant",
    )
    norm = models.CharField("Norm", max_length=200, blank=True)
    year_built = models.DateField("Baujahr / Baudatum", null=True, blank=True)
    build_date = models.DateField("Baudatum", null=True, blank=True)
    demolition_date = models.DateField("Abbruchjahr / Abbruchdatum", null=True, blank=True)
    renovation_type = models.CharField("Sanierungsart", max_length=20, choices=RENOVATION_TYPE_CHOICES, blank=True)
    recommended_renovation_year = models.PositiveIntegerField(
        "Empfohlenes Sanierungsjahr",
        null=True,
        blank=True,
        help_text="Vierstellige Jahreszahl. Historische Legacy-Werte sind zulässig.",
    )
    renovation_comment = models.CharField("Kommentar zur Sanierung", max_length=500, blank=True)
    not_to_inspect = models.BooleanField(
        "Nicht zu prüfen",
        default=False,
        help_text=(
            "Administrative Prüfausnahme. Das Spielgerät bleibt im Bestand, wird aber nicht "
            "in Kontrollprotokollen berücksichtigt. Dieses Feld wird durch die Organisation verwaltet."
        ),
    )
    not_to_inspect_reason = models.CharField("Grund nicht zu prüfen", max_length=500, blank=True)
    not_inspectable = models.BooleanField(
        "Nicht prüfbar",
        default=False,
        help_text=(
            "Das Spielgerät muss grundsätzlich geprüft werden, konnte aber bei einer Kontrolle "
            "nicht geprüft werden, z. B. weil es nicht zugänglich war."
        ),
    )
