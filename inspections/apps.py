from django.apps import AppConfig


class InspectionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "inspections"
    verbose_name = "Kontrollen"

    def ready(self):
        self.register_defect_urgency_field()

        import inspections.signals  # noqa: F401

    def register_defect_urgency_field(self):
        from django.db import models

        from inspections.models import Defect

        if getattr(Defect, "_urgency_field_registered", False):
            return

        Defect.URGENCY_A = "a_immediate"
        Defect.URGENCY_B = "b_medium_term"
        Defect.URGENCY_CHOICES = [
            (Defect.URGENCY_A, "A (sofort)"),
            (Defect.URGENCY_B, "B (mittelfristig)"),
        ]

        if not hasattr(Defect, "urgency"):
            Defect.add_to_class(
                "urgency",
                models.CharField(
                    "Dringlichkeit",
                    max_length=30,
                    choices=Defect.URGENCY_CHOICES,
                    blank=True,
                    help_text="Nur erfassen, wenn ein Sicherheitsrisiko besteht.",
                ),
            )

        Defect._urgency_field_registered = True
