# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

from django.contrib import admin

from accounts.admin_utils import OrganizationAdminPermissionMixin, get_user_organization
from playgrounds.models import PlayEquipment, Playground, PlaygroundAccessory, PlaygroundSurface

from .models import (
    Defect,
    DefectImage,
    Inspection,
    InspectionAnswer,
    InspectionCriterion,
    InspectionCriterionApplicability,
    InspectionScope,
    MaintenanceAction,
)


def queryset_for_user_organization(request, qs, organization_path):
    if request.user.is_superuser:
        return qs

    organization = get_user_organization(request.user)

    if not organization:
        return qs.none()

    return qs.filter(**{organization_path: organization})


def object_organization_from_playground_object(obj):
    if obj is None:
        return None

    playground = getattr(obj, "playground", None)
    return playground.organization if playground else None


def object_organization_from_inspection_object(obj):
    if obj is None:
        return None

    inspection = getattr(obj, "inspection", None)
    return inspection.playground.organization if inspection and inspection.playground_id else None


def object_organization_from_defect_object(obj):
    if obj is None:
        return None

    defect = getattr(obj, "defect", None)
    return defect.playground.organization if defect and defect.playground_id else None


class InspectionAnswerInline(admin.TabularInline):
    model = InspectionAnswer
    extra = 0
    autocomplete_fields = ("scope", "criterion", "equipment")
    fields = ("scope", "criterion", "equipment", "answer", "comment")


class DefectInline(admin.StackedInline):
    model = Defect
    extra = 0
    autocomplete_fields = ("equipment",)


class InspectionScopeInline(admin.TabularInline):
    model = InspectionScope
    extra = 0
    autocomplete_fields = ("equipment", "surface", "accessory")
    fields = ("scope_type", "equipment", "surface", "accessory", "label", "sort_order")


class InspectionCriterionApplicabilityInline(admin.StackedInline):
    model = InspectionCriterionApplicability
    extra = 1
    fields = ("scope_type", "applies_to_all_equipment", "equipment_types")
    filter_horizontal = ("equipment_types",)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        organization = get_user_organization(request.user)

        if not request.user.is_superuser and organization and db_field.name == "equipment_types":
            kwargs["queryset"] = db_field.remote_field.model.objects.filter(organization=organization)

        return super().formfield_for_manytomany(db_field, request, **kwargs)


@admin.register(InspectionCriterion)
class InspectionCriterionAdmin(OrganizationAdminPermissionMixin, admin.ModelAdmin):
    list_display = (
        "title",
        "area",
        "organization",
        "norm_reference",
        "minimum_inspection_type",
        "is_standard",
        "standard_version",
        "is_locked",
        "is_active",
    )
    list_filter = ("organization", "area", "minimum_inspection_type", "is_standard", "is_locked", "is_active", "standard_version")
    search_fields = ("title", "area", "inspection_text", "maintenance_text", "norm_reference", "standard_version", "source_note")
    inlines = (InspectionCriterionApplicabilityInline,)

    def get_queryset(self, request):
        return queryset_for_user_organization(request, super().get_queryset(request), "organization")

    def get_fields(self, request, obj=None):
        if request.user.is_superuser:
            return (
                "organization",
                "area",
                "title",
                "inspection_text",
                "maintenance_text",
                "norm_reference",
                "minimum_inspection_type",
                "is_standard",
                "standard_version",
                "source_note",
                "is_locked",
                "is_active",
            )

        return ("area", "title", "inspection_text", "maintenance_text", "norm_reference", "minimum_inspection_type", "is_active")

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            organization = get_user_organization(request.user)
            obj.organization = organization
            obj.is_standard = False
            obj.standard_version = ""
            obj.source_note = ""
            obj.is_locked = False

        super().save_model(request, obj, form, change)


@admin.register(InspectionScope)
class InspectionScopeAdmin(OrganizationAdminPermissionMixin, admin.ModelAdmin):
    list_display = ("inspection", "scope_type", "equipment", "surface", "accessory", "label", "sort_order")
    list_filter = ("scope_type", "inspection__playground__organization")
    search_fields = ("label", "inspection__playground__name", "equipment__name", "surface__name", "accessory__name")
    autocomplete_fields = ("inspection", "equipment", "surface", "accessory")

    def get_object_organization(self, obj):
        return object_organization_from_inspection_object(obj)

    def get_queryset(self, request):
        return queryset_for_user_organization(request, super().get_queryset(request), "inspection__playground__organization")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        organization = get_user_organization(request.user)

        if not request.user.is_superuser and organization:
            if db_field.name == "inspection":
                kwargs["queryset"] = Inspection.objects.filter(playground__organization=organization)
            elif db_field.name == "equipment":
                kwargs["queryset"] = PlayEquipment.objects.filter(playground__organization=organization)
            elif db_field.name == "surface":
                kwargs["queryset"] = PlaygroundSurface.objects.filter(playground__organization=organization)
            elif db_field.name == "accessory":
                kwargs["queryset"] = PlaygroundAccessory.objects.filter(playground__organization=organization)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


def get_allowed_minimum_inspection_types(inspection_type):
    if inspection_type == Inspection.TYPE_VISUAL:
        return [InspectionCriterion.MINIMUM_VISUAL]

    if inspection_type == Inspection.TYPE_OPERATIONAL:
        return [InspectionCriterion.MINIMUM_VISUAL, InspectionCriterion.MINIMUM_OPERATIONAL]

    if inspection_type == Inspection.TYPE_ANNUAL:
        return [InspectionCriterion.MINIMUM_VISUAL, InspectionCriterion.MINIMUM_OPERATIONAL, InspectionCriterion.MINIMUM_ANNUAL]

    return [InspectionCriterion.MINIMUM_VISUAL, InspectionCriterion.MINIMUM_OPERATIONAL, InspectionCriterion.MINIMUM_ANNUAL]


@admin.register(Inspection)
class InspectionAdmin(OrganizationAdminPermissionMixin, admin.ModelAdmin):
    list_display = ("playground", "inspection_type", "inspected_at", "inspector", "result", "created_at")
    list_filter = ("inspection_type", "result", "playground__organization", "inspected_at")
    search_fields = ("playground__name", "inspector__email", "notes")
    autocomplete_fields = ("playground", "inspector")
    inlines = (InspectionScopeInline, InspectionAnswerInline, DefectInline)

    def get_object_organization(self, obj):
        return object_organization_from_playground_object(obj)

    def get_queryset(self, request):
        return queryset_for_user_organization(request, super().get_queryset(request), "playground__organization")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        organization = get_user_organization(request.user)

        if not request.user.is_superuser and organization:
            if db_field.name == "playground":
                kwargs["queryset"] = Playground.objects.filter(organization=organization)
            elif db_field.name == "inspector":
                kwargs["queryset"] = db_field.remote_field.model.objects.filter(profile__organization=organization)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        is_new = obj.pk is None

        if not change and not request.user.is_superuser:
            obj.inspector = request.user

        super().save_model(request, obj, form, change)

        if is_new:
            from internal.views import create_default_answers

            create_default_answers(obj)


class DefectImageInline(admin.TabularInline):
    model = DefectImage
    extra = 0
    autocomplete_fields = ("image",)


class MaintenanceActionInline(admin.TabularInline):
    model = MaintenanceAction
    extra = 0


@admin.register(Defect)
class DefectAdmin(OrganizationAdminPermissionMixin, admin.ModelAdmin):
    list_display = ("id", "playground", "equipment", "surface", "accessory", "source_type", "has_safety_risk", "status", "public_visible", "planned_resolution_date", "created_at")
    list_filter = ("source_type", "has_safety_risk", "status", "public_visible", "planned_resolution_date", "playground__organization")
    search_fields = ("internal_description", "internal_note", "public_note", "reported_by_text", "playground__name", "equipment__name", "surface__name", "accessory__name")
    autocomplete_fields = ("inspection", "playground", "equipment", "surface", "accessory")
    inlines = (MaintenanceActionInline, DefectImageInline)

    def get_object_organization(self, obj):
        return object_organization_from_playground_object(obj)

    def get_queryset(self, request):
        return queryset_for_user_organization(request, super().get_queryset(request), "playground__organization")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        organization = get_user_organization(request.user)

        if not request.user.is_superuser and organization:
            if db_field.name == "inspection":
                kwargs["queryset"] = Inspection.objects.filter(playground__organization=organization)
            elif db_field.name == "playground":
                kwargs["queryset"] = Playground.objects.filter(organization=organization)
            elif db_field.name == "equipment":
                kwargs["queryset"] = PlayEquipment.objects.filter(playground__organization=organization)
            elif db_field.name == "surface":
                kwargs["queryset"] = PlaygroundSurface.objects.filter(playground__organization=organization)
            elif db_field.name == "accessory":
                kwargs["queryset"] = PlaygroundAccessory.objects.filter(playground__organization=organization)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(MaintenanceAction)
class MaintenanceActionAdmin(OrganizationAdminPermissionMixin, admin.ModelAdmin):
    list_display = ("title", "defect", "planned_date", "completed_date", "status", "public_visible")
    list_filter = ("status", "public_visible", "planned_date", "completed_date")
    search_fields = ("title", "description", "defect__internal_description")
    autocomplete_fields = ("defect",)

    def get_object_organization(self, obj):
        return object_organization_from_defect_object(obj)

    def get_queryset(self, request):
        return queryset_for_user_organization(request, super().get_queryset(request), "defect__playground__organization")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        organization = get_user_organization(request.user)

        if db_field.name == "defect" and not request.user.is_superuser and organization:
            kwargs["queryset"] = Defect.objects.filter(playground__organization=organization)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(DefectImage)
class DefectImageAdmin(OrganizationAdminPermissionMixin, admin.ModelAdmin):
    list_display = ("defect", "image", "caption", "public_visible")
    list_filter = ("public_visible",)
    search_fields = ("caption", "defect__internal_description", "image__original_filename")
    autocomplete_fields = ("defect", "image")

    def get_object_organization(self, obj):
        return object_organization_from_defect_object(obj)

    def get_queryset(self, request):
        return queryset_for_user_organization(request, super().get_queryset(request), "defect__playground__organization")

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        organization = get_user_organization(request.user)

        if not request.user.is_superuser and organization:
            if db_field.name == "defect":
                kwargs["queryset"] = Defect.objects.filter(playground__organization=organization)
            elif db_field.name == "image":
                kwargs["queryset"] = db_field.remote_field.model.objects.filter(organization=organization)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)
