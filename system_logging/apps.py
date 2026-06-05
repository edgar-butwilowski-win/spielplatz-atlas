# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.

from django.apps import AppConfig


class SystemLoggingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "system_logging"
    verbose_name = "Logging"
