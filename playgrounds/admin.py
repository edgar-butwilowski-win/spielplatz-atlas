# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

from django import forms
from django.contrib import admin, messages
from django.shortcuts import redirect, render
from django.urls import path, reverse
from PIL import Image as PillowImage

from accounts.admin_utils import get_user_organization
from media_assets.models import ImageAsset

from .models import (
    EquipmentSupplier,
    EquipmentType,
    PlayEquipment,
    Playground,
    PlaygroundAccessory,
    PlaygroundSurface,
)
from .webservice_sync import PlaygroundSyncError, sync_playgrounds_from_url


def create_image_asset_from_upload(uploaded_file, organization):
    binary_data = uploaded_file.read()

    width = None
    height = None

    try:
        uploaded_file.seek(0)
        image = PillowImage.open(uploaded_file)
        width, height = image.size
    except Exception:
        width = None
        height = None

    return ImageAsset.objects.create(
        organization=organization,
        original_filename=uploaded_file.name,
        mime_type=uploaded_file.content_type or "application/octet-stream",
        size_bytes=len(binary_data),
        width=width,
        height=height,
        sha256=ImageAsset.calculate_sha256(binary_data),
        data=binary_data,
        public_visible=True,
    )

class PlaygroundAdminForm(forms.ModelForm):
    photo_upload = forms.ImageField(
        label="Neues Foto hochladen",
        required=False,
        help_text="Optional. Wenn ein neues Foto hochgeladen wird, ersetzt es das bisherige Hauptfoto.",
    )

    class Meta:
        model = Playground
        fields = "__all__"


class PlaygroundSyncForm(forms.Form):
    service_url = forms.URLField(
        label="Webservice-URL",
        required=True,
        help_text="URL eines GeoJSON-Webservice mit Spielplatz-Objekten.",
        widget=forms.URLInput(attrs={"class": "vURLField", "size": 100}),
    )


class PlayEquipmentAdminForm(forms.ModelForm):
    photo_upload = forms.ImageField(
        label="Neues Foto hochladen",
        required=False,
        help_text="Optional. Wenn ein neues Foto hochgeladen wird, ersetzt es das bisherige Hauptfoto.",
    )

    class Meta:
        model = PlayEquipment
        fields = "__all__"

@admin.register(Playground)
class PlaygroundAdmin(admin.ModelAdmin):

    form = PlaygroundAdminForm

    fieldsets = (
        ("Grunddaten", {
            "fields": (
                "organization",
                "uuid",
                "name",
                "slug",
                "number",
                "description",
                "construction_costs",
            )
        }),
        ("Adresse und Lage", {
            "fields": (
                "address",
                "street_name",
                "house_number",
                "district",
                "latitude",
                "longitude",
            )
        }),
        ("Inspektionen", {
            "fields": (
                "inspection_suspended_from",
                "inspection_suspended_until",
            )
        }),
        ("Foto", {
            "fields": (
                "photo",
                "photo_upload",
            )
        }),
        ("Sichtbarkeit", {
            "fields": (
                "is_active",
                "public_visible",
            )
        }),
    )

    list_display = (
        "name",
        "number",
        "uuid",
        "organization",
        "district",
        "public_visible",
        "is_active",
        "inspection_suspended_from",
        "inspection_suspended_until",
        "created_at",
    )
    list_filter = ("organization", "public_visible", "is_active", "district")
    search_fields = ("name", "uuid", "number", "address", "street_name", "house_number", "district")
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ("photo",)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "sync/",
                self.admin_site.admin_view(self.sync_playgrounds_view),
                name="playgrounds_playground_sync",
            ),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["sync_url"] = reverse("admin:playgrounds_playground_sync")
        return super().changelist_view(request, extra_context=extra_context)

    def sync_playgrounds_view(self, request):
        organization = None

        if not request.user.is_superuser:
            organization = get_user_organization(request.user)

            if organization is None:
                messages.error(request, "Für Ihr Benutzerkonto ist keine Organisation hinterlegt.")
                return redirect("admin:playgrounds_playground_changelist")

        if request.method == "POST":
            form = PlaygroundSyncForm(request.POST)

            if form.is_valid():
                target_organization = organization

                if request.user.is_superuser:
                    organization_id = request.POST.get("organization")

                    if organization_id:
                        from tenants.models import Organization
                        target_organization = Organization.objects.filter(id=organization_id).first()

                if target_organization is None:
                    messages.error(request, "Bitte eine Organisation für den Abgleich auswählen.")
                    return redirect("admin:playgrounds_playground_sync")

                try:
                    result = sync_playgrounds_from_url(
                        form.cleaned_data["service_url"],
                        target_organization,
                    )
                except PlaygroundSyncError as error:
                    messages.error(request, str(error))
                except Exception as error:
                    messages.error(request, f"Der Abgleich ist fehlgeschlagen: {error}")
                else:
                    messages.success(
                        request,
                        (
                            "Spielplätze abgeglichen: "
                            f"{result['created']} neu, "
                            f"{result['updated']} aktualisiert, "
                            f"{result['unchanged']} unverändert, "
                            f"{result['skipped']} übersprungen."
                        ),
                    )
                    return redirect("admin:playgrounds_playground_changelist")
        else:
            form = PlaygroundSyncForm()

        organizations = []

        if request.user.is_superuser:
            from tenants.models import Organization
            organizations = Organization.objects.filter(is_active=True).order_by("name")

        context = {
            **self.admin_site.each_context(request),
            "title": "Spielplätze abgleichen",
            "form": form,
            "organization": organization,
            "organizations": organizations,
            "opts": self.model._meta,
        }
        return render(request, "admin/playgrounds/playground/sync.html", context)

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        organization = get_user_organization(request.user)

        if organization:
            return qs.filter(organization=organization)

        return qs.none()

    def get_fieldsets(self, request, obj=None):
        fieldsets = super().get_fieldsets(request, obj)

        if request.user.is_superuser:
            return fieldsets

        filtered_fieldsets = []

        for title, options in fieldsets:
            fields = tuple(
                field for field in options.get("fields", ())
                if field not in ("organization", "is_active")
            )
            filtered_options = {**options, "fields": fields}
            filtered_fieldsets.append((title, filtered_options))

        return tuple(filtered_fieldsets)

    def get_readonly_fields(self, request, obj=None):
        return ()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser:
            organization = get_user_organization(request.user)

            if organization:
                if db_field.name == "organization":
                    kwargs["queryset"] = organization.__class__.objects.filter(
                        id=organization.id
                    )

                if db_field.name == "photo":
                    kwargs["queryset"] = db_field.remote_field.model.objects.filter(
                        organization=organization
                    )

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            organization = get_user_organization(request.user)

            if organization:
                obj.organization = organization

        uploaded_photo = form.cleaned_data.get("photo_upload")

        if uploaded_photo:
            organization = obj.organization

            if not organization:
                organization = get_user_organization(request.user)

            image_asset = create_image_asset_from_upload(
                uploaded_photo,
                organization,
            )
            obj.photo = image_asset

        super().save_model(request, obj, form, change)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(EquipmentType)
class EquipmentTypeAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "code",
        "organization",
        "norm_reference",
        "is_standard",
        "standard_version",
        "is_locked",
        "is_active",
    )
    list_filter = (
        "organization",
        "is_standard",
        "is_locked",
        "is_active",
        "standard_version",
    )
    search_fields = (
        "name",
        "code",
        "norm_reference",
        "standard_version",
        "source_note",
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        organization = get_user_organization(request.user)

        if organization:
            return (
                qs.filter(organization__isnull=True)
                | qs.filter(organization=organization)
            ).distinct()

        return qs.filter(organization__isnull=True)

    def get_fields(self, request, obj=None):
        if request.user.is_superuser:
            return (
                "organization",
                "name",
                "code",
                "norm_reference",
                "is_standard",
                "standard_version",
                "source_note",
                "is_locked",
                "is_active",
            )

        return (
            "name",
            "code",
            "norm_reference",
            "is_active",
        )

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return ()

        if obj and obj.organization_id is None:
            return (
                "name",
                "code",
                "norm_reference",
                "is_active",
            )

        if obj and obj.is_locked:
            return (
                "name",
                "code",
                "norm_reference",
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

    def has_add_permission(self, request):
        if request.user.is_superuser:
            return True

        return get_user_organization(request.user) is not None

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True

        organization = get_user_organization(request.user)

        if obj is None:
            return organization is not None

        if not organization:
            return False

        if obj.organization_id is None:
            return True

        return obj.organization_id == organization.id

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "organization" and not request.user.is_superuser:
            organization = get_user_organization(request.user)

            if organization:
                kwargs["queryset"] = organization.__class__.objects.filter(
                    id=organization.id
                )

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


@admin.register(EquipmentSupplier)
class EquipmentSupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "is_active", "created_at")
    list_filter = ("organization", "is_active")
    search_fields = ("name", "organization__name")

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        organization = get_user_organization(request.user)

        if organization:
            return (
                qs.filter(organization__isnull=True)
                | qs.filter(organization=organization)
            ).distinct()

        return qs.filter(organization__isnull=True)

    def get_fields(self, request, obj=None):
        if request.user.is_superuser:
            return ("organization", "name", "is_active")

        return ("name", "is_active")

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return ()

        if obj and obj.organization_id is None:
            return ("name", "is_active")

        return ()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "organization" and not request.user.is_superuser:
            organization = get_user_organization(request.user)

            if organization:
                kwargs["queryset"] = organization.__class__.objects.filter(id=organization.id)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            organization = get_user_organization(request.user)

            if change and obj.organization_id is None:
                return

            if organization:
                obj.organization = organization

        super().save_model(request, obj, form, change)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(PlayEquipment)
class PlayEquipmentAdmin(admin.ModelAdmin):

    form = PlayEquipmentAdminForm

    fieldsets = (
        ("Grunddaten", {
            "fields": (
                "playground",
                "equipment_type",
                "name",
                "sequence_number",
                "inventory_number",
            )
        }),
        ("Herstellung und Lieferung", {
            "fields": (
                "manufacturer",
                "supplier",
                "norm",
                "year_built",
                "build_date",
            )
        }),
        ("Sanierung und Rückbau", {
            "fields": (
                "renovation_type",
                "recommended_renovation_year",
                "renovation_comment",
                "demolition_date",
            )
        }),
        ("Prüfbarkeit", {
            "fields": (
                "not_inspectable",
                "not_inspectable_reason",
            )
        }),
        ("Foto", {
            "fields": (
                "photo",
                "photo_upload",
            )
        }),
        ("Koordinaten und Sichtbarkeit", {
            "fields": (
                "latitude",
                "longitude",
                "public_visible",
                "is_active",
            )
        }),
    )

    list_display = (
        "name",
        "playground",
        "equipment_type",
        "sequence_number",
        "inventory_number",
        "recommended_renovation_year",
        "demolition_date",
        "public_visible",
        "is_active",
    )
    list_filter = (
        "playground__organization",
        "equipment_type",
        "supplier",
        "renovation_type",
        "not_inspectable",
        "public_visible",
        "is_active",
    )
    search_fields = (
        "name",
        "inventory_number",
        "manufacturer",
        "supplier__name",
        "norm",
        "playground__name",
    )
    autocomplete_fields = ("playground", "equipment_type", "supplier", "photo")

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
                kwargs["queryset"] = Playground.objects.filter(
                    organization=organization
                )

            if db_field.name == "equipment_type":
                kwargs["queryset"] = (
                    EquipmentType.objects.filter(organization__isnull=True)
                    | EquipmentType.objects.filter(organization=organization)
                ).distinct()

            if db_field.name == "supplier":
                kwargs["queryset"] = (
                    EquipmentSupplier.objects.filter(organization__isnull=True)
                    | EquipmentSupplier.objects.filter(organization=organization)
                ).filter(is_active=True).distinct()

            if db_field.name == "photo":
                kwargs["queryset"] = db_field.remote_field.model.objects.filter(
                    organization=organization
                )

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def save_model(self, request, obj, form, change):
        uploaded_photo = form.cleaned_data.get("photo_upload")
    
        if uploaded_photo:
            organization = obj.playground.organization
    
            image_asset = create_image_asset_from_upload(
                uploaded_photo,
                organization,
            )
            obj.photo = image_asset
    
        super().save_model(request, obj, form, change)


@admin.register(PlaygroundSurface)
class PlaygroundSurfaceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "playground",
        "surface_type",
        "public_visible",
        "is_active",
        "created_at",
    )
    list_filter = (
        "playground__organization",
        "surface_type",
        "public_visible",
        "is_active",
    )
    search_fields = ("name", "description", "playground__name")

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
                kwargs["queryset"] = Playground.objects.filter(
                    organization=organization
                )

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(PlaygroundAccessory)
class PlaygroundAccessoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "playground",
        "accessory_type",
        "public_visible",
        "is_active",
        "created_at",
    )
    list_filter = (
        "playground__organization",
        "accessory_type",
        "public_visible",
        "is_active",
    )
    search_fields = ("name", "description", "playground__name")

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
                kwargs["queryset"] = Playground.objects.filter(
                    organization=organization
                )

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
