# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

from django.urls import path

from . import views

app_name = "media_assets"

urlpatterns = [
    path("images/<int:image_id>/", views.image_content, name="image_content"),
    path("images/<int:image_id>/thumbnail/", views.image_thumbnail, name="image_thumbnail"),
]