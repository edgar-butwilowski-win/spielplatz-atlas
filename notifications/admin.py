# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.

from django.contrib import admin

from accounts.admin_utils import OrganizationAdminPermissionMixin, get_user_organization

from .models import DefectAssignment, PushSubscription, SystemNotification


class OrganizationNotificationAdminMixin(OrganizationAdminPermissionMixin):
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

            if db_field.name in {"recipient", "created_by", "assigned_to", "assigned_by", "user"}:
                kwargs["queryset"] = db_field.remote_field.model.objects.filter(
                    profile__organization=organization,
                    profile__is_active_for_organization=True,
                )

            if db_field.name in {"related_defect", "defect"}:
                kwargs["queryset"] = db_field.remote_field.model.objects.filter(
                    playground__organization=organization
                )

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            organization = get_user_organization(request.user)
            if organization and hasattr(obj, "organization"):
                obj.organization = organization

        super().save_model(request, obj, form, change)


def format_user_with_email(user):
    if not user:
        return "-"

    full_name = user.get_full_name().strip()
    email = (user.email or "").strip()

    if full_name and email:
        return f"{full_name} ({email})"
    if email:
        return email
    if full_name:
        return full_name
    return user.get_username()


@admin.register(SystemNotification)
class SystemNotificationAdmin(OrganizationNotificationAdminMixin, admin.ModelAdmin):
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
        "recipient__email",
        "related_defect__internal_description",
    )
    autocomplete_fields = ("organization", "recipient", "created_by", "related_defect")
    readonly_fields = ("created_at", "updated_at", "sent_at", "delivery_status", "delivery_error")


@admin.register(DefectAssignment)
class DefectAssignmentAdmin(OrganizationNotificationAdminMixin, admin.ModelAdmin):
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
        "assigned_to__email",
    )
    autocomplete_fields = ("defect", "organization", "assigned_to", "assigned_by")
    readonly_fields = ("assigned_at",)


@admin.register(PushSubscription)
class PushSubscriptionAdmin(OrganizationNotificationAdminMixin, admin.ModelAdmin):
    list_display = (
        "user_display",
        "organization",
        "is_active",
        "created_at",
        "last_seen_at",
    )
    list_filter = ("organization", "is_active", "created_at", "last_seen_at")
    search_fields = ("user__first_name", "user__last_name", "user__email", "endpoint", "user_agent")
    autocomplete_fields = ("user", "organization")
    readonly_fields = (
        "endpoint",
        "p256dh_key",
        "auth_key",
        "user_agent",
        "created_at",
        "last_seen_at",
    )

    @admin.display(description="Benutzer", ordering="user__last_name")
    def user_display(self, obj):
        return format_user_with_email(obj.user)

    def has_add_permission(self, request):
        return request.user.is_superuser
