from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class WorkOrder(models.Model):
    TYPE_INSPECTION = "inspection"
    TYPE_DEFECT_REPAIR = "defect_repair"
    TYPE_RENOVATION = "renovation"
    TYPE_OTHER = "other"

    TYPE_CHOICES = [
        (TYPE_INSPECTION, _("Inspection")),
        (TYPE_DEFECT_REPAIR, _("Defect repair")),
        (TYPE_RENOVATION, _("Renovation")),
        (TYPE_OTHER, _("Other")),
    ]

    STATUS_OPEN = "open"
    STATUS_PLANNED = "planned"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_DONE = "done"
    STATUS_CANCELLED = "cancelled"
    STATUS_SUSPENDED = "suspended"

    STATUS_CHOICES = [
        (STATUS_OPEN, _("Open")),
        (STATUS_PLANNED, _("Planned")),
        (STATUS_IN_PROGRESS, _("In progress")),
        (STATUS_DONE, _("Completed")),
        (STATUS_CANCELLED, _("Cancelled")),
        (STATUS_SUSPENDED, _("Suspended")),
    ]

    PRIORITY_LOW = "low"
    PRIORITY_NORMAL = "normal"
    PRIORITY_HIGH = "high"
    PRIORITY_URGENT = "urgent"

    PRIORITY_CHOICES = [
        (PRIORITY_LOW, _("Low")),
        (PRIORITY_NORMAL, _("Normal")),
        (PRIORITY_HIGH, _("High")),
        (PRIORITY_URGENT, _("Urgent")),
    ]

    SOURCE_MANUAL = "manual"
    SOURCE_AUTOMATIC = "automatic"
    SOURCE_EQUIPMENT_RENOVATION = "equipment_renovation"
    SOURCE_INSPECTION = "inspection"
    SOURCE_DEFECT = "defect"

    SOURCE_CHOICES = [
        (SOURCE_MANUAL, _("Manual")),
        (SOURCE_AUTOMATIC, _("Automatic")),
        (SOURCE_EQUIPMENT_RENOVATION, _("Equipment renovation")),
        (SOURCE_INSPECTION, _("Inspection")),
        (SOURCE_DEFECT, _("Defect")),
    ]

    organization = models.ForeignKey(
        "tenants.Organization",
        on_delete=models.CASCADE,
        related_name="work_orders",
        verbose_name="Organisation",
    )
    playground = models.ForeignKey(
        "playgrounds.Playground",
        on_delete=models.CASCADE,
        related_name="work_orders",
        verbose_name="Spielplatz",
    )

    title = models.CharField("Titel", max_length=255)
    description = models.TextField("Beschreibung", blank=True)
    order_type = models.CharField("Auftragsart", max_length=30, choices=TYPE_CHOICES, default=TYPE_OTHER)
    status = models.CharField("Status", max_length=30, choices=STATUS_CHOICES, default=STATUS_OPEN)
    priority = models.CharField("Priorität", max_length=30, choices=PRIORITY_CHOICES, default=PRIORITY_NORMAL)
    source = models.CharField("Quelle", max_length=40, choices=SOURCE_CHOICES, default=SOURCE_MANUAL)

    equipment = models.ForeignKey(
        "playgrounds.PlayEquipment",
        on_delete=models.SET_NULL,
        related_name="work_orders",
        null=True,
        blank=True,
        verbose_name="Spielgerät",
    )
    surface = models.ForeignKey(
        "playgrounds.PlaygroundSurface",
        on_delete=models.SET_NULL,
        related_name="work_orders",
        null=True,
        blank=True,
        verbose_name="Fallschutzfläche / Boden",
    )
    accessory = models.ForeignKey(
        "playgrounds.PlaygroundAccessory",
        on_delete=models.SET_NULL,
        related_name="work_orders",
        null=True,
        blank=True,
        verbose_name="Zusatzausstattung",
    )

    inspection = models.ForeignKey(
        "inspections.Inspection",
        on_delete=models.SET_NULL,
        related_name="work_orders",
        null=True,
        blank=True,
        verbose_name="Kontrolle",
    )
    inspection_task = models.ForeignKey(
        "inspections.InspectionTask",
        on_delete=models.SET_NULL,
        related_name="work_orders",
        null=True,
        blank=True,
        verbose_name="Kontrollauftrag",
    )
    defect = models.ForeignKey(
        "inspections.Defect",
        on_delete=models.SET_NULL,
        related_name="work_orders",
        null=True,
        blank=True,
        verbose_name="Mangel",
    )
    maintenance_action = models.ForeignKey(
        "inspections.MaintenanceAction",
        on_delete=models.SET_NULL,
        related_name="work_orders",
        null=True,
        blank=True,
        verbose_name="Instandhaltungsmassnahme",
    )

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="assigned_work_orders",
        null=True,
        blank=True,
        verbose_name="Zuständige Person",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_work_orders",
        null=True,
        blank=True,
        verbose_name="Erstellt durch",
    )

    due_date = models.DateField("Fällig am", null=True, blank=True)
    planned_date = models.DateField("Geplant am", null=True, blank=True)
    completed_at = models.DateTimeField("Abgeschlossen am", null=True, blank=True)

    renovation_type = models.CharField(
        "Sanierungsart",
        max_length=20,
        choices=[("total", "Totalsanierung"), ("partial", "Teilsanierung")],
        blank=True,
    )
    renovation_year = models.PositiveIntegerField("Empfohlenes Sanierungsjahr", null=True, blank=True)
    estimated_costs = models.DecimalField("Kostenschätzung", max_digits=12, decimal_places=2, null=True, blank=True)
    credit_name = models.CharField("Sammelkredit", max_length=255, blank=True)
    internal_note = models.TextField("Interne Notiz", blank=True)
    public_visible = models.BooleanField("Öffentlich sichtbar", default=False)

    created_at = models.DateTimeField("Erstellt am", auto_now_add=True)
    updated_at = models.DateTimeField("Aktualisiert am", auto_now=True)

    class Meta:
        ordering = ["due_date", "planned_date", "playground__name", "title"]
        verbose_name = "Auftrag"
        verbose_name_plural = "Aufträge"
        indexes = [
            models.Index(fields=["organization", "order_type", "status"], name="inspections_organiz_e0d7d5_idx"),
            models.Index(fields=["organization", "renovation_year", "credit_name"], name="inspections_organiz_74e71c_idx"),
            models.Index(fields=["equipment", "order_type", "status"], name="inspections_equipme_c8aeca_idx"),
        ]

    def __str__(self):
        return self.title

    @property
    def is_closed(self):
        return self.status in {self.STATUS_DONE, self.STATUS_CANCELLED}

    def clean(self):
        super().clean()
        if self.equipment_id and self.playground_id and self.equipment.playground_id != self.playground_id:
            raise ValidationError({"equipment": "Das Spielgerät gehört nicht zum ausgewählten Spielplatz."})
        if self.surface_id and self.playground_id and self.surface.playground_id != self.playground_id:
            raise ValidationError({"surface": "Die Fallschutzfläche gehört nicht zum ausgewählten Spielplatz."})
        if self.accessory_id and self.playground_id and self.accessory.playground_id != self.playground_id:
            raise ValidationError({"accessory": "Die Zusatzausstattung gehört nicht zum ausgewählten Spielplatz."})
        if self.assigned_to_id:
            profile = getattr(self.assigned_to, "profile", None)
            if not self.assigned_to.is_superuser and (not profile or profile.organization_id != self.organization_id or not profile.may_manage_organization):
                raise ValidationError({"assigned_to": "Diese Person darf für diese Organisation keine Aufträge verwalten."})

    def save(self, *args, **kwargs):
        if self.equipment_id:
            self.playground = self.equipment.playground
        if self.surface_id and not self.playground_id:
            self.playground = self.surface.playground
        if self.accessory_id and not self.playground_id:
            self.playground = self.accessory.playground
        if self.playground_id and not self.organization_id:
            self.organization = self.playground.organization
        if self.status == self.STATUS_DONE and self.completed_at is None:
            self.completed_at = timezone.now()
        if self.status != self.STATUS_DONE:
            self.completed_at = None
        super().save(*args, **kwargs)
