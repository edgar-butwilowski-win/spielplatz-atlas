# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

from django.conf import settings
from django.db import models
from django.utils import timezone


class InspectionCriterion(models.Model):
    MINIMUM_VISUAL = "visual"
    MINIMUM_OPERATIONAL = "operational"
    MINIMUM_ANNUAL = "annual"

    MINIMUM_INSPECTION_TYPE_CHOICES = [
        (MINIMUM_VISUAL, "Visuelle Routinekontrolle"),
        (MINIMUM_OPERATIONAL, "Operative Kontrolle"),
        (MINIMUM_ANNUAL, "Jährliche Hauptinspektion"),
    ]

    organization = models.ForeignKey(
        "tenants.Organization",
        on_delete=models.CASCADE,
        related_name="inspection_criteria",
        null=True,
        blank=True,
        verbose_name="Organisation",
        help_text="Leer lassen für globale Anbieter-Standards.",
    )

    area = models.CharField(
        "Bereich",
        max_length=255,
        blank=True,
    )

    title = models.CharField(
        "Titel",
        max_length=255,
    )

    inspection_text = models.TextField(
        "Prüfhinweis",
        blank=True,
    )

    maintenance_text = models.TextField(
        "Wartungshinweis",
        blank=True,
    )

    norm_reference = models.CharField(
        "Norm-/Quellenhinweis",
        max_length=255,
        blank=True,
    )

    minimum_inspection_type = models.CharField(
        "Mindest-Kontrollart",
        max_length=30,
        choices=MINIMUM_INSPECTION_TYPE_CHOICES,
        default=MINIMUM_OPERATIONAL,
        help_text=(
            "Legt fest, ab welcher Kontrollart dieses Prüfkriterium berücksichtigt wird. "
            "Visuelle Kriterien erscheinen auch bei operativen und jährlichen Kontrollen."
        ),
    )

    is_standard = models.BooleanField(
        "Standardkriterium",
        default=False,
    )

    standard_version = models.CharField(
        "Standardversion",
        max_length=100,
        blank=True,
    )

    source_note = models.TextField(
        "Quellen-/Bearbeitungshinweis",
        blank=True,
    )

    is_locked = models.BooleanField(
        "Gesperrt",
        default=False,
        help_text="Gesperrte globale Standards dürfen durch Organisationen nicht verändert werden.",
    )

    is_active = models.BooleanField(
        "Aktiv",
        default=True,
    )

    created_at = models.DateTimeField(
        "Erstellt am",
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        "Aktualisiert am",
        auto_now=True,
    )

    class Meta:
        ordering = ["area", "title"]
        verbose_name = "Prüfkriterium"
        verbose_name_plural = "Prüfkriterien"

    def __str__(self):
        if self.area:
            return f"{self.area} – {self.title}"

        return self.title


class InspectionCriterionApplicability(models.Model):
    SCOPE_PLAYGROUND = "playground"
    SCOPE_EQUIPMENT = "equipment"
    SCOPE_SURFACE = "surface"
    SCOPE_ACCESSORY = "accessory"

    SCOPE_CHOICES = [
        (SCOPE_PLAYGROUND, "Allgemeine Spielplatzprüfung"),
        (SCOPE_EQUIPMENT, "Spielgerät"),
        (SCOPE_SURFACE, "Fallschutzfläche / Boden"),
        (SCOPE_ACCESSORY, "Zusatzausstattung"),
    ]

    criterion = models.ForeignKey(
        InspectionCriterion,
        on_delete=models.CASCADE,
        related_name="applicabilities",
        verbose_name="Prüfkriterium",
    )

    scope_type = models.CharField(
        "Geltungsbereich",
        max_length=30,
        choices=SCOPE_CHOICES,
    )

    applies_to_all_equipment = models.BooleanField(
        "Gilt für alle Spielgerätearten",
        default=False,
        help_text="Nur relevant, wenn der Geltungsbereich «Spielgerät» ist.",
    )

    equipment_types = models.ManyToManyField(
        "playgrounds.EquipmentType",
        blank=True,
        related_name="criterion_applicabilities",
        verbose_name="Nur für diese Spielgerätearten",
        help_text=(
            "Nur relevant, wenn der Geltungsbereich «Spielgerät» ist "
            "und das Prüfkriterium nicht für alle Spielgerätearten gilt."
        ),
    )

    class Meta:
        unique_together = [("criterion", "scope_type")]
        ordering = ["criterion__area", "criterion__title", "scope_type"]
        verbose_name = "Anwendbarkeit"
        verbose_name_plural = "Anwendbarkeiten"

    def __str__(self):
        return f"{self.criterion} – {self.get_scope_type_display()}"


class Inspection(models.Model):
    TYPE_VISUAL = "visual"
    TYPE_OPERATIONAL = "operational"
    TYPE_ANNUAL = "annual"

    TYPE_CHOICES = [
        (TYPE_VISUAL, "Visuelle Routinekontrolle"),
        (TYPE_OPERATIONAL, "Operative Kontrolle"),
        (TYPE_ANNUAL, "Jährliche Hauptinspektion"),
    ]

    RESULT_OK = "ok"
    RESULT_DEFECTS = "defects"

    RESULT_CHOICES = [
        (RESULT_OK, "In Ordnung"),
        (RESULT_DEFECTS, "Mängel festgestellt"),
    ]

    STATUS_DRAFT = "draft"
    STATUS_COMPLETED = "completed"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "In Bearbeitung"),
        (STATUS_COMPLETED, "Abgeschlossen"),
    ]

    playground = models.ForeignKey(
        "playgrounds.Playground",
        on_delete=models.CASCADE,
        related_name="inspections",
        verbose_name="Spielplatz",
    )

    inspection_type = models.CharField(
        "Kontrollart",
        max_length=30,
        choices=TYPE_CHOICES,
        default=TYPE_VISUAL,
    )

    inspected_at = models.DateField(
        "Kontrolldatum",
        default=timezone.localdate,
    )

    inspector = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inspections",
        verbose_name="Kontrollperson",
    )

    result = models.CharField(
        "Ergebnis",
        max_length=30,
        choices=RESULT_CHOICES,
        default=RESULT_OK,
    )

    status = models.CharField(
        "Status",
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
    )

    completed_at = models.DateTimeField(
        "Abgeschlossen am",
        null=True,
        blank=True,
    )

    completed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="completed_inspections",
        verbose_name="Abgeschlossen durch",
    )

    notes = models.TextField(
        "Notizen",
        blank=True,
    )

    created_at = models.DateTimeField(
        "Erstellt am",
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        "Aktualisiert am",
        auto_now=True,
    )

    class Meta:
        ordering = ["-inspected_at", "-created_at"]
        verbose_name = "Kontrolle"
        verbose_name_plural = "Kontrollen"

    def __str__(self):
        return f"{self.playground} – {self.get_inspection_type_display()} – {self.inspected_at}"


class InspectionScope(models.Model):
    SCOPE_PLAYGROUND = "playground"
    SCOPE_EQUIPMENT = "equipment"
    SCOPE_SURFACE = "surface"
    SCOPE_ACCESSORY = "accessory"

    SCOPE_CHOICES = [
        (SCOPE_PLAYGROUND, "Allgemeine Spielplatzprüfung"),
        (SCOPE_EQUIPMENT, "Spielgerät"),
        (SCOPE_SURFACE, "Fallschutzfläche / Boden"),
        (SCOPE_ACCESSORY, "Zusatzausstattung"),
    ]

    inspection = models.ForeignKey(
        Inspection,
        on_delete=models.CASCADE,
        related_name="scopes",
        verbose_name="Kontrolle",
    )

    scope_type = models.CharField(
        "Prüfbereich",
        max_length=30,
        choices=SCOPE_CHOICES,
    )

    equipment = models.ForeignKey(
        "playgrounds.PlayEquipment",
        on_delete=models.CASCADE,
        related_name="inspection_scopes",
        null=True,
        blank=True,
        verbose_name="Spielgerät",
    )

    surface = models.ForeignKey(
        "playgrounds.PlaygroundSurface",
        on_delete=models.CASCADE,
        related_name="inspection_scopes",
        null=True,
        blank=True,
        verbose_name="Fallschutzfläche / Boden",
    )

    accessory = models.ForeignKey(
        "playgrounds.PlaygroundAccessory",
        on_delete=models.CASCADE,
        related_name="inspection_scopes",
        null=True,
        blank=True,
        verbose_name="Zusatzausstattung",
    )

    label = models.CharField(
        "Bezeichnung",
        max_length=255,
    )

    sort_order = models.PositiveIntegerField(
        "Sortierung",
        default=0,
    )

    class Meta:
        ordering = ["sort_order", "label"]
        verbose_name = "Prüfbereich"
        verbose_name_plural = "Prüfbereiche"

    def __str__(self):
        return f"{self.inspection} – {self.label}"


class InspectionAnswer(models.Model):
    ANSWER_PENDING = "pending"
    ANSWER_OK = "ok"
    ANSWER_DEFECT = "defect"
    ANSWER_NOT_APPLICABLE = "not_applicable"

    ANSWER_CHOICES = [
        (ANSWER_PENDING, "Noch nicht geprüft"),
        (ANSWER_OK, "In Ordnung"),
        (ANSWER_DEFECT, "Mangel"),
        (ANSWER_NOT_APPLICABLE, "Nicht anwendbar"),
    ]

    inspection = models.ForeignKey(
        Inspection,
        on_delete=models.CASCADE,
        related_name="answers",
        verbose_name="Kontrolle",
    )

    scope = models.ForeignKey(
        InspectionScope,
        on_delete=models.CASCADE,
        related_name="answers",
        null=True,
        blank=True,
        verbose_name="Prüfbereich",
    )

    criterion = models.ForeignKey(
        InspectionCriterion,
        on_delete=models.PROTECT,
        related_name="answers",
        verbose_name="Prüfkriterium",
    )

    equipment = models.ForeignKey(
        "playgrounds.PlayEquipment",
        on_delete=models.SET_NULL,
        related_name="inspection_answers",
        null=True,
        blank=True,
        verbose_name="Spielgerät",
    )

    answer = models.CharField(
        "Antwort",
        max_length=30,
        choices=ANSWER_CHOICES,
        default=ANSWER_PENDING,
    )

    comment = models.TextField(
        "Kommentar",
        blank=True,
    )

    created_at = models.DateTimeField(
        "Erstellt am",
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        "Aktualisiert am",
        auto_now=True,
    )

    class Meta:
        ordering = [
            "scope__sort_order",
            "criterion__area",
            "criterion__title",
        ]
        unique_together = [("inspection", "scope", "criterion")]
        verbose_name = "Prüfantwort"
        verbose_name_plural = "Prüfantworten"

    def __str__(self):
        return f"{self.inspection} – {self.criterion} – {self.get_answer_display()}"


class Defect(models.Model):
    STATUS_OPEN = "open"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_PLANNED = "planned"
    STATUS_DONE = "done"
    STATUS_VERIFIED = "verified"

    STATUS_CHOICES = [
        (STATUS_OPEN, "Offen"),
        (STATUS_IN_PROGRESS, "In Bearbeitung"),
        (STATUS_PLANNED, "Geplant"),
        (STATUS_DONE, "Behoben"),
        (STATUS_VERIFIED, "Geprüft / abgeschlossen"),
    ]

    SOURCE_INSPECTION = "inspection"
    SOURCE_CITIZEN_REPORT = "citizen_report"
    SOURCE_INTERNAL_REPORT = "internal_report"
    SOURCE_MAINTENANCE = "maintenance"
    SOURCE_OTHER = "other"

    SOURCE_CHOICES = [
        (SOURCE_INSPECTION, "Kontrolle"),
        (SOURCE_CITIZEN_REPORT, "Bürgermeldung"),
        (SOURCE_INTERNAL_REPORT, "Interne Meldung"),
        (SOURCE_MAINTENANCE, "Unterhalt / Pflege"),
        (SOURCE_OTHER, "Sonstiges"),
    ]

    inspection = models.ForeignKey(
        Inspection,
        on_delete=models.SET_NULL,
        related_name="defects",
        null=True,
        blank=True,
        verbose_name="Kontrolle",
        help_text="Optional. Ein Mangel kann aus einer Kontrolle stammen, muss aber nicht.",
    )

    inspection_answer = models.ForeignKey(
        InspectionAnswer,
        on_delete=models.SET_NULL,
        related_name="defects",
        null=True,
        blank=True,
        verbose_name="Prüfantwort",
        help_text="Optionale Prüfantwort, aus der dieser Mangel entstanden ist.",
    )

    playground = models.ForeignKey(
        "playgrounds.Playground",
        on_delete=models.CASCADE,
        related_name="defects",
        null=True,
        blank=True,
        verbose_name="Spielplatz",
    )

    equipment = models.ForeignKey(
        "playgrounds.PlayEquipment",
        on_delete=models.SET_NULL,
        related_name="defects",
        null=True,
        blank=True,
        verbose_name="Spielgerät",
    )

    surface = models.ForeignKey(
        "playgrounds.PlaygroundSurface",
        on_delete=models.SET_NULL,
        related_name="defects",
        null=True,
        blank=True,
        verbose_name="Fallschutzfläche / Boden",
    )

    accessory = models.ForeignKey(
        "playgrounds.PlaygroundAccessory",
        on_delete=models.SET_NULL,
        related_name="defects",
        null=True,
        blank=True,
        verbose_name="Zusatzausstattung",
    )

    source_type = models.CharField(
        "Quelle",
        max_length=30,
        choices=SOURCE_CHOICES,
        default=SOURCE_INTERNAL_REPORT,
    )

    reported_at = models.DateTimeField(
        "Gemeldet am",
        default=timezone.now,
    )

    reported_by_text = models.CharField(
        "Gemeldet durch",
        max_length=255,
        blank=True,
        help_text="Optionaler Freitext, z. B. Bürgerin, Hauswart, Werkhof.",
    )

    internal_description = models.TextField(
        "Interne Beschreibung",
    )

    internal_note = models.TextField(
        "Interne Notiz",
        blank=True,
    )

    has_safety_risk = models.BooleanField(
        "Sicherheitsrisiko",
        default=False,
    )

    status = models.CharField(
        "Status",
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_OPEN,
    )

    planned_resolution_date = models.DateField(
        "Geplante Behebung",
        null=True,
        blank=True,
    )

    public_visible = models.BooleanField(
        "Öffentlich sichtbar",
        default=False,
    )

    public_note = models.TextField(
        "Öffentlicher Hinweis",
        blank=True,
    )

    created_at = models.DateTimeField(
        "Erstellt am",
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        "Aktualisiert am",
        auto_now=True,
    )

    class Meta:
        ordering = ["-has_safety_risk", "planned_resolution_date", "-created_at"]
        verbose_name = "Mangel"
        verbose_name_plural = "Mängel"

    def __str__(self):
        target = self.playground or self.equipment or self.surface or self.accessory

        if target:
            return f"Mangel: {target}"

        return f"Mangel #{self.id}"

    def save(self, *args, **kwargs):
        if self.inspection_answer_id:
            if not self.inspection_id:
                self.inspection = self.inspection_answer.inspection

            if not self.playground_id:
                self.playground = self.inspection_answer.inspection.playground

        if self.inspection_id and not self.playground_id:
            self.playground = self.inspection.playground

        if self.equipment_id and not self.playground_id:
            self.playground = self.equipment.playground

        if self.surface_id and not self.playground_id:
            self.playground = self.surface.playground

        if self.accessory_id and not self.playground_id:
            self.playground = self.accessory.playground

        if self.inspection_id and self.source_type == self.SOURCE_INTERNAL_REPORT:
            self.source_type = self.SOURCE_INSPECTION

        super().save(*args, **kwargs)

    def get_public_message(self):
        if self.has_safety_risk:
            return (
                "An diesem Spielgerät ist ein Mangel mit Sicherheitsrisiko bekannt. "
                "Bitte beachten Sie die Hinweise vor Ort."
            )

        return (
            "An diesem Spielgerät ist ein Mangel bekannt. "
            "Der Mangel stellt kein Sicherheitsrisiko dar. "
            "Die Instandsetzung ist geplant."
        )


class MaintenanceAction(models.Model):
    STATUS_PLANNED = "planned"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_DONE = "done"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_PLANNED, "Geplant"),
        (STATUS_IN_PROGRESS, "In Bearbeitung"),
        (STATUS_DONE, "Abgeschlossen"),
        (STATUS_CANCELLED, "Abgebrochen"),
    ]

    defect = models.ForeignKey(
        Defect,
        on_delete=models.CASCADE,
        related_name="maintenance_actions",
        verbose_name="Mangel",
    )

    title = models.CharField(
        "Titel",
        max_length=255,
    )

    description = models.TextField(
        "Beschreibung",
        blank=True,
    )

    planned_date = models.DateField(
        "Geplant am",
        null=True,
        blank=True,
    )

    completed_date = models.DateField(
        "Abgeschlossen am",
        null=True,
        blank=True,
    )

    status = models.CharField(
        "Status",
        max_length=30,
        choices=STATUS_CHOICES,
        default=STATUS_PLANNED,
    )

    public_visible = models.BooleanField(
        "Öffentlich sichtbar",
        default=False,
    )

    created_at = models.DateTimeField(
        "Erstellt am",
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        "Aktualisiert am",
        auto_now=True,
    )

    class Meta:
        ordering = ["planned_date", "-created_at"]
        verbose_name = "Instandhaltungsmassnahme"
        verbose_name_plural = "Instandhaltungsmassnahmen"

    def __str__(self):
        return self.title


class DefectImage(models.Model):
    defect = models.ForeignKey(
        Defect,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name="Mangel",
    )

    image = models.ForeignKey(
        "media_assets.ImageAsset",
        on_delete=models.CASCADE,
        related_name="defect_images",
        verbose_name="Bild",
    )

    caption = models.CharField(
        "Bildlegende",
        max_length=255,
        blank=True,
    )

    public_visible = models.BooleanField(
        "Öffentlich sichtbar",
        default=False,
    )

    created_at = models.DateTimeField(
        "Erstellt am",
        auto_now_add=True,
    )

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Mangelbild"
        verbose_name_plural = "Mangelbilder"

    def __str__(self):
        return self.caption or str(self.image)
