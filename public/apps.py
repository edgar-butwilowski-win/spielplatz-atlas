# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

from django.apps import AppConfig


class PublicConfig(AppConfig):
    name = "public"

    def ready(self):
        from public import runtime_i18n
        runtime_i18n.install()