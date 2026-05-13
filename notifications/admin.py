# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.

from django.contrib import admin

from accounts.admin_utils import get_user_organization

from .models import DefectAssignment, PushSubscription, SystemNotification


@admin.register(SystemNotification)
class SystemNotificationAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "recipient",
        "organization",
        "notification_type",
        "delivery_status",
        "read_at",
        "created_at",
    )
    list_filter = (
        "organization",
        "notification_type",
        "delivery_status",
        "read_at",
        "created_at",
    )
    search_fields = (
        "title",
        "message",
        "recipient__username",
        "recipient__email",
        "related_defect__internal_description",
    )
    autocomplete_fields = ("organization", "recipient", "created_by", "related_defect")
    readonly_fields = ("created_at", "updated_at", "sent_at", "delivery_status", "delivery_error")

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        organization = get_user_organization(request.user)

        if organization:
            return qs.filter(organization=organization)

        return qs.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        organization = get_user_organization(request.user)

        if not request.user.is_superuser and organization:
            if db_field.name == "organization":
                kwargs["queryset"] = db_field.remote_field.model.objects.filter(id=organization.id)

            if db_field.name in {"recipient", "created_by"}:
                kwargs["queryset"] = db_field.remote_field.model.objects.filter(
                    profile__organization=organization,
                    profile__is_active_for_organization=True,
                )

            if db_field.name == "related_defect":
                kwargs["queryset"] = db_field.remote_field.model.objects.filter(
                    playground__organization=organization
                )

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(DefectAssignment)
class DefectAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "defect",
        "assigned_to",
        "organization",
        "assigned_by",
        "assigned_at",
    )
    list_filter = ("organization", "assigned_at")
    search_fields = (
        "defect__internal_description",
        "defect__playground__name",
        "assigned_to__username",
        "assigned_to__email",
    )
    autocomplete_fields = ("defect", "organization", "assigned_to", "assigned_by")
    readonly_fields = ("assigned_at",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        organization = get_user_organization(request.user)

        if organization:
            return qs.filter(organization=organization)

        return qs.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        organization = get_user_organization(request.user)

        if not request.user.is_superuser and organization:
            if db_field.name == "organization":
                kwargs["queryset"] = db_field.remote_field.model.objects.filter(id=organization.id)

            if db_field.name == "defect":
                kwargs["queryset"] = db_field.remote_field.model.objects.filter(
                    playground__organization=organization
                )

            if db_field.name in {"assigned_to", "assigned_by"}:
                kwargs["queryset"] = db_field.remote_field.model.objects.filter(
                    profile__organization=organization,
                    profile__is_active_for_organization=True,
                )

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            organization = get_user_organization(request.user)

            if organization:
                obj.organization = organization

        super().save_model(request, obj, form, change)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(PushSubscription)
class PushSubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "organization",
        "is_active",
        "created_at",
        "last_seen_at",
    )
    list_filter = ("organization", "is_active", "created_at", "last_seen_at")
    search_fields = ("user__username", "user__email", "endpoint", "user_agent")
    autocomplete_fields = ("user", "organization")
    readonly_fields = (
        "endpoint",
        "p256dh_key",
        "auth_key",
        "user_agent",
        "created_at",
        "last_seen_at",
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        organization = get_user_organization(request.user)

        if organization:
            return qs.filter(organization=organization)

        return qs.none()

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
