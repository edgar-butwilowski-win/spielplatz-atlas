from django import forms
from django.contrib import admin, messages
from django.http import HttpResponseRedirect
from django.urls import path, reverse
from django.utils.html import format_html

from accounts.admin_utils import get_user_organization

from .quartier_import import QuartierImportError, import_quartiere_from_import_config
from .quartier_models import Quartier, QuartierImport


class QuartierImportAdminForm(forms.ModelForm):
    run_import_now = forms.BooleanField(
        label="Quartiere jetzt importieren",
        required=False,
        help_text="Nach dem Speichern werden die Quartiere direkt aus der GeoJSON-Datei oder dem WFS importiert.",
    )

    class Meta:
        model = QuartierImport
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        geojson_file = cleaned_data.get("geojson_file")
        wfs_endpoint = cleaned_data.get("wfs_endpoint")

        if geojson_file and wfs_endpoint:
            raise forms.ValidationError(
                "Bitte entweder eine GeoJSON-Datei oder einen WFS-Endpoint angeben, nicht beides."
            )

        if cleaned_data.get("run_import_now") and not geojson_file and not wfs_endpoint:
            raise forms.ValidationError(
                "Für den Import braucht es eine GeoJSON-Datei oder einen WFS-Endpoint."
            )

        return cleaned_data


@admin.register(Quartier)
class QuartierAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "is_active", "source", "imported_at")
    list_filter = ("organization", "is_active")
    search_fields = ("name", "source", "organization__name")
    readonly_fields = ("imported_at",)

    fieldsets = (
        ("Grunddaten", {
            "fields": ("organization", "name", "is_active"),
        }),
        ("Geometrie", {
            "fields": ("geom",),
            "description": "GeoJSON-Geometrie des Quartiers.",
        }),
        ("Import", {
            "fields": ("source", "imported_at"),
        }),
    )

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
                if field != "organization"
            )
            filtered_fieldsets.append((title, {**options, "fields": fields}))

        return tuple(filtered_fieldsets)

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            organization = get_user_organization(request.user)
            if organization:
                obj.organization = organization

        super().save_model(request, obj, form, change)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(QuartierImport)
class QuartierImportAdmin(admin.ModelAdmin):
    form = QuartierImportAdminForm
    list_display = ("organization", "source_display", "replace_existing", "updated_at", "import_button")
    list_filter = ("organization", "replace_existing")
    readonly_fields = ("last_import_message", "created_at", "updated_at")

    fieldsets = (
        ("Organisation", {
            "fields": ("organization",),
        }),
        ("Quelle", {
            "fields": ("geojson_file", "wfs_endpoint"),
            "description": (
                "Der Import erwartet den Quartiernamen im Attribut 'Quartiername' "
                "und die Geometrie im Attribut 'geom'. Bei GeoJSON wird zusätzlich "
                "das Standardfeld 'geometry' akzeptiert."
            ),
        }),
        ("Import", {
            "fields": ("replace_existing", "run_import_now", "last_import_message"),
        }),
        ("System", {
            "fields": ("created_at", "updated_at"),
        }),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "<path:object_id>/import-quartiere/",
                self.admin_site.admin_view(self.import_quartiere_view),
                name="playgrounds_quartierimport_import_quartiere",
            ),
        ]
        return custom_urls + urls

    def source_display(self, obj):
        if obj.geojson_file:
            return obj.geojson_file.name
        return obj.wfs_endpoint or "-"
    source_display.short_description = "Quelle"

    def import_button(self, obj):
        url = reverse("admin:playgrounds_quartierimport_import_quartiere", args=[obj.pk])
        return format_html('<a class="button" href="{}">Quartiere importieren</a>', url)
    import_button.short_description = "Aktion"

    def import_quartiere_view(self, request, object_id):
        import_config = self.get_object(request, object_id)

        if not import_config:
            self.message_user(request, "Import-Konfiguration nicht gefunden.", level=messages.ERROR)
            return HttpResponseRedirect("../../")

        if not self.has_change_permission(request, import_config):
            self.message_user(request, "Keine Berechtigung für diesen Import.", level=messages.ERROR)
            return HttpResponseRedirect("../../")

        self.run_import(request, import_config)
        return HttpResponseRedirect("../../")

    def run_import(self, request, obj):
        try:
            result = import_quartiere_from_import_config(obj)
        except QuartierImportError as exc:
            obj.last_import_message = str(exc)
            obj.save(update_fields=["last_import_message", "updated_at"])
            self.message_user(request, str(exc), level=messages.ERROR)
            return
        except Exception as exc:
            message = f"Import fehlgeschlagen: {exc}"
            obj.last_import_message = message
            obj.save(update_fields=["last_import_message", "updated_at"])
            self.message_user(request, message, level=messages.ERROR)
            return

        message = (
            f"Quartier-Import abgeschlossen: {result['imported']} importiert, "
            f"{result['skipped']} übersprungen."
        )

        if result["errors"]:
            message += " Hinweise: " + " | ".join(result["errors"][:5])

        obj.last_import_message = message
        obj.save(update_fields=["last_import_message", "updated_at"])
        self.message_user(request, message, level=messages.SUCCESS)

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            organization = get_user_organization(request.user)
            if organization:
                obj.organization = organization

        super().save_model(request, obj, form, change)

        if form.cleaned_data.get("run_import_now"):
            self.run_import(request, obj)

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
                if field != "organization"
            )
            filtered_fieldsets.append((title, {**options, "fields": fields}))

        return tuple(filtered_fieldsets)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
