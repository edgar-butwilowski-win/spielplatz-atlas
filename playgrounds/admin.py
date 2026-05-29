from django import forms
from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db.models import Q
from PIL import Image as PillowImage

from accounts.admin_utils import OrganizationAdminPermissionMixin, get_user_organization
from accounts.models import UserProfile
from accounts.utils import display_user
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


class InspectorChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return display_user(obj)


def inspector_queryset_for_organization(organization):
    User = get_user_model()

    if not organization:
        return User.objects.filter(is_active=True, is_superuser=True).order_by("last_name", "first_name", "email")

    return (
        User.objects
        .filter(is_active=True)
        .filter(
            Q(is_superuser=True)
            | Q(
                profile__organization=organization,
                profile__is_active_for_organization=True,
                profile__role__in=[
                    UserProfile.ROLE_INSPECTOR,
                    UserProfile.ROLE_ORG_ADMIN,
                ],
            )
        )
        .distinct()
        .order_by("last_name", "first_name", "email")
    )


class PlaygroundAdminForm(forms.ModelForm):
    photo_upload = forms.ImageField(
        label="Neues Foto hochladen",
        required=False,
        help_text="Optional. Wenn ein neues Foto hochgeladen wird, ersetzt es das bisherige Hauptfoto.",
    )
    default_visual_inspector = InspectorChoiceField(label="Default-Kontrolleur/in visuell", queryset=get_user_model().objects.none(), required=False)
    default_operational_inspector = InspectorChoiceField(label="Default-Kontrolleur/in operativ", queryset=get_user_model().objects.none(), required=False)
    default_annual_inspector = InspectorChoiceField(label="Default-Kontrolleur/in jährlich", queryset=get_user_model().objects.none(), required=False)

    class Meta:
        model = Playground
        fields = "__all__"

    def __init__(self, *args, request=None, **kwargs):
        super().__init__(*args, **kwargs)
        organization = None

        if self.instance and self.instance.pk:
            organization = self.instance.organization
        elif request and not request.user.is_superuser:
            organization = get_user_organization(request.user)

        if request and request.user.is_superuser and not organization:
            queryset = get_user_model().objects.filter(is_active=True).filter(
                Q(is_superuser=True)
                | Q(profile__is_active_for_organization=True, profile__role__in=[UserProfile.ROLE_INSPECTOR, UserProfile.ROLE_ORG_ADMIN])
            ).distinct().order_by("last_name", "first_name", "email")
        else:
            queryset = inspector_queryset_for_organization(organization)

        for field_name in (
            "default_visual_inspector",
            "default_operational_inspector",
            "default_annual_inspector",
        ):
            self.fields[field_name].queryset = queryset


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


class OrganizationScopedAdminMixin(OrganizationAdminPermissionMixin):
    organization_field = "organization"

    def get_object_organization(self, obj):
        if obj is None:
            return None
        return getattr(obj, self.organization_field, None)

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

        return qs.filter(**{self.organization_field: organization})


@admin.register(Playground)
class PlaygroundAdmin(OrganizationScopedAdminMixin, admin.ModelAdmin):
    form = PlaygroundAdminForm

    fieldsets = (
        ("Grunddaten", {"fields": ("organization", "uuid", "name", "slug", "number", "description", "construction_costs")}),
        ("Adresse und Lage", {"fields": ("address", "street_name", "house_number", "district", "latitude", "longitude")}),
        ("Inspektionen", {"fields": ("inspection_suspended_from", "inspection_suspended_until")}),
        ("Default-Kontrolleure", {"fields": ("default_visual_inspector", "default_operational_inspector", "default_annual_inspector"), "description": "Diese Personen werden bei neuen Kontrollaufträgen je Kontrollart automatisch als zuständige Kontrollperson voreingestellt."}),
        ("Foto", {"fields": ("photo", "photo_upload")}),
        ("Sichtbarkeit", {"fields": ("is_active", "public_visible")}),
    )
    list_display = ("name", "number", "uuid", "organization", "district", "default_visual_inspector", "default_operational_inspector", "default_annual_inspector", "public_visible", "is_active", "created_at")
    list_filter = ("organization", "public_visible", "is_active", "district")
    search_fields = ("name", "uuid", "number", "address", "street_name", "house_number", "district")
    prepopulated_fields = {"slug": ("name",)}
    autocomplete_fields = ("photo",)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)

        class RequestAwareForm(form):
            def __init__(self, *args, **inner_kwargs):
                inner_kwargs["request"] = request
                super().__init__(*args, **inner_kwargs)

        return RequestAwareForm

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


@admin.register(EquipmentType)
class EquipmentTypeAdmin(OrganizationScopedAdminMixin, admin.ModelAdmin):
    list_display = ("name", "code", "organization", "norm_reference", "is_standard", "standard_version", "is_locked", "is_active")
    list_filter = ("organization", "is_standard", "is_locked", "is_active", "standard_version")
    search_fields = ("name", "code", "norm_reference", "standard_version", "source_note")

    def get_queryset(self, request):
        return self.scope_queryset_to_organization(super().get_queryset(request), request)

    def get_fields(self, request, obj=None):
        if request.user.is_superuser:
            return ("organization", "name", "code", "norm_reference", "is_standard", "standard_version", "source_note", "is_locked", "is_active")
        return ("name", "code", "norm_reference", "is_active")

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            organization = get_user_organization(request.user)
            if organization:
                obj.organization = organization
                obj.is_standard = False
                obj.standard_version = ""
                obj.source_note = ""
                obj.is_locked = False
        super().save_model(request, obj, form, change)


@admin.register(EquipmentSupplier)
class EquipmentSupplierAdmin(OrganizationScopedAdminMixin, admin.ModelAdmin):
    list_display = ("name", "organization", "tel_nr", "plz_ort", "e_mail", "is_active", "created_at")
    list_filter = ("organization", "is_active")
    search_fields = ("name", "tel_nr", "strasse", "plz_ort", "e_mail", "organization__name")

    def get_queryset(self, request):
        return self.scope_queryset_to_organization(super().get_queryset(request), request)

    def get_fields(self, request, obj=None):
        base_fields = ("name", "tel_nr", "strasse", "plz_ort", "e_mail", "is_active")
        if request.user.is_superuser:
            return ("organization", *base_fields)
        return base_fields

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            organization = get_user_organization(request.user)
            if organization:
                obj.organization = organization
        super().save_model(request, obj, form, change)


@admin.register(PlayEquipment)
class PlayEquipmentAdmin(OrganizationAdminPermissionMixin, admin.ModelAdmin):
    form = PlayEquipmentAdminForm

    fieldsets = (
        ("Grunddaten", {"fields": ("playground", "equipment_type", "name", "sequence_number", "inventory_number")}),
        ("Lieferung und Norm", {"fields": ("supplier", "norm", "year_built", "build_date")}),
        ("Sanierung und Rückbau", {"fields": ("renovation_type", "recommended_renovation_year", "renovation_comment", "demolition_date")}),
        ("Administrative Prüfausnahme", {"fields": ("not_to_inspect", "not_to_inspect_reason"), "description": "Diese Einstellung wird durch die Organisation verwaltet und nimmt das Gerät aus neuen Kontrollprotokollen heraus."}),
        ("Prüfbarkeit während der Kontrolle", {"fields": ("not_inspectable", "not_inspectable_reason"), "description": "Diese Felder beschreiben, ob ein grundsätzlich prüfpflichtiges Gerät bei einer Kontrolle nicht geprüft werden konnte."}),
        ("Foto", {"fields": ("photo", "photo_upload")}),
        ("Koordinaten und Sichtbarkeit", {"fields": ("latitude", "longitude", "public_visible", "is_active")}),
    )
    list_display = ("name", "playground", "equipment_type", "supplier", "sequence_number", "inventory_number", "not_to_inspect", "not_inspectable", "recommended_renovation_year", "demolition_date", "public_visible", "is_active")
    list_filter = ("playground__organization", "equipment_type", "supplier", "renovation_type", "not_to_inspect", "not_inspectable", "public_visible", "is_active")
    search_fields = ("name", "inventory_number", "supplier__name", "norm", "playground__name")
    autocomplete_fields = ("playground", "equipment_type", "supplier", "photo")

    def get_object_organization(self, obj):
        return obj.playground.organization if obj and obj.playground_id else None

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
                kwargs["queryset"] = EquipmentType.objects.filter(organization=organization)
            elif db_field.name == "supplier":
                kwargs["queryset"] = EquipmentSupplier.objects.filter(organization=organization, is_active=True)
            elif db_field.name == "photo":
                kwargs["queryset"] = db_field.remote_field.model.objects.filter(organization=organization)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        uploaded_photo = form.cleaned_data.get("photo_upload")
        if uploaded_photo:
            organization = obj.playground.organization
            obj.photo = create_image_asset_from_upload(uploaded_photo, organization)
        super().save_model(request, obj, form, change)


@admin.register(PlaygroundSurface)
class PlaygroundSurfaceAdmin(OrganizationAdminPermissionMixin, admin.ModelAdmin):
    list_display = ("name", "playground", "surface_type", "public_visible", "is_active", "created_at")
    list_filter = ("playground__organization", "surface_type", "public_visible", "is_active")
    search_fields = ("name", "description", "playground__name")

    def get_object_organization(self, obj):
        return obj.playground.organization if obj and obj.playground_id else None

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
        if not request.user.is_superuser and organization and db_field.name == "playground":
            kwargs["queryset"] = Playground.objects.filter(organization=organization)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(PlaygroundAccessory)
class PlaygroundAccessoryAdmin(OrganizationAdminPermissionMixin, admin.ModelAdmin):
    list_display = ("name", "playground", "accessory_type", "public_visible", "is_active", "created_at")
    list_filter = ("playground__organization", "accessory_type", "public_visible", "is_active")
    search_fields = ("name", "description", "playground__name")

    def get_object_organization(self, obj):
        return obj.playground.organization if obj and obj.playground_id else None

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
        if not request.user.is_superuser and organization and db_field.name == "playground":
            kwargs["queryset"] = Playground.objects.filter(organization=organization)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
