# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

from django.contrib import admin
from django.db import models

from accounts.admin_utils import get_user_organization
from accounts.permissions import user_may_manage_organization
from playgrounds.models import (
    PlayEquipment,
    Playground,
    PlaygroundAccessory,
    PlaygroundSurface,
)

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


def user_can_admin_organization(user):
    return bool(user and user.is_authenticated and user_may_manage_organization(user))


def object_belongs_to_user_organization(user, obj):
    if user.is_superuser:
        return True

    organization = get_user_organization(user)
    if not organization:
        return False

    if obj is None:
        return True

    playground = getattr(obj, "playground", None)
    if not playground:
        return False

    return playground.organization_id == organization.id


class OrganizationCapabilityAdminMixin:
    """Use the single SpielplatzAtlas profile capability model in Django admin."""

    def has_module_permission(self, request):
        return request.user.is_superuser or user_can_admin_organization(request.user)

    def has_view_permission(self, request, obj=None):
        if not (request.user.is_superuser or user_can_admin_organization(request.user)):
            return False

        return object_belongs_to_user_organization(request.user, obj)

    def has_add_permission(self, request):
        return request.user.is_superuser or user_can_admin_organization(request.user)

    def has_change_permission(self, request, obj=None):
        if not (request.user.is_superuser or user_can_admin_organization(request.user)):
            return False

        return object_belongs_to_user_organization(request.user, obj)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


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
    fields = (
        "scope_type",
        "equipment",
        "surface",
        "accessory",
        "label",
        "sort_order",
    )

class InspectionCriterionApplicabilityInline(admin.StackedInline):
    model = InspectionCriterionApplicability
    extra = 1
    fields = (
        "scope_type",
        "applies_to_all_equipment",
        "equipment_types",
    )
    filter_horizontal = ("equipment_types",)

@admin.register(InspectionCriterion)
class InspectionCriterionAdmin(admin.ModelAdmin):
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
    list_filter = (
        "organization",
        "area",
        "minimum_inspection_type",
        "is_standard",
        "is_locked",
        "is_active",
        "standard_version",
    )
    search_fields = (
        "title",
        "area",
        "inspection_text",
        "maintenance_text",
        "norm_reference",
        "standard_version",
        "source_note",
    )

    inlines = (InspectionCriterionApplicabilityInline,)

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        organization = get_user_organization(request.user)

        if organization:
            return qs.filter(organization__isnull=True) | qs.filter(organization=organization)

        return qs.filter(organization__isnull=True)

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

        return (
            "area",
            "title",
            "inspection_text",
            "maintenance_text",
            "norm_reference",
            "minimum_inspection_type",
            "is_active",
        )

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return ()
    
        if obj and obj.organization_id is None:
            return (
                "area",
                "title",
                "inspection_text",
                "maintenance_text",
                "norm_reference",
                "minimum_inspection_type",
                "is_active",
            )
    
        if obj and obj.is_locked:
            return (
                "area",
                "title",
                "inspection_text",
                "maintenance_text",
                "norm_reference",
                "minimum_inspection_type",
                "is_active",
            )
    
        return ()

    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True

        organization = get_user_organization(request.user)

        if obj is None:
            return organization is not None

        if obj.organization_id is None:
            return True

        return organization and obj.organization_id == organization.id


    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True

        organization = get_user_organization(request.user)

        if obj is None:
            return organization is not None

        if not organization:
            return False

        if obj.organization_id is None:
            # Globale Standards dürfen geöffnet, aber nicht bearbeitet werden.
            return True

        return obj.organization_id == organization.id

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "organization" and not request.user.is_superuser:
            organization = get_user_organization(request.user)
            kwargs["queryset"] = organization.__class__.objects.filter(id=organization.id)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            organization = get_user_organization(request.user)

            if change and obj.organization_id is None:
                return

            if organization:
                obj.organization = organization
                obj.is_standard = False
                obj.standard_version = ""
                obj.source_note = ""
                obj.is_locked = False

        super().save_model(request, obj, form, change)

@admin.register(InspectionScope)
class InspectionScopeAdmin(admin.ModelAdmin):
    list_display = (
        "inspection",
        "scope_type",
        "equipment",
        "surface",
        "accessory",
        "label",
        "sort_order",
    )
    list_filter = (
        "scope_type",
        "inspection__playground__organization",
    )
    search_fields = (
        "label",
        "inspection__playground__name",
        "equipment__name",
        "surface__name",
        "accessory__name",
    )
    autocomplete_fields = (
        "inspection",
        "equipment",
        "surface",
        "accessory",
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        organization = get_user_organization(request.user)

        if organization:
            return qs.filter(inspection__playground__organization=organization)

        return qs.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        organization = get_user_organization(request.user)

        if not request.user.is_superuser and organization:
            if db_field.name == "inspection":
                kwargs["queryset"] = Inspection.objects.filter(
                    playground__organization=organization
                )

            if db_field.name == "equipment":
                kwargs["queryset"] = PlayEquipment.objects.filter(
                    playground__organization=organization
                )

            if db_field.name == "surface":
                kwargs["queryset"] = PlaygroundSurface.objects.filter(
                    playground__organization=organization
                )

            if db_field.name == "accessory":
                kwargs["queryset"] = PlaygroundAccessory.objects.filter(
                    playground__organization=organization
                )

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

def get_allowed_minimum_inspection_types(inspection_type):
    if inspection_type == Inspection.TYPE_VISUAL:
        return [
            InspectionCriterion.MINIMUM_VISUAL,
        ]

    if inspection_type == Inspection.TYPE_OPERATIONAL:
        return [
            InspectionCriterion.MINIMUM_VISUAL,
            InspectionCriterion.MINIMUM_OPERATIONAL,
        ]

    if inspection_type == Inspection.TYPE_ANNUAL:
        return [
            InspectionCriterion.MINIMUM_VISUAL,
            InspectionCriterion.MINIMUM_OPERATIONAL,
            InspectionCriterion.MINIMUM_ANNUAL,
        ]

    return [
        InspectionCriterion.MINIMUM_VISUAL,
        InspectionCriterion.MINIMUM_OPERATIONAL,
        InspectionCriterion.MINIMUM_ANNUAL,
    ]

@admin.register(Inspection)
class InspectionAdmin(OrganizationCapabilityAdminMixin, admin.ModelAdmin):
    list_display = (
        "playground",
        "inspection_type",
        "inspected_at",
        "inspector",
        "result",
        "created_at",
    )
    list_filter = (
        "inspection_type",
        "result",
        "playground__organization",
        "inspected_at",
    )
    search_fields = (
        "playground__name",
        "inspector__username",
        "inspector__email",
        "notes",
    )
    autocomplete_fields = ("playground", "inspector")
    inlines = (InspectionScopeInline, InspectionAnswerInline, DefectInline)

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        organization = get_user_organization(request.user)

        if organization:
            return qs.filter(playground__organization=organization)

        return qs.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        organization = get_user_organization(request.user)

        if not request.user.is_superuser and organization:
            if db_field.name == "playground":
                kwargs["queryset"] = Playground.objects.filter(organization=organization)

            if db_field.name == "inspector":
                kwargs["queryset"] = kwargs.get("queryset", db_field.remote_field.model.objects.all()).filter(
                    profile__organization=organization
                )

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        is_new = obj.pk is None

        if not change and not request.user.is_superuser:
            obj.inspector = request.user

        super().save_model(request, obj, form, change)

        if is_new:
            self.create_default_answers(obj)

    def create_default_answers(self, inspection):
        organization = inspection.playground.organization

        allowed_minimum_types = get_allowed_minimum_inspection_types(
            inspection.inspection_type
        )

        base_criteria = (
            InspectionCriterion.objects
            .filter(is_active=True)
            .filter(minimum_inspection_type__in=allowed_minimum_types)
            .filter(
                models.Q(organization__isnull=True)
                | models.Q(organization=organization)
            )
            .distinct()
        )
    
        playground_criteria = list(
            base_criteria
            .filter(
                applicabilities__scope_type=InspectionCriterionApplicability.SCOPE_PLAYGROUND
            )
            .order_by("area", "title")
            .distinct()
        )
    
        surface_criteria = list(
            base_criteria
            .filter(
                applicabilities__scope_type=InspectionCriterionApplicability.SCOPE_SURFACE
            )
            .order_by("area", "title")
            .distinct()
        )
    
        accessory_criteria = list(
            base_criteria
            .filter(
                applicabilities__scope_type=InspectionCriterionApplicability.SCOPE_ACCESSORY
            )
            .order_by("area", "title")
            .distinct()
        )
    
        scopes_with_criteria = []
    
        playground_scope, _ = InspectionScope.objects.get_or_create(
            inspection=inspection,
            scope_type=InspectionScope.SCOPE_PLAYGROUND,
            equipment=None,
            surface=None,
            accessory=None,
            defaults={
                "label": "Allgemeine Spielplatzprüfung",
                "sort_order": 0,
            },
        )
        scopes_with_criteria.append((playground_scope, playground_criteria))
    
        equipment_list = list(
            PlayEquipment.objects
            .filter(
                playground=inspection.playground,
                is_active=True,
                public_visible=True,
            )
            .select_related("equipment_type")
            .order_by("name")
        )
    
        for index, equipment in enumerate(equipment_list, start=1):
            equipment_scope, _ = InspectionScope.objects.get_or_create(
                inspection=inspection,
                scope_type=InspectionScope.SCOPE_EQUIPMENT,
                equipment=equipment,
                surface=None,
                accessory=None,
                defaults={
                    "label": equipment.name,
                    "sort_order": index * 10,
                },
            )
    
            equipment_criteria = list(
                base_criteria
                .filter(
                    applicabilities__scope_type=InspectionCriterionApplicability.SCOPE_EQUIPMENT
                )
                .filter(
                    models.Q(applicabilities__applies_to_all_equipment=True)
                    | models.Q(applicabilities__equipment_types=equipment.equipment_type)
                )
                .order_by("area", "title")
                .distinct()
            )
    
            scopes_with_criteria.append((equipment_scope, equipment_criteria))
    
        surface_list = list(
            PlaygroundSurface.objects
            .filter(
                playground=inspection.playground,
                is_active=True,
                public_visible=True,
            )
            .order_by("name")
        )
    
        for index, surface in enumerate(surface_list, start=1):
            surface_scope, _ = InspectionScope.objects.get_or_create(
                inspection=inspection,
                scope_type=InspectionScope.SCOPE_SURFACE,
                equipment=None,
                surface=surface,
                accessory=None,
                defaults={
                    "label": surface.name,
                    "sort_order": 1000 + index * 10,
                },
            )
    
            scopes_with_criteria.append((surface_scope, surface_criteria))
    
        accessory_list = list(
            PlaygroundAccessory.objects
            .filter(
                playground=inspection.playground,
                is_active=True,
                public_visible=True,
            )
            .order_by("name")
        )
    
        for index, accessory in enumerate(accessory_list, start=1):
            accessory_scope, _ = InspectionScope.objects.get_or_create(
                inspection=inspection,
                scope_type=InspectionScope.SCOPE_ACCESSORY,
                equipment=None,
                surface=None,
                accessory=accessory,
                defaults={
                    "label": accessory.name,
                    "sort_order": 2000 + index * 10,
                },
            )
    
            scopes_with_criteria.append((accessory_scope, accessory_criteria))
    
        existing_pairs = set(
            InspectionAnswer.objects
            .filter(inspection=inspection)
            .values_list("scope_id", "criterion_id")
        )
    
        answers_to_create = []
    
        for scope, criteria in scopes_with_criteria:
            for criterion in criteria:
                key = (scope.id, criterion.id)
    
                if key in existing_pairs:
                    continue
                
                answers_to_create.append(
                    InspectionAnswer(
                        inspection=inspection,
                        scope=scope,
                        criterion=criterion,
                        equipment=scope.equipment,
                        answer=InspectionAnswer.ANSWER_PENDING,
                    )
                )
    
        InspectionAnswer.objects.bulk_create(answers_to_create)


class DefectImageInline(admin.TabularInline):
    model = DefectImage
    extra = 0
    autocomplete_fields = ("image",)


class MaintenanceActionInline(admin.TabularInline):
    model = MaintenanceAction
    extra = 0


@admin.register(Defect)
class DefectAdmin(OrganizationCapabilityAdminMixin, admin.ModelAdmin):
    list_display = (
        "id",
        "playground",
        "equipment",
        "surface",
        "accessory",
        "source_type",
        "has_safety_risk",
        "status",
        "public_visible",
        "planned_resolution_date",
        "created_at",
    )
    list_filter = (
        "source_type",
        "has_safety_risk",
        "status",
        "public_visible",
        "planned_resolution_date",
        "playground__organization",
    )
    search_fields = (
        "internal_description",
        "internal_note",
        "public_note",
        "reported_by_text",
        "playground__name",
        "equipment__name",
        "surface__name",
        "accessory__name",
    )
    autocomplete_fields = (
        "inspection",
        "playground",
        "equipment",
        "surface",
        "accessory",
    )
    inlines = (MaintenanceActionInline, DefectImageInline)

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        organization = get_user_organization(request.user)

        if organization:
            return qs.filter(playground__organization=organization)

        return qs.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        organization = get_user_organization(request.user)

        if not request.user.is_superuser and organization:
            if db_field.name == "inspection":
                kwargs["queryset"] = Inspection.objects.filter(
                    playground__organization=organization
                )

            if db_field.name == "playground":
                kwargs["queryset"] = Playground.objects.filter(
                    organization=organization
                )

            if db_field.name == "equipment":
                kwargs["queryset"] = PlayEquipment.objects.filter(
                    playground__organization=organization
                )

            if db_field.name == "surface":
                kwargs["queryset"] = PlaygroundSurface.objects.filter(
                    playground__organization=organization
                )

            if db_field.name == "accessory":
                kwargs["queryset"] = PlaygroundAccessory.objects.filter(
                    playground__organization=organization
                )

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            organization = get_user_organization(request.user)

            if obj.playground and obj.playground.organization_id != organization.id:
                return

            if obj.equipment and obj.equipment.playground.organization_id != organization.id:
                return

            if obj.surface and obj.surface.playground.organization_id != organization.id:
                return

            if obj.accessory and obj.accessory.playground.organization_id != organization.id:
                return

        super().save_model(request, obj, form, change)


@admin.register(MaintenanceAction)
class MaintenanceActionAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "defect",
        "planned_date",
        "completed_date",
        "status",
        "public_visible",
    )
    list_filter = ("status", "public_visible", "planned_date", "completed_date")
    search_fields = ("title", "description", "defect__internal_description")
    autocomplete_fields = ("defect",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        organization = get_user_organization(request.user)

        if organization:
            return qs.filter(defect__playground__organization=organization)

        return qs.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        organization = get_user_organization(request.user)

        if db_field.name == "defect" and not request.user.is_superuser and organization:
            kwargs["queryset"] = Defect.objects.filter(
                playground__organization=organization
            )

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(DefectImage)
class DefectImageAdmin(admin.ModelAdmin):
    list_display = ("defect", "image", "caption", "public_visible")
    list_filter = ("public_visible",)
    search_fields = ("caption", "defect__internal_description", "image__original_filename")
    autocomplete_fields = ("defect", "image")

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        organization = get_user_organization(request.user)

        if organization:
            return qs.filter(defect__playground__organization=organization)

        return qs.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        organization = get_user_organization(request.user)
    
        if not request.user.is_superuser and organization:
            if db_field.name == "defect":
                kwargs["queryset"] = Defect.objects.filter(
                    playground__organization=organization
                )
    
            if db_field.name == "image":
                kwargs["queryset"] = db_field.remote_field.model.objects.filter(
                    organization=organization
                )
    
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
