import csv
from datetime import date

from django.contrib import admin, messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django import forms
from django.http import HttpResponse
from django.shortcuts import render
from django.utils import timezone

from inspections.models import Defect, Inspection
from .permissions import require_org_admin_permission


CSV_DELIMITER = ";"


class CsvExportPeriodForm(forms.Form):
    date_from = forms.DateField(
        label="Von",
        widget=forms.DateInput(attrs={"type": "date"}),
        help_text="Erster Tag des Exportzeitraums.",
    )
    date_to = forms.DateField(
        label="Bis",
        widget=forms.DateInput(attrs={"type": "date"}),
        help_text="Letzter Tag des Exportzeitraums. Der Zeitraum darf maximal ein Kalenderjahr umfassen.",
    )

    def clean(self):
        cleaned_data = super().clean()
        date_from = cleaned_data.get("date_from")
        date_to = cleaned_data.get("date_to")

        if not date_from or not date_to:
            return cleaned_data

        if date_to < date_from:
            raise forms.ValidationError("Das Bis-Datum darf nicht vor dem Von-Datum liegen.")

        if date_to > add_one_calendar_year(date_from):
            raise forms.ValidationError(
                "Der Exportzeitraum darf maximal ein Kalenderjahr umfassen. "
                "Bitte wählen Sie einen kürzeren Zeitraum."
            )

        return cleaned_data


def add_one_calendar_year(value):
    try:
        return value.replace(year=value.year + 1)
    except ValueError:
        return date(value.year + 1, 2, 28)


def get_admin_export_organization(user):
    if user.is_superuser:
        return None

    profile = getattr(user, "profile", None)
    if not profile or not profile.is_active_for_organization or not profile.organization:
        raise PermissionDenied("Keine aktive Organisation vorhanden.")

    require_org_admin_permission(user, profile.organization)
    return profile.organization


def safe_text(value):
    if value is None:
        return ""
    return str(value)


def user_display_name(user):
    if not user:
        return ""
    return user.get_full_name() or user.get_username()


def date_value(value):
    if not value:
        return ""
    if hasattr(value, "tzinfo") and value.tzinfo is not None:
        return timezone.localtime(value).strftime("%d.%m.%Y %H:%M")
    return value.strftime("%d.%m.%Y")


def object_label(defect):
    if defect.equipment:
        return defect.equipment.name
    if defect.surface:
        return defect.surface.name
    if defect.accessory:
        return defect.accessory.name
    return "Allgemeiner Spielplatzmangel"


def csv_response(filename):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.write("\ufeff")
    return response


def export_context(request, title, description):
    return {
        **admin.site.each_context(request),
        "title": title,
        "description": description,
    }


@login_required
def inspections_admin_csv_export(request):
    organization = get_admin_export_organization(request.user)

    if request.method == "POST":
        form = CsvExportPeriodForm(request.POST)
        if form.is_valid():
            date_from = form.cleaned_data["date_from"]
            date_to = form.cleaned_data["date_to"]
            return inspections_csv_response(organization, date_from, date_to)
        messages.error(request, "Der CSV-Export konnte nicht erstellt werden. Bitte prüfen Sie die Datumsangaben.")
    else:
        form = CsvExportPeriodForm()

    context = export_context(
        request,
        "Prüfprotokolle als CSV exportieren",
        "Exportiert Prüfprotokolle für einen frei wählbaren Zeitraum von maximal einem Kalenderjahr.",
    )
    context["form"] = form
    context["opts"] = Inspection._meta
    return render(request, "admin/csv_export_period_form.html", context)


@login_required
def defects_admin_csv_export(request):
    organization = get_admin_export_organization(request.user)

    if request.method == "POST":
        form = CsvExportPeriodForm(request.POST)
        if form.is_valid():
            date_from = form.cleaned_data["date_from"]
            date_to = form.cleaned_data["date_to"]
            return defects_csv_response(organization, date_from, date_to)
        messages.error(request, "Der CSV-Export konnte nicht erstellt werden. Bitte prüfen Sie die Datumsangaben.")
    else:
        form = CsvExportPeriodForm()

    context = export_context(
        request,
        "Mängelmeldungen als CSV exportieren",
        "Exportiert Mängelmeldungen für einen frei wählbaren Zeitraum von maximal einem Kalenderjahr.",
    )
    context["form"] = form
    context["opts"] = Defect._meta
    return render(request, "admin/csv_export_period_form.html", context)


def inspections_csv_response(organization, date_from, date_to):
    queryset = (
        Inspection.objects
        .select_related("playground", "playground__organization", "inspector", "completed_by")
        .prefetch_related("answers", "defects")
        .filter(inspected_at__gte=date_from, inspected_at__lte=date_to)
        .order_by("-inspected_at", "-created_at")
    )

    if organization:
        queryset = queryset.filter(playground__organization=organization)

    response = csv_response(f"pruefprotokolle_{date_from.isoformat()}_{date_to.isoformat()}.csv")
    writer = csv.writer(response, delimiter=CSV_DELIMITER)
    writer.writerow([
        "ID",
        "Organisation",
        "Spielplatz",
        "Kontrollart",
        "Kontrolldatum",
        "Kontrollperson",
        "Status",
        "Ergebnis",
        "Prüfpunkte",
        "Mängel",
        "Abgeschlossen am",
        "Abgeschlossen durch",
        "Notizen",
    ])

    for inspection in queryset.iterator(chunk_size=1000):
        writer.writerow([
            inspection.id,
            inspection.playground.organization.name,
            inspection.playground.name,
            inspection.get_inspection_type_display(),
            date_value(inspection.inspected_at),
            user_display_name(inspection.inspector),
            inspection.get_status_display(),
            inspection.get_result_display(),
            inspection.answers.count(),
            inspection.defects.count(),
            date_value(inspection.completed_at),
            user_display_name(inspection.completed_by),
            inspection.notes,
        ])

    return response


def defects_csv_response(organization, date_from, date_to):
    queryset = (
        Defect.objects
        .select_related(
            "inspection",
            "inspection_answer",
            "inspection_answer__criterion",
            "inspection_answer__scope",
            "playground",
            "playground__organization",
            "equipment",
            "surface",
            "accessory",
        )
        .filter(reported_at__date__gte=date_from, reported_at__date__lte=date_to)
        .order_by("-has_safety_risk", "planned_resolution_date", "-created_at")
    )

    if organization:
        queryset = queryset.filter(playground__organization=organization)

    response = csv_response(f"maengelmeldungen_{date_from.isoformat()}_{date_to.isoformat()}.csv")
    writer = csv.writer(response, delimiter=CSV_DELIMITER)
    writer.writerow([
        "ID",
        "Organisation",
        "Spielplatz",
        "Betroffenes Objekt",
        "Quelle",
        "Gemeldet am",
        "Gemeldet durch",
        "Status",
        "Sicherheitsrisiko",
        "Dringlichkeit",
        "Geplante Behebung",
        "Öffentlich sichtbar",
        "Kontroll-ID",
        "Prüfbereich",
        "Prüfpunkt",
        "Interne Beschreibung",
        "Interne Notiz",
        "Öffentlicher Hinweis",
    ])

    for defect in queryset.iterator(chunk_size=1000):
        writer.writerow([
            defect.id,
            defect.playground.organization.name if defect.playground else "",
            defect.playground.name if defect.playground else "",
            object_label(defect),
            defect.get_source_type_display(),
            date_value(defect.reported_at),
            defect.reported_by_text,
            defect.get_status_display(),
            "Ja" if defect.has_safety_risk else "Nein",
            defect.get_urgency_display() if defect.urgency else "",
            date_value(defect.planned_resolution_date),
            "Ja" if defect.public_visible else "Nein",
            defect.inspection_id or "",
            defect.inspection_answer.scope.label if defect.inspection_answer and defect.inspection_answer.scope else "",
            defect.inspection_answer.criterion.title if defect.inspection_answer and defect.inspection_answer.criterion else "",
            defect.internal_description,
            defect.internal_note,
            defect.public_note,
        ])

    return response
