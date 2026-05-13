# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

from django import forms
from django.contrib import admin
from django.core.exceptions import ValidationError

from accounts.admin_utils import get_user_organization

from .document_models import PlaygroundDocument
from .models import Playground


class PlaygroundDocumentAdminForm(forms.ModelForm):
    upload_file = forms.FileField(
        label="PDF-Dokument hochladen",
        required=False,
        help_text="Erlaubt sind ausschliesslich PDF-Dokumente.",
    )

    class Meta:
        model = PlaygroundDocument
        fields = (
            "playground",
            "document_type",
            "upload_file",
        )

    def clean_upload_file(self):
        upload_file = self.cleaned_data.get("upload_file")

        if not upload_file:
            if self.instance and self.instance.pk:
                return upload_file

            raise ValidationError("Bitte ein PDF-Dokument hochladen.")

        content_type = upload_file.content_type or ""

        if content_type != "application/pdf":
            raise ValidationError("Bitte ausschliesslich PDF-Dokumente hochladen.")

        if not upload_file.name.lower().endswith(".pdf"):
            raise ValidationError("Bitte eine Datei mit der Endung .pdf hochladen.")

        return upload_file


@admin.register(PlaygroundDocument)
class PlaygroundDocumentAdmin(admin.ModelAdmin):
    form = PlaygroundDocumentAdminForm

    list_display = (
        "id",
        "document_type",
        "playground",
        "size_bytes",
        "created_at",
    )
    list_filter = (
        "document_type",
        "playground__organization",
        "created_at",
    )
    search_fields = (
        "=id",
        "playground__name",
        "playground__organization__name",
    )
    autocomplete_fields = ("playground",)
    readonly_fields = (
        "id",
        "mime_type",
        "size_bytes",
        "sha256",
        "created_at",
    )

    fieldsets = (
        ("Zuordnung", {
            "fields": (
                "id",
                "playground",
                "document_type",
            )
        }),
        ("PDF-Dokument", {
            "fields": (
                "upload_file",
                "mime_type",
                "size_bytes",
                "sha256",
                "created_at",
            )
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request).select_related(
            "playground",
            "playground__organization",
        )

        if request.user.is_superuser:
            return qs

        organization = get_user_organization(request.user)

        if organization:
            return qs.filter(playground__organization=organization)

        return qs.none()

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "playground" and not request.user.is_superuser:
            organization = get_user_organization(request.user)

            if organization:
                kwargs["queryset"] = Playground.objects.filter(
                    organization=organization,
                )

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        upload_file = form.cleaned_data.get("upload_file")

        if upload_file:
            binary_data = upload_file.read()
            obj.mime_type = "application/pdf"
            obj.size_bytes = len(binary_data)
            obj.sha256 = PlaygroundDocument.calculate_sha256(binary_data)
            obj.data = binary_data

        super().save_model(request, obj, form, change)

    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True

        organization = get_user_organization(request.user)

        if obj is None:
            return organization is not None

        return bool(
            organization
            and obj.playground.organization_id == organization.id
        )

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True

        organization = get_user_organization(request.user)

        if obj is None:
            return organization is not None

        return bool(
            organization
            and obj.playground.organization_id == organization.id
        )

    def has_add_permission(self, request):
        if request.user.is_superuser:
            return True

        return get_user_organization(request.user) is not None

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
