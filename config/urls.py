# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

from django.contrib import admin
from django.urls import include, path

admin.site.site_header = "playsafeswiss"
admin.site.site_title = "playsafeswiss"
admin.site.index_title = "Verwaltung und Stammdaten"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("internal/", include("internal.urls")),
    path("internal/", include("notifications.urls")),
    path("media-assets/", include("media_assets.urls")),
    path("", include("accounts.urls")),
    path("", include("public.urls")),
]
