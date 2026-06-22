import csv
from io import BytesIO

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.text import slugify

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from inspections.models import Defect, Inspection, InspectionAnswer
from .permissions import (
    get_active_profile_for_organization,
    require_defect_permission,
    require_inspection_permission,
    user_may_inspect,
    user_may_maintain,
)


CSV_DELIMITER = ";"


class Echo:
    def write(self, value):
        return value


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
    return timezone.localtime(value).strftime("%d.%m.%Y %H:%M") if hasattr(value, "tzinfo") else value.strftime("%d.%m.%Y")


def object_label(defect):
    if defect.equipment:
        return defect.equipment.name
    if defect.surface:
        return defect.surface.name
    if defect.accessory:
        return defect.accessory.name
    return "Allgemeiner Spielplatzmangel"


def filename_slug(*parts):
    value = "-".join(slugify(safe_text(part)) for part in parts if safe_text(part))
    return value or "export"


def get_profile_organization_or_raise(user):
    profile = getattr(user, "profile", None)
    if not profile or not profile.is_active_for_organization or not profile.organization_id:
        raise PermissionDenied("Keine aktive Organisation vorhanden.")
    return profile.organization


def restrict_inspections_for_user(user, queryset):
    if user.is_superuser:
        return queryset

    organization = get_profile_organization_or_raise(user)
    if not user_may_inspect(user, organization):
        raise PermissionDenied("Keine Berechtigung zum Exportieren von Kontrollen.")

    return queryset.filter(playground__organization=organization)


def restrict_defects_for_user(user, queryset):
    if user.is_superuser:
        return queryset

    organization = get_profile_organization_or_raise(user)
    if not (user_may_inspect(user, organization) or user_may_maintain(user, organization)):
        raise PermissionDenied("Keine Berechtigung zum Exportieren von Mängeln.")

    return queryset.filter(playground__organization=organization)


def apply_date_filters(request, queryset, field_name):
    date_from = request.GET.get("from")
    date_to = request.GET.get("to")

    if date_from:
        queryset = queryset.filter(**{f"{field_name}__gte": date_from})
    if date_to:
        queryset = queryset.filter(**{f"{field_name}__lte": date_to})

    return queryset


def csv_response(filename):
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response.write("\ufeff")
    return response


def pdf_response(buffer, filename):
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def pdf_styles():
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="AtlasTitle",
            parent=styles["Title"],
            alignment=TA_LEFT,
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            spaceAfter=8,
        )
    )
    styles.add(
        ParagraphStyle(
            name="AtlasSubtitle",
            parent=styles["Normal"],
            textColor=colors.HexColor("#475569"),
            fontSize=10,
            leading=14,
            spaceAfter=12,
        )
    )
    styles.add(
        ParagraphStyle(
            name="AtlasSection",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            spaceBefore=10,
            spaceAfter=6,
        )
    )
    styles.add(
        ParagraphStyle(
            name="AtlasSmall",
            parent=styles["Normal"],
            fontSize=8,
            leading=10,
        )
    )
    styles.add(
        ParagraphStyle(
            name="AtlasCell",
            parent=styles["Normal"],
            fontSize=8,
            leading=10,
            wordWrap="CJK",
        )
    )
    styles.add(
        ParagraphStyle(
            name="AtlasHeaderCell",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.white,
            alignment=TA_CENTER,
        )
    )
    return styles


def paragraph(value, style):
    return Paragraph(safe_text(value).replace("\n", "<br />"), style)


def add_key_value_table(story, rows, styles):
    table_data = [
        [paragraph(label, styles["AtlasHeaderCell"]), paragraph(value, styles["AtlasCell"])]
        for label, value in rows
    ]
    table = Table(table_data, colWidths=[45 * mm, 125 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#0F766E")),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 7 * mm))


def build_pdf(title, subtitle, story_builder, pagesize=A4):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=pagesize,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title=title,
    )
    styles = pdf_styles()
    story = [paragraph(title, styles["AtlasTitle"]), paragraph(subtitle, styles["AtlasSubtitle"])]
    story_builder(story, styles)
    doc.build(story)
    buffer.seek(0)
    return buffer


@login_required
def inspection_pdf(request, inspection_id):
    inspection = get_object_or_404(
        Inspection.objects.select_related(
            "playground",
            "playground__organization",
            "inspector",
            "completed_by",
        ),
        id=inspection_id,
    )
    require_inspection_permission(request.user, inspection.playground.organization)

    answers = (
        InspectionAnswer.objects
        .filter(inspection=inspection)
        .select_related("scope", "criterion")
        .prefetch_related("defects")
        .order_by("scope__sort_order", "criterion_area_snapshot", "criterion_title_snapshot")
    )

    title = f"Prüfprotokoll Kontrolle #{inspection.id}"
    subtitle = f"{inspection.archived_playground_name} · {inspection.archived_organization_name}"

    def build_story(story, styles):
        add_key_value_table(
            story,
            [
                ("Spielplatz", inspection.archived_playground_name),
                ("Organisation", inspection.archived_organization_name),
                ("Kontrollart", inspection.get_inspection_type_display()),
                ("Kontrolldatum", date_value(inspection.inspected_at)),
                ("Kontrollperson", user_display_name(inspection.inspector)),
                ("Status", inspection.get_status_display()),
                ("Ergebnis", inspection.get_result_display()),
                ("Abgeschlossen am", date_value(inspection.completed_at)),
                ("Abgeschlossen durch", user_display_name(inspection.completed_by)),
                ("Notizen", inspection.notes),
            ],
            styles,
        )

        story.append(paragraph("Prüfpunkte", styles["AtlasSection"]))
        table_data = [[
            paragraph("Bereich", styles["AtlasHeaderCell"]),
            paragraph("Prüfbereich", styles["AtlasHeaderCell"]),
            paragraph("Kriterium", styles["AtlasHeaderCell"]),
            paragraph("Antwort", styles["AtlasHeaderCell"]),
            paragraph("Kommentar", styles["AtlasHeaderCell"]),
            paragraph("Mängel", styles["AtlasHeaderCell"]),
        ]]

        for answer in answers:
            defects = answer.defect_summary_snapshot if inspection.status == Inspection.STATUS_COMPLETED else ", ".join(f"#{defect.id} {defect.get_status_display()}" for defect in answer.defects.all())
            table_data.append([
                paragraph(answer.archived_criterion_area, styles["AtlasCell"]),
                paragraph(answer.scope.archived_label if answer.scope else "", styles["AtlasCell"]),
                paragraph(answer.archived_criterion_title, styles["AtlasCell"]),
                paragraph(answer.get_answer_display(), styles["AtlasCell"]),
                paragraph(answer.comment, styles["AtlasCell"]),
                paragraph(defects, styles["AtlasCell"]),
            ])

        table = Table(
            table_data,
            colWidths=[25 * mm, 32 * mm, 52 * mm, 24 * mm, 45 * mm, 25 * mm],
            repeatRows=1,
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F766E")),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#CBD5E1")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        story.append(table)

    buffer = build_pdf(title, subtitle, build_story, pagesize=landscape(A4))
    filename = filename_slug("pruefprotokoll", inspection.archived_playground_name, inspection.id) + ".pdf"
    return pdf_response(buffer, filename)


@login_required
def defect_pdf(request, defect_id):
    defect = get_object_or_404(
        Defect.objects.select_related(
            "inspection",
            "inspection_answer",
            "inspection_answer__criterion",
            "inspection_answer__scope",
            "playground",
            "playground__organization",
            "equipment",
            "surface",
            "accessory",
        ),
        id=defect_id,
    )

    if not defect.playground:
        raise PermissionDenied("Dieser Mangel ist keinem Spielplatz zugeordnet.")

    require_defect_permission(request.user, defect.playground.organization)

    title = f"Mängelmeldung #{defect.id}"
    subtitle = f"{defect.playground.name} · {defect.playground.organization.name}"

    def build_story(story, styles):
        add_key_value_table(
            story,
            [
                ("Spielplatz", defect.playground.name),
                ("Organisation", defect.playground.organization.name),
                ("Betroffenes Objekt", object_label(defect)),
                ("Quelle", defect.get_source_type_display()),
                ("Gemeldet am", date_value(defect.reported_at)),
                ("Gemeldet durch", defect.reported_by_text),
                ("Status", defect.get_status_display()),
                ("Sicherheitsrisiko", "Ja" if defect.has_safety_risk else "Nein"),
                ("Dringlichkeit", defect.get_urgency_display() if defect.urgency else ""),
                ("Geplante Behebung", date_value(defect.planned_resolution_date)),
                ("Öffentlich sichtbar", "Ja" if defect.public_visible else "Nein"),
                ("Öffentlicher Hinweis", defect.public_note),
                ("Interne Beschreibung", defect.internal_description),
                ("Interne Notiz", defect.internal_note),
            ],
            styles,
        )

        if defect.inspection:
            story.append(paragraph("Bezug zur Kontrolle", styles["AtlasSection"]))
            criterion = ""
            if defect.inspection_answer and defect.inspection_answer.criterion:
                criterion = defect.inspection_answer.archived_criterion_title
            scope = ""
            if defect.inspection_answer and defect.inspection_answer.scope:
                scope = defect.inspection_answer.scope.archived_label
            add_key_value_table(
                story,
                [
                    ("Kontroll-ID", f"#{defect.inspection.id}"),
                    ("Kontrolldatum", date_value(defect.inspection.inspected_at)),
                    ("Prüfbereich", scope),
                    ("Prüfpunkt", criterion),
                ],
                styles,
            )

    buffer = build_pdf(title, subtitle, build_story)
    filename = filename_slug("maengelmeldung", defect.playground.name, defect.id) + ".pdf"
    return pdf_response(buffer, filename)


@login_required
def inspections_csv(request):
    queryset = (
        Inspection.objects
        .select_related("playground", "playground__organization", "inspector", "completed_by")
        .prefetch_related("answers", "defects")
        .order_by("-inspected_at", "-created_at")
    )
    queryset = restrict_inspections_for_user(request.user, queryset)
    queryset = apply_date_filters(request, queryset, "inspected_at")

    if request.GET.get("status"):
        queryset = queryset.filter(status=request.GET["status"])
    if request.GET.get("playground"):
        queryset = queryset.filter(playground_id=request.GET["playground"])

    response = csv_response("pruefprotokolle.csv")
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

    for inspection in queryset:
        writer.writerow([
            inspection.id,
            inspection.archived_organization_name,
            inspection.archived_playground_name,
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


@login_required
def defects_csv(request):
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
        .order_by("-has_safety_risk", "planned_resolution_date", "-created_at")
    )
    queryset = restrict_defects_for_user(request.user, queryset)
    queryset = apply_date_filters(request, queryset, "reported_at")

    if request.GET.get("status"):
        queryset = queryset.filter(status=request.GET["status"])
    if request.GET.get("playground"):
        queryset = queryset.filter(playground_id=request.GET["playground"])
    if request.GET.get("safety_risk") in {"0", "1"}:
        queryset = queryset.filter(has_safety_risk=request.GET["safety_risk"] == "1")
    if request.GET.get("public_visible") in {"0", "1"}:
        queryset = queryset.filter(public_visible=request.GET["public_visible"] == "1")

    response = csv_response("maengelmeldungen.csv")
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

    for defect in queryset:
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
            defect.inspection_answer.scope.archived_label if defect.inspection_answer and defect.inspection_answer.scope else "",
            defect.inspection_answer.archived_criterion_title if defect.inspection_answer and defect.inspection_answer.criterion else "",
            defect.internal_description,
            defect.internal_note,
            defect.public_note,
        ])

    return response
