# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

from django.conf import settings
from django.contrib import admin
from django.urls import include, path

from internal import admin_csv_views

admin.site.site_header = "playsafeswiss"
admin.site.site_title = f"playsafeswiss{settings.ENVIRONMENT_TITLE_SUFFIX}"
admin.site.index_title = "Verwaltung und Stammdaten"

urlpatterns = [
    path(
        "admin/exports/inspections.csv/",
        admin.site.admin_view(admin_csv_views.inspections_admin_csv_export),
        name="admin_inspections_csv_export",
    ),
    path(
        "admin/exports/defects.csv/",
        admin.site.admin_view(admin_csv_views.defects_admin_csv_export),
        name="admin_defects_csv_export",
    ),
    path("admin/", admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    path("internal/", include("internal.urls")),
    path("internal/", include("notifications.urls")),
    path("media-assets/", include("media_assets.urls")),
    path("", include("accounts.urls")),
    path("", include("public.urls")),
]
