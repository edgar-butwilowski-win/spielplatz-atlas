from django import forms
from django.contrib import admin

from accounts.admin_utils import get_user_organization
from media_assets.image_import import create_image_asset_from_upload

from .models import (
    EquipmentSupplier,
    EquipmentType,
    PlayEquipment,
    Playground,
    PlaygroundAccessory,
    PlaygroundSurface,
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


class PlayEquipmentAdminForm(forms.ModelForm):
    photo_upload = forms.ImageField(
        label="Neues Foto hochladen",
        required=False,
        help_text="Optional. Wenn ein neues Foto hochgeladen wird, ersetzt es das bisherige Hauptfoto.",
    )

    class Meta:
        model = PlayEquipment
        fields = "__all__"
        widgets = {
            "year_built": forms.DateInput(attrs={"type": "date"}),
            "build_date": forms.DateInput(attrs={"type": "date"}),
            "demolition_date": forms.DateInput(attrs={"type": "date"}),
        }


class OrganizationScopedAdminMixin:
    organization_field = "organization"

    def get_user_organization(self, request):
        if request.user.is_superuser:
            return None

        return get_user_organization(request.user)

    def scope_queryset_to_organization(self, qs, request):
        if request.user.is_superuser:
            return qs

        organization = self.get_user_organization(request)

        if not organization:
            return qs.none()

        return qs.filter(organization=organization)


@admin.register(Playground)
class PlaygroundAdmin(OrganizationScopedAdminMixin, admin.ModelAdmin):
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
        "created_at",
    )
    list_filter = ("organization", "public_visible", "is_active", "district")
    search_fields = ("name", "uuid", "number", "address", "street_name", "house_number", "district")
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ("photo",)

    def get_queryset(self, request):
        return self.scope_queryset_to_organization(super().get_queryset(request), request)

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
            filtered_fieldsets.append((title, {**options, "fields": fields}))

        return tuple(filtered_fieldsets)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if not request.user.is_superuser:
            organization = get_user_organization(request.user)

            if organization:
                if db_field.name == "organization":
                    kwargs["queryset"] = organization.__class__.objects.filter(id=organization.id)
                elif db_field.name == "photo":
                    kwargs["queryset"] = db_field.remote_field.model.objects.filter(organization=organization)

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            organization = get_user_organization(request.user)

            if organization:
                obj.organization = organization

        uploaded_photo = form.cleaned_data.get("photo_upload")

        if uploaded_photo:
            organization = obj.organization or get_user_organization(request.user)
            obj.photo = create_image_asset_from_upload(uploaded_photo, organization)

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
    )
    search_fields = ("name", "code", "norm_reference", "organization__name")

    fieldsets = (
        ("Grunddaten", {
            "fields": (
                "organization",
                "name",
                "code",
                "norm_reference",
                "is_active",
            )
        }),
        ("Standardkatalog", {
            "fields": (
                "is_standard",
                "standard_version",
                "source_note",
                "is_locked",
            )
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.is_superuser:
            return qs

        organization = get_user_organization(request.user)

        if organization:
            return qs.filter(
                models.Q(organization=organization) | models.Q(organization__isnull=True)
            )

        return qs.filter(organization__isnull=True)

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True

        if obj and obj.is_locked:
            return False

        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
