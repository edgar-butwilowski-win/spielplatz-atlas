# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

from django.contrib import admin

from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "organization",
        "is_active_for_organization",
        "is_org_admin",
        "can_view_internal",
        "can_inspect",
        "can_maintain",
    )
    list_filter = (
        "organization",
        "is_active_for_organization",
        "is_org_admin",
        "can_view_internal",
        "can_inspect",
        "can_maintain",
    )
    search_fields = (
        "user__username",
        "user__email",
        "user__first_name",
        "user__last_name",
        "organization__name",
    )
    autocomplete_fields = (
        "user",
        "organization",
    )