# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

from django.apps import AppConfig


class InspectionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "inspections"
    verbose_name = "Kontrollen"

    def import_models(self):
        super().import_models()
        import inspections.work_orders  # noqa: F401

    def ready(self):
        import inspections.signals  # noqa: F401
