# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.

from django.contrib import admin
from django.core.paginator import Paginator

from .models import LogEntry


class NewestLogEntryPaginator(Paginator):
    @property
    def count(self):
        return min(super().count, 100)


@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = ("created_at", "level", "logger_name", "short_message", "module", "function_name", "line_number")
    list_filter = ("level", "logger_name", "created_at")
    search_fields = ("message", "logger_name", "module", "function_name", "pathname", "exception_text")
    readonly_fields = (
        "created_at",
        "level",
        "logger_name",
        "message",
        "module",
        "function_name",
        "line_number",
        "pathname",
        "process_id",
        "thread_id",
        "exception_text",
    )
    ordering = ("-created_at",)
    list_per_page = 100
    show_full_result_count = False
    paginator = NewestLogEntryPaginator

    @admin.display(description="Meldung")
    def short_message(self, obj):
        if len(obj.message) <= 120:
            return obj.message
        return f"{obj.message[:117]}..."

    def get_queryset(self, request):
        return super().get_queryset(request).order_by("-created_at")[:100]

    def has_module_permission(self, request):
        return request.user.is_active and request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_superuser

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_superuser
