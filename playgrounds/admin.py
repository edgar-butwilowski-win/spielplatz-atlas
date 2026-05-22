from django import forms
from django.contrib import admin
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
        ("Grunddaten", {"fields": ("organization", "uuid", "name", "slug", "number", "description", "construction_costs")}),
        ("Adresse und Lage", {"fields": ("address", "street_name", "house_number", "district", "latitude", "longitude")}),
        ("Inspektionen", {"fields": ("inspection_suspended_from", "inspection_suspended_until")}),
        ("Foto", {"fields": ("photo", "photo_upload")}),
        ("Sichtbarkeit", {"fields": ("is_active", "public_visible")}),
    )
    list_display = ("name", "number", "uuid", "organization", "district", "public_visible", "is_active", "created_at")
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
            fields = tuple(field for field in options.get("fields", ()) if field not in ("organization", "is_active"))
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
    list_display = ("name", "code", "organization", "norm_reference", "is_standard", "standard_version", "is_locked", "is_active")
    list_filter = ("organization", "is_standard", "is_locked", "is_active", "standard_version")
    search_fields = ("name", "code", "norm_reference", "standard_version", "source_note")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        organization = get_user_organization(request.user)
        if organization:
            return (qs.filter(organization__isnull=True) | qs.filter(organization=organization)).distinct()
        return qs.filter(organization__isnull=True)

    def get_fields(self, request, obj=None):
        if request.user.is_superuser:
            return ("organization", "name", "code", "norm_reference", "is_standard", "standard_version", "source_note", "is_locked", "is_active")
        return ("name", "code", "norm_reference", "is_active")

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return ()
        if obj and (obj.organization_id is None or obj.is_locked):
            return ("name", "code", "norm_reference", "is_active")
        return ()

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

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(EquipmentSupplier)
class EquipmentSupplierAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "tel_nr", "plz_ort", "e_mail", "is_active", "created_at")
    list_filter = ("organization", "is_active")
    search_fields = ("name", "tel_nr", "strasse", "plz_ort", "e_mail", "organization__name")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        organization = get_user_organization(request.user)
        if organization:
            return (qs.filter(organization__isnull=True) | qs.filter(organization=organization)).distinct()
        return qs.filter(organization__isnull=True)

    def get_fields(self, request, obj=None):
        base_fields = ("name", "tel_nr", "strasse", "plz_ort", "e_mail", "is_active")
        if request.user.is_superuser:
            return ("organization", *base_fields)
        return base_fields

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return ()
        if obj and obj.organization_id is None:
            return ("name", "tel_nr", "strasse", "plz_ort", "e_mail", "is_active")
        return ()

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
        ("Grunddaten", {"fields": ("playground", "equipment_type", "name", "sequence_number", "inventory_number")}),
        ("Herstellung und Lieferung", {"fields": ("manufacturer", "supplier", "norm", "year_built", "build_date")}),
        ("Sanierung und Rückbau", {"fields": ("renovation_type", "recommended_renovation_year", "renovation_comment", "demolition_date")}),
        ("Administrative Prüfausnahme", {"fields": ("not_to_inspect", "not_to_inspect_reason"), "description": "Diese Einstellung wird durch die Organisation verwaltet und nimmt das Gerät aus neuen Kontrollprotokollen heraus."}),
        ("Prüfbarkeit während der Kontrolle", {"fields": ("not_inspectable", "not_inspectable_reason"), "description": "Diese Felder beschreiben, ob ein grundsätzlich prüfpflichtiges Gerät bei einer Kontrolle nicht geprüft werden konnte."}),
        ("Foto", {"fields": ("photo", "photo_upload")}),
        ("Koordinaten und Sichtbarkeit", {"fields": ("latitude", "longitude", "public_visible", "is_active")}),
    )
    list_display = ("name", "playground", "equipment_type", "sequence_number", "inventory_number", "not_to_inspect", "not_inspectable", "recommended_renovation_year", "demolition_date", "public_visible", "is_active")
    list_filter = ("playground__organization", "equipment_type", "supplier", "renovation_type", "not_to_inspect", "not_inspectable", "public_visible", "is_active")
    search_fields = ("name", "inventory_number", "manufacturer", "supplier__name", "norm", "playground__name")
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
                kwargs["queryset"] = Playground.objects.filter(organization=organization)
            elif db_field.name == "equipment_type":
                kwargs["queryset"] = (EquipmentType.objects.filter(organization__isnull=True) | EquipmentType.objects.filter(organization=organization)).distinct()
            elif db_field.name == "supplier":
                kwargs["queryset"] = (EquipmentSupplier.objects.filter(organization__isnull=True) | EquipmentSupplier.objects.filter(organization=organization)).filter(is_active=True).distinct()
            elif db_field.name == "photo":
                kwargs["queryset"] = db_field.remote_field.model.objects.filter(organization=organization)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        uploaded_photo = form.cleaned_data.get("photo_upload")
        if uploaded_photo:
            organization = obj.playground.organization
            obj.photo = create_image_asset_from_upload(uploaded_photo, organization)
        super().save_model(request, obj, form, change)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(PlaygroundSurface)
class PlaygroundSurfaceAdmin(admin.ModelAdmin):
    list_display = ("name", "playground", "surface_type", "public_visible", "is_active", "created_at")
    list_filter = ("playground__organization", "surface_type", "public_visible", "is_active")
    search_fields = ("name", "description", "playground__name")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        organization = get_user_organization(request.user)
        if organization:
            return qs.filter(playground__organization=organization)
        return qs.none()

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(PlaygroundAccessory)
class PlaygroundAccessoryAdmin(admin.ModelAdmin):
    list_display = ("name", "playground", "accessory_type", "public_visible", "is_active", "created_at")
    list_filter = ("playground__organization", "accessory_type", "public_visible", "is_active")
    search_fields = ("name", "description", "playground__name")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        organization = get_user_organization(request.user)
        if organization:
            return qs.filter(playground__organization=organization)
        return qs.none()

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
