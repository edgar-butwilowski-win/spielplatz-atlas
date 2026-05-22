# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

from django.apps import AppConfig


class PlaygroundsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "playgrounds"

    def ready(self):
        # Ergänzende Admin-Registrierungen in separaten Dateien laden.
        from . import admin_documents  # noqa: F401
        from . import quartier_admin  # noqa: F401
