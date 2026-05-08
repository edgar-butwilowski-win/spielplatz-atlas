# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

from django.contrib import admin

from .models import ImageAsset


@admin.register(ImageAsset)
class ImageAssetAdmin(admin.ModelAdmin):
    list_display = (
        "original_filename",
        "organization",
        "mime_type",
        "size_bytes",
        "public_visible",
        "created_at",
    )
    list_filter = ("organization", "mime_type", "public_visible")
    search_fields = ("original_filename", "sha256")
    readonly_fields = ("sha256", "size_bytes", "width", "height", "created_at")