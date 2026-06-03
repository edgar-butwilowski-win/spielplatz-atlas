# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class InspectionCriterion(models.Model):
    MINIMUM_VISUAL = "visual"
    MINIMUM_OPERATIONAL = "operational"
    MINIMUM_ANNUAL = "annual"
    MINIMUM_INSPECTION_TYPE_CHOICES = [(MINIMUM_VISUAL, _("Visual routine inspection")), (MINIMUM_OPERATIONAL, _("Operational inspection")), (MINIMUM_ANNUAL, _("Annual main inspection"))]
    organization = models.ForeignKey("tenants.Organization", on_delete=models.CASCADE, related_name="inspection_criteria", null=True, blank=True, verbose_name="Organisation", help_text="Leer lassen für globale Anbieter-Standards.")
    area = models.CharField("Bereich", max_length=255, blank=True)
    title = models.CharField("Titel", max_length=255)
    inspection_text = models.TextField("Prüfhinweis", blank=True)
    maintenance_text = models.TextField("Wartungshinweis", blank=True)
    norm_reference = models.CharField("Norm-/Quellenhinweis", max_length=255, blank=True)
    minimum_inspection_type = models.CharField("Mindest-Kontrollart", max_length=30, choices=MINIMUM_INSPECTION_TYPE_CHOICES, default=MINIMUM_OPERATIONAL, help_text="Legt fest, ab welcher Kontrollart dieses Prüfkriterium berücksichtigt wird. Visuelle Kriterien erscheinen auch bei operativen und jährlichen Kontrollen.")
    is_standard = models.BooleanField("Standardkriterium", default=False)
    standard_version = models.CharField("Standardversion", max_length=100, blank=True)
    source_note = models.TextField("Quellen-/Bearbeitungshinweis", blank=True)
    is_locked = models.BooleanField("Gesperrt", default=False, help_text="Gesperrte globale Standards dürfen durch Organisationen nicht verändert werden.")
    is_active = models.BooleanField("Aktiv", default=True)
    created_at = models.DateTimeField("Erstellt am", auto_now_add=True)
    updated_at = models.DateTimeField("Aktualisiert am", auto_now=True)

    class Meta:
        ordering = ["area", "title"]
        verbose_name = "Prüfkriterium"
        verbose_name_plural = "Prüfkriterien"

    def __str__(self):
        return f"{self.area} – {self.title}" if self.area else self.title


class InspectionCriterionApplicability(models.Model):
    SCOPE_PLAYGROUND = "playground"
    SCOPE_EQUIPMENT = "equipment"
    SCOPE_SURFACE = "surface"
    SCOPE_ACCESSORY = "accessory"
    SCOPE_CHOICES = [(SCOPE_PLAYGROUND, _("General playground inspection")), (SCOPE_EQUIPMENT, _("Play equipment")), (SCOPE_SURFACE, _("Impact protection surface / ground")), (SCOPE_ACCESSORY, _("Additional equipment"))]
    criterion = models.ForeignKey(InspectionCriterion, on_delete=models.CASCADE, related_name="applicabilities", verbose_name="Prüfkriterium")
    scope_type = models.CharField("Geltungsbereich", max_length=30, choices=SCOPE_CHOICES)
    applies_to_all_equipment = models.BooleanField("Gilt für alle Spielgerätearten", default=False, help_text="Nur relevant, wenn der Geltungsbereich «Spielgerät» ist.")
    equipment_types = models.ManyToManyField("playgrounds.EquipmentType", blank=True, related_name="criterion_applicabilities", verbose_name="Nur für diese Spielgerätearten", help_text="Nur relevant, wenn der Geltungsbereich «Spielgerät» ist und das Prüfkriterium nicht für alle Spielgerätearten gilt.")

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
    TYPE_CHOICES = [(TYPE_VISUAL, _("Visual routine inspection")), (TYPE_OPERATIONAL, _("Operational inspection")), (TYPE_ANNUAL, _("Annual main inspection"))]
    RESULT_OK = "ok"
    RESULT_DEFECTS = "defects"
    RESULT_CHOICES = [(RESULT_OK, _("OK")), (RESULT_DEFECTS, _("Defects found"))]
    STATUS_DRAFT = "draft"
    STATUS_COMPLETED = "completed"
    STATUS_CHOICES = [(STATUS_DRAFT, _("In progress")), (STATUS_COMPLETED, _("Completed"))]
    playground = models.ForeignKey("playgrounds.Playground", on_delete=models.CASCADE, related_name="inspections", verbose_name="Spielplatz")
    inspection_type = models.CharField("Kontrollart", max_length=30, choices=TYPE_CHOICES, default=TYPE_VISUAL)
    inspected_at = models.DateField("Kontrolldatum", default=timezone.localdate)
    inspector = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="inspections", verbose_name="Kontrollperson")
    result = models.CharField("Ergebnis", max_length=30, choices=RESULT_CHOICES, default=RESULT_OK)
    status = models.CharField("Status", max_length=30, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    completed_at = models.DateTimeField("Abgeschlossen am", null=True, blank=True)
    completed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="completed_inspections", verbose_name="Abgeschlossen durch")
    notes = models.TextField("Notizen", blank=True)
    created_at = models.DateTimeField("Erstellt am", auto_now_add=True)
    updated_at = models.DateTimeField("Aktualisiert am", auto_now=True)

    class Meta:
        ordering = ["-inspected_at", "-created_at"]
        verbose_name = "Kontrolle"
        verbose_name_plural = "Kontrollen"

    def __str__(self):
        return f"{self.playground} – {self.get_inspection_type_display()} – {self.inspected_at}"


class InspectionRule(models.Model):
    DEFAULT_INTERVAL_DAYS = {Inspection.TYPE_VISUAL: 7, Inspection.TYPE_OPERATIONAL: 90, Inspection.TYPE_ANNUAL: 365}
    organization = models.ForeignKey("tenants.Organization", on_delete=models.CASCADE, related_name="inspection_rules", verbose_name="Organisation")
    inspection_type = models.CharField("Kontrollart", max_length=30, choices=Inspection.TYPE_CHOICES)
    interval_days = models.PositiveIntegerField("Intervall in Tagen", help_text="Intervall für die Kontrollplanung auf Basis von SN EN 1176/1177.")
    applies_to_all_playgrounds = models.BooleanField("Gilt für alle Spielplätze", default=True)
    is_active = models.BooleanField("Aktiv", default=True)
    created_at = models.DateTimeField("Erstellt am", auto_now_add=True)
    updated_at = models.DateTimeField("Aktualisiert am", auto_now=True)

    class Meta:
        unique_together = [("organization", "inspection_type")]
        ordering = ["organization__name", "inspection_type"]
        verbose_name = "Kontrollregel"
        verbose_name_plural = "Kontrollregeln"

    def __str__(self):
        return f"{self.organization} – {self.get_inspection_type_display()} alle {self.interval_days} Tage"

    @classmethod
    def get_default_interval_days(cls, inspection_type):
        return cls.DEFAULT_INTERVAL_DAYS.get(inspection_type, 365)


class InspectionTask(models.Model):
    STATUS_OPEN = "open"
    STATUS_PLANNED = "planned"
    STATUS_COMPLETED = "completed"
    STATUS_OVERDUE = "overdue"
    STATUS_SUSPENDED = "suspended"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [(STATUS_OPEN, _("Open")), (STATUS_PLANNED, _("Planned")), (STATUS_COMPLETED, _("Done")), (STATUS_OVERDUE, _("Overdue")), (STATUS_SUSPENDED, _("Suspended")), (STATUS_CANCELLED, _("Cancelled"))]
    SOURCE_AUTOMATIC = "automatic"
    SOURCE_MANUAL = "manual"
    SOURCE_CHOICES = [(SOURCE_AUTOMATIC, _("Automatic")), (SOURCE_MANUAL, _("Manual"))]
    organization = models.ForeignKey("tenants.Organization", on_delete=models.CASCADE, related_name="inspection_tasks", verbose_name="Organisation")
    playground = models.ForeignKey("playgrounds.Playground", on_delete=models.CASCADE, related_name="inspection_tasks", verbose_name="Spielplatz")
    inspection_type = models.CharField("Kontrollart", max_length=30, choices=Inspection.TYPE_CHOICES)
    due_date = models.DateField("Fällig am")
    planned_date = models.DateField("Geplant am", null=True, blank=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, related_name="assigned_inspection_tasks", null=True, blank=True, verbose_name="Zuständige Person")
    status = models.CharField("Status", max_length=30, choices=STATUS_CHOICES, default=STATUS_OPEN)
    source = models.CharField("Quelle", max_length=30, choices=SOURCE_CHOICES, default=SOURCE_AUTOMATIC)
    note = models.TextField("Interne Notiz", blank=True)
    created_from_inspection = models.ForeignKey(Inspection, on_delete=models.SET_NULL, related_name="created_tasks", null=True, blank=True, verbose_name="Aus Kontrolle erzeugt")
    completed_by_inspection = models.ForeignKey(Inspection, on_delete=models.SET_NULL, related_name="completed_tasks", null=True, blank=True, verbose_name="Durch Kontrolle abgeschlossen")
    generated_from_inspection = models.ForeignKey(Inspection, on_delete=models.SET_NULL, related_name="generated_tasks", null=True, blank=True, verbose_name="Aus Kontrolle erzeugt (alt)")
    created_at = models.DateTimeField("Erstellt am", auto_now_add=True)
    updated_at = models.DateTimeField("Aktualisiert am", auto_now=True)

    class Meta:
        ordering = ["due_date", "playground__name", "inspection_type"]
        verbose_name = "Kontrollauftrag"
        verbose_name_plural = "Kontrollaufträge"
        indexes = [models.Index(fields=["organization", "due_date", "status"]), models.Index(fields=["playground", "inspection_type", "due_date"])]

    def __str__(self):
        return f"{self.playground} – {self.get_inspection_type_display()} – {self.due_date}"

    def clean(self):
        super().clean()
        if self.playground_id and self.organization_id and self.playground.organization_id != self.organization_id:
            raise ValidationError("Der Spielplatz gehört nicht zur ausgewählten Organisation.")
        if self.assigned_to_id:
            profile = getattr(self.assigned_to, "profile", None)
            if not self.assigned_to.is_superuser and (not profile or profile.organization_id != self.organization_id or not profile.may_inspect):
                raise ValidationError({"assigned_to": "Diese Person darf für diese Organisation keine Kontrollen durchführen."})

    @property
    def effective_status(self):
        today = timezone.localdate()
        if self.status in [self.STATUS_COMPLETED, self.STATUS_CANCELLED]:
            return self.status
        if self.playground and self.playground.is_inspection_suspended:
            return self.STATUS_SUSPENDED
        if self.due_date < today:
            return self.STATUS_OVERDUE
        if self.planned_date:
            return self.STATUS_PLANNED
        return self.STATUS_OPEN

    def refresh_status(self, save=True):
        effective_status = self.effective_status
        if effective_status != self.status:
            self.status = effective_status
            if save:
                self.save(update_fields=["status", "updated_at"])
        return self.status

    @classmethod
    def calculate_due_date(cls, playground, inspection_type, reference_inspection=None):
        organization = playground.organization
        rule, _ = InspectionRule.objects.get_or_create(organization=organization, inspection_type=inspection_type, defaults={"interval_days": InspectionRule.get_default_interval_days(inspection_type), "applies_to_all_playgrounds": True, "is_active": True})
        if reference_inspection:
            base_date = reference_inspection.inspected_at
        else:
            latest_inspection = Inspection.objects.filter(playground=playground, inspection_type=inspection_type, status=Inspection.STATUS_COMPLETED).order_by("-inspected_at", "-completed_at", "-created_at").first()
            base_date = latest_inspection.inspected_at if latest_inspection else timezone.localdate()
        return base_date + timedelta(days=rule.interval_days)


class InspectionScope(models.Model):
    SCOPE_PLAYGROUND = "playground"
    SCOPE_EQUIPMENT = "equipment"
    SCOPE_SURFACE = "surface"
    SCOPE_ACCESSORY = "accessory"
    SCOPE_CHOICES = [(SCOPE_PLAYGROUND, _("General playground inspection")), (SCOPE_EQUIPMENT, _("Play equipment")), (SCOPE_SURFACE, _("Impact protection surface / ground")), (SCOPE_ACCESSORY, _("Additional equipment"))]
    inspection = models.ForeignKey(Inspection, on_delete=models.CASCADE, related_name="scopes", verbose_name="Kontrolle")
    scope_type = models.CharField("Prüfbereich", max_length=30, choices=SCOPE_CHOICES)
    equipment = models.ForeignKey("playgrounds.PlayEquipment", on_delete=models.CASCADE, related_name="inspection_scopes", null=True, blank=True, verbose_name="Spielgerät")
    surface = models.ForeignKey("playgrounds.PlaygroundSurface", on_delete=models.CASCADE, related_name="inspection_scopes", null=True, blank=True, verbose_name="Fallschutzfläche / Boden")
    accessory = models.ForeignKey("playgrounds.PlaygroundAccessory", on_delete=models.CASCADE, related_name="inspection_scopes", null=True, blank=True, verbose_name="Zusatzausstattung")
    label = models.CharField("Bezeichnung", max_length=255)
    sort_order = models.PositiveIntegerField("Sortierung", default=0)

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
    ANSWER_CHOICES = [(ANSWER_PENDING, _("Not checked yet")), (ANSWER_OK, _("OK")), (ANSWER_DEFECT, _("Defect")), (ANSWER_NOT_APPLICABLE, _("Not applicable"))]
    inspection = models.ForeignKey(Inspection, on_delete=models.CASCADE, related_name="answers", verbose_name="Kontrolle")
    scope = models.ForeignKey(InspectionScope, on_delete=models.CASCADE, related_name="answers", null=True, blank=True, verbose_name="Prüfbereich")
    criterion = models.ForeignKey(InspectionCriterion, on_delete=models.PROTECT, related_name="answers", verbose_name="Prüfkriterium")
    equipment = models.ForeignKey("playgrounds.PlayEquipment", on_delete=models.SET_NULL, related_name="inspection_answers", null=True, blank=True, verbose_name="Spielgerät")
    answer = models.CharField("Antwort", max_length=30, choices=ANSWER_CHOICES, default=ANSWER_PENDING)
    comment = models.TextField("Kommentar", blank=True)
    created_at = models.DateTimeField("Erstellt am", auto_now_add=True)
    updated_at = models.DateTimeField("Aktualisiert am", auto_now=True)

    class Meta:
        ordering = ["scope__sort_order", "criterion__area", "criterion__title"]
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
    STATUS_CHOICES = [(STATUS_OPEN, _("Open")), (STATUS_IN_PROGRESS, _("In progress")), (STATUS_PLANNED, _("Planned")), (STATUS_DONE, _("Resolved")), (STATUS_VERIFIED, _("Checked / completed"))]
    SOURCE_INSPECTION = "inspection"
    SOURCE_CITIZEN_REPORT = "citizen_report"
    SOURCE_INTERNAL_REPORT = "internal_report"
    SOURCE_MAINTENANCE = "maintenance"
    SOURCE_OTHER = "other"
    SOURCE_CHOICES = [(SOURCE_INSPECTION, _("Inspection")), (SOURCE_CITIZEN_REPORT, _("Citizen report")), (SOURCE_INTERNAL_REPORT, _("Internal report")), (SOURCE_MAINTENANCE, _("Maintenance / care")), (SOURCE_OTHER, _("Other"))]
    URGENCY_A = "a_immediate"
    URGENCY_B = "b_medium_term"
    URGENCY_CHOICES = [(URGENCY_A, _("A (immediate)")), (URGENCY_B, _("B (medium-term)"))]
    inspection = models.ForeignKey(Inspection, on_delete=models.SET_NULL, related_name="defects", null=True, blank=True, verbose_name="Kontrolle", help_text="Optional. Ein Mangel kann aus einer Kontrolle stammen, muss aber nicht.")
    inspection_answer = models.ForeignKey(InspectionAnswer, on_delete=models.SET_NULL, related_name="defects", null=True, blank=True, verbose_name="Prüfantwort", help_text="Optionale Prüfantwort, aus der dieser Mangel entstanden ist.")
    playground = models.ForeignKey("playgrounds.Playground", on_delete=models.CASCADE, related_name="defects", null=True, blank=True, verbose_name="Spielplatz")
    equipment = models.ForeignKey("playgrounds.PlayEquipment", on_delete=models.SET_NULL, related_name="defects", null=True, blank=True, verbose_name="Spielgerät")
    surface = models.ForeignKey("playgrounds.PlaygroundSurface", on_delete=models.SET_NULL, related_name="defects", null=True, blank=True, verbose_name="Fallschutzfläche / Boden")
    accessory = models.ForeignKey("playgrounds.PlaygroundAccessory", on_delete=models.SET_NULL, related_name="defects", null=True, blank=True, verbose_name="Zusatzausstattung")
    source_type = models.CharField("Quelle", max_length=30, choices=SOURCE_CHOICES, default=SOURCE_INTERNAL_REPORT)
    reported_at = models.DateTimeField("Gemeldet am", default=timezone.now)
    reported_by_text = models.CharField("Gemeldet durch", max_length=255, blank=True, help_text="Optionaler Freitext, z. B. Bürgerin, Hauswart, Werkhof.")
    internal_description = models.TextField("Interne Beschreibung")
    internal_note = models.TextField("Interne Notiz", blank=True)
    has_safety_risk = models.BooleanField("Sicherheitsrisiko", default=False)
    urgency = models.CharField("Dringlichkeit", max_length=30, choices=URGENCY_CHOICES, blank=True, help_text="Nur erfassen, wenn ein Sicherheitsrisiko besteht.")
    status = models.CharField("Status", max_length=30, choices=STATUS_CHOICES, default=STATUS_OPEN)
    public_visible = models.BooleanField("Öffentlich sichtbar", default=False)
    public_note = models.TextField("Öffentlicher Hinweis", blank=True)
    created_at = models.DateTimeField("Erstellt am", auto_now_add=True)
    updated_at = models.DateTimeField("Aktualisiert am", auto_now=True)

    class Meta:
        ordering = ["-has_safety_risk", "-created_at"]
        verbose_name = "Mangel"
        verbose_name_plural = "Mängel"

    def __str__(self):
        target = self.playground or self.equipment or self.surface or self.accessory
        return f"Mangel: {target}" if target else f"Mangel #{self.id}"

    def _maintenance_action_list(self):
        if hasattr(self, "_prefetched_objects_cache") and "maintenance_actions" in self._prefetched_objects_cache:
            return list(self._prefetched_objects_cache["maintenance_actions"])
        if not self.pk:
            return []
        return list(self.maintenance_actions.select_related("assigned_to").all())

    @property
    def active_maintenance_action(self):
        active_statuses = {MaintenanceAction.STATUS_PLANNED, MaintenanceAction.STATUS_IN_PROGRESS}
        actions = [action for action in self._maintenance_action_list() if action.status in active_statuses]
        actions.sort(key=lambda action: (action.planned_date is None, action.planned_date or timezone.localdate(), -action.created_at.timestamp() if action.created_at else 0))
        return actions[0] if actions else None

    @property
    def planned_resolution_date(self):
        action = self.active_maintenance_action
        return action.planned_date if action else None

    @property
    def assigned_to_for_resolution(self):
        action = self.active_maintenance_action
        return action.assigned_to if action else None

    def clean(self):
        super().clean()
        if self.has_safety_risk and not self.urgency:
            self.urgency = self.URGENCY_A
        if not self.has_safety_risk:
            self.urgency = ""

    def save(self, *args, **kwargs):
        if self.has_safety_risk and not self.urgency:
            self.urgency = self.URGENCY_A
        if not self.has_safety_risk:
            self.urgency = ""
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
            return _("A defect with a safety risk is known for this play equipment. Please observe the notices on site.")
        return _("A defect is known for this play equipment. The defect does not pose a safety risk. Repair is planned.")


class MaintenanceAction(models.Model):
    STATUS_PLANNED = "planned"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_DONE = "done"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [(STATUS_PLANNED, _("Planned")), (STATUS_IN_PROGRESS, _("In progress")), (STATUS_DONE, _("Completed")), (STATUS_CANCELLED, _("Cancelled"))]
    defect = models.ForeignKey(Defect, on_delete=models.CASCADE, related_name="maintenance_actions", verbose_name="Mangel")
    title = models.CharField("Titel", max_length=255)
    description = models.TextField("Beschreibung", blank=True)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="assigned_maintenance_actions", verbose_name="Zuständige Person")
    planned_date = models.DateField("Geplant am", null=True, blank=True)
    completed_date = models.DateField("Abgeschlossen am", null=True, blank=True)
    status = models.CharField("Status", max_length=30, choices=STATUS_CHOICES, default=STATUS_PLANNED)
    public_visible = models.BooleanField("Öffentlich sichtbar", default=False)
    created_at = models.DateTimeField("Erstellt am", auto_now_add=True)
    updated_at = models.DateTimeField("Aktualisiert am", auto_now=True)

    class Meta:
        ordering = ["planned_date", "-created_at"]
        verbose_name = "Instandhaltungsmassnahme"
        verbose_name_plural = "Instandhaltungsmassnahmen"

    def __str__(self):
        return self.title


class DefectImage(models.Model):
    defect = models.ForeignKey(Defect, on_delete=models.CASCADE, related_name="images", verbose_name="Mangel")
    image = models.ForeignKey("media_assets.ImageAsset", on_delete=models.CASCADE, related_name="defect_images", verbose_name="Bild")
    caption = models.CharField("Bildlegende", max_length=255, blank=True)
    public_visible = models.BooleanField("Öffentlich sichtbar", default=False)
    created_at = models.DateTimeField("Erstellt am", auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name = "Mangelbild"
        verbose_name_plural = "Mangelbilder"

    def __str__(self):
        return self.caption or str(self.image)
