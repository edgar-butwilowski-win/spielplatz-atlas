# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

from django.contrib import admin

from accounts.admin_utils import get_user_organization
from playgrounds.models import Playground

from .models import Inspection, InspectionRule, InspectionTask


@admin.register(InspectionRule)
class InspectionRuleAdmin(admin.ModelAdmin):
    list_display = (
        "organization",
        "inspection_type",
        "interval_days",
        "applies_to_all_playgrounds",
        "is_active",
        "updated_at",
    )
    list_filter = (
        "organization",
        "inspection_type",
        "applies_to_all_playgrounds",
        "is_active",
    )
    search_fields = (
        "organization__name",
        "inspection_type",
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        organization = get_user_organization(request.user)

        if organization:
            return qs.filter(organization=organization)

        return qs.none()

    def get_fields(self, request, obj=None):
        if request.user.is_superuser:
            return (
                "organization",
                "inspection_type",
                "interval_days",
                "applies_to_all_playgrounds",
                "is_active",
            )

        return (
            "inspection_type",
            "interval_days",
            "applies_to_all_playgrounds",
            "is_active",
        )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "organization" and not request.user.is_superuser:
            organization = get_user_organization(request.user)

            if organization:
                kwargs["queryset"] = organization.__class__.objects.filter(id=organization.id)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            organization = get_user_organization(request.user)

            if organization:
                obj.organization = organization

        super().save_model(request, obj, form, change)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(InspectionTask)
class InspectionTaskAdmin(admin.ModelAdmin):
    list_display = (
        "playground",
        "inspection_type",
        "due_date",
        "planned_date",
        "assigned_to",
        "status",
        "source",
        "organization",
    )
    list_filter = (
        "organization",
        "inspection_type",
        "status",
        "source",
        "due_date",
        "planned_date",
    )
    search_fields = (
        "playground__name",
        "playground__organization__name",
        "assigned_to__username",
        "assigned_to__email",
        "note",
    )
    autocomplete_fields = (
        "playground",
        "assigned_to",
        "created_from_inspection",
        "completed_by_inspection",
    )
    readonly_fields = (
        "created_from_inspection",
        "completed_by_inspection",
        "created_at",
        "updated_at",
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related(
            "organization",
            "playground",
            "assigned_to",
            "created_from_inspection",
            "completed_by_inspection",
        )

        if request.user.is_superuser:
            return qs

        organization = get_user_organization(request.user)

        if organization:
            return qs.filter(organization=organization)

        return qs.none()

    def get_fields(self, request, obj=None):
        if request.user.is_superuser:
            return (
                "organization",
                "playground",
                "inspection_type",
                "due_date",
                "planned_date",
                "assigned_to",
                "status",
                "source",
                "note",
                "created_from_inspection",
                "completed_by_inspection",
                "created_at",
                "updated_at",
            )

        return (
            "playground",
            "inspection_type",
            "due_date",
            "planned_date",
            "assigned_to",
            "status",
            "source",
            "note",
            "created_from_inspection",
            "completed_by_inspection",
            "created_at",
            "updated_at",
        )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        organization = get_user_organization(request.user)

        if not request.user.is_superuser and organization:
            if db_field.name == "organization":
                kwargs["queryset"] = organization.__class__.objects.filter(id=organization.id)

            if db_field.name == "playground":
                kwargs["queryset"] = Playground.objects.filter(
                    organization=organization,
                    is_active=True,
                )

            if db_field.name == "assigned_to":
                kwargs["queryset"] = db_field.remote_field.model.objects.filter(
                    profile__organization=organization,
                    profile__is_active_for_organization=True,
                ).filter(
                    profile__can_inspect=True
                )

            if db_field.name in ["created_from_inspection", "completed_by_inspection"]:
                kwargs["queryset"] = Inspection.objects.filter(
                    playground__organization=organization,
                )

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            organization = get_user_organization(request.user)

            if organization:
                obj.organization = organization

        if obj.playground_id and not obj.organization_id:
            obj.organization = obj.playground.organization

        obj.full_clean()
        super().save_model(request, obj, form, change)
        obj.refresh_status(save=True)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
