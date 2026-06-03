import json
from datetime import date, timedelta

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count, Max, Q
from django.shortcuts import render
from django.utils import timezone

from inspections.models import Defect, Inspection, InspectionTask, MaintenanceAction
from playgrounds.models import PlayEquipment, Playground
from tenants.models import Organization

from .permissions import get_active_profile_for_organization

RECENT_INSPECTION_DAYS = 365
DASHBOARD_MONTHS = 12
DASHBOARD_WEEKS = 12
MIN_SUPPLIER_EQUIPMENT_COUNT = 5
SUPPLIER_RATE_LIMIT = 10
EXCLUDED_DASHBOARD_DEFECT_STATUSES = [
    Defect.STATUS_IN_PROGRESS,
    Defect.STATUS_VERIFIED,
]
DASHBOARD_INSPECTION_TASK_STATUS_CHOICES = [
    (InspectionTask.STATUS_OPEN, "Open"),
    (InspectionTask.STATUS_PLANNED, "Planned"),
    (InspectionTask.STATUS_SUSPENDED, "Suspended"),
]


def dashboard_json(data):
    return json.dumps(data, cls=DjangoJSONEncoder)


def get_dashboard_scope(user):
    if user.is_superuser:
        return {"organization": None, "is_superadmin": True, "can_manage": True, "can_inspect": True, "can_maintain": True, "can_view_internal": True}
    profile = getattr(user, "profile", None)
    if not profile:
        return None
    profile = get_active_profile_for_organization(user, profile.organization)
    if not profile:
        return None
    return {"organization": profile.organization, "is_superadmin": False, "can_manage": profile.may_manage_organization, "can_inspect": profile.may_inspect, "can_maintain": profile.may_maintain, "can_view_internal": profile.may_view_internal}


def choice_count_map(queryset, field_name, choices):
    raw_counts = queryset.values(field_name).annotate(count=Count("id"))
    counts = {entry[field_name]: entry["count"] for entry in raw_counts}
    return [{"key": key, "label": label, "count": counts.get(key, 0)} for key, label in choices]


def inspection_task_status_count_map(inspection_tasks):
    counts = {key: 0 for key, _label in DASHBOARD_INSPECTION_TASK_STATUS_CHOICES}
    for task in inspection_tasks:
        key = task.effective_status
        if key in counts:
            counts[key] += 1
    return [
        {"key": key, "label": label, "count": counts[key]}
        for key, label in DASHBOARD_INSPECTION_TASK_STATUS_CHOICES
    ]


def top_playground_defect_counts(defects):
    return list(defects.values("playground__name", "playground__organization__name").annotate(count=Count("id")).order_by("-count", "playground__organization__name", "playground__name")[:10])


def build_playgrounds_without_recent_completed_inspection(playgrounds):
    cutoff_date = timezone.localdate() - timedelta(days=RECENT_INSPECTION_DAYS)
    return list(playgrounds.annotate(latest_completed_inspection=Max("inspections__inspected_at", filter=Q(inspections__status=Inspection.STATUS_COMPLETED))).filter(Q(latest_completed_inspection__isnull=True) | Q(latest_completed_inspection__lt=cutoff_date)).select_related("organization").order_by("organization__name", "name")[:25])


def month_starts():
    today = timezone.localdate()
    current = date(today.year, today.month, 1)
    months = []
    for offset in range(DASHBOARD_MONTHS - 1, -1, -1):
        year = current.year
        month = current.month - offset
        while month <= 0:
            year -= 1
            month += 12
        months.append(date(year, month, 1))
    return months


def month_label(value):
    return f"{value.year}-{value.month:02d}"


def month_matches(value, month):
    if hasattr(value, "date"):
        value = value.date()
    return value and value.year == month.year and value.month == month.month


def monthly_counts(items, months, date_attr):
    return [sum(1 for item in items if month_matches(getattr(item, date_attr), month)) for month in months]


def chart_series(label, data):
    return {"label": label, "data": data}


def week_start(value):
    return value - timedelta(days=value.weekday())


def week_label(value):
    iso_year, iso_week, _ = value.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def build_time_charts(defects, inspections, maintenance_actions, inspection_tasks):
    months = month_starts()
    defect_list = list(defects)
    inspection_list = list(inspections)
    action_list = list(maintenance_actions)
    completed_inspections = [item for item in inspection_list if item.status == Inspection.STATUS_COMPLETED]
    verified_defects = [item for item in defect_list if item.status == Defect.STATUS_VERIFIED]
    safety_defects = [item for item in defect_list if item.has_safety_risk]
    week0 = week_start(timezone.localdate())
    weeks = [week0 + timedelta(days=7 * offset) for offset in range(DASHBOARD_WEEKS)]
    task_counts = {key: {week_label(week): 0 for week in weeks} for key, _label in InspectionTask.STATUS_CHOICES}
    for task in inspection_tasks:
        key = task.effective_status
        label = week_label(week_start(task.due_date))
        if key in task_counts and label in task_counts[key]:
            task_counts[key][label] += 1
    return {
        "monthLabels": [month_label(month) for month in months],
        "defectTrend": [chart_series("New defects", monthly_counts(defect_list, months, "reported_at")), chart_series("Geprüfte / abgeschlossene Mängel", monthly_counts(verified_defects, months, "updated_at"))],
        "safetyRiskTrend": [chart_series("New safety-risk defects", monthly_counts(safety_defects, months, "reported_at"))],
        "inspectionTypeTrend": [chart_series(label, monthly_counts([item for item in completed_inspections if item.inspection_type == key], months, "inspected_at")) for key, label in Inspection.TYPE_CHOICES],
        "inspectionResultTrend": [chart_series(label, monthly_counts([item for item in completed_inspections if item.result == key], months, "inspected_at")) for key, label in Inspection.RESULT_CHOICES],
        "weekLabels": [week_label(week) for week in weeks],
        "taskPlanning": [chart_series(label, list(task_counts[key].values())) for key, label in InspectionTask.STATUS_CHOICES],
        "maintenanceTrend": [chart_series("Planned maintenance actions", monthly_counts(action_list, months, "planned_date")), chart_series("Completed maintenance actions", monthly_counts(action_list, months, "completed_date"))],
    }


def supplier_rate_chart(rows, value_key):
    visible_rows = [row for row in rows if row["equipment_count"] >= MIN_SUPPLIER_EQUIPMENT_COUNT]
    visible_rows = sorted(visible_rows, key=lambda row: (-row[value_key], row["supplier_name"]))[:SUPPLIER_RATE_LIMIT]
    return {
        "labels": [row["supplier_name"] for row in visible_rows],
        "data": [row[value_key] for row in visible_rows],
        "defects": [row["defect_count"] for row in visible_rows],
        "safetyDefects": [row["safety_defect_count"] for row in visible_rows],
        "equipment": [row["equipment_count"] for row in visible_rows],
        "minimumEquipment": MIN_SUPPLIER_EQUIPMENT_COUNT,
        "limit": SUPPLIER_RATE_LIMIT,
    }


def build_supplier_rate_rows(equipment):
    rows = []
    for item in equipment.filter(supplier__isnull=False).values("supplier_id", "supplier__name").annotate(
        equipment_count=Count("id", distinct=True),
        defect_count=Count("defects"),
        safety_defect_count=Count("defects", filter=Q(defects__has_safety_risk=True)),
    ):
        equipment_count = item["equipment_count"] or 0
        defect_count = item["defect_count"] or 0
        safety_defect_count = item["safety_defect_count"] or 0
        if equipment_count <= 0:
            continue
        rows.append({
            "supplier_name": item["supplier__name"] or "Unknown supplier",
            "equipment_count": equipment_count,
            "defect_count": defect_count,
            "safety_defect_count": safety_defect_count,
            "defect_rate": round(defect_count * 100 / equipment_count, 1),
            "safety_defect_rate": round(safety_defect_count * 100 / equipment_count, 1),
        })
    return rows


def build_equipment_charts(defects, equipment):
    supplier_rows = list(defects.filter(equipment__isnull=False).values("equipment__supplier__name").annotate(count=Count("id")).order_by("-count", "equipment__supplier__name")[:12])
    supplier_rate_rows = build_supplier_rate_rows(equipment)
    bucket_names = ["0-5 years", "6-10 years", "11-15 years", "16-20 years", "21-30 years", "Over 30 years", "Unknown age"]
    buckets = {name: {"equipment": 0, "defects": 0} for name in bucket_names}
    current_year = timezone.localdate().year
    for item in equipment.annotate(defect_count=Count("defects")):
        build_date = item.build_date or item.year_built
        bucket = "Unknown age"
        if build_date:
            age = max(0, current_year - build_date.year)
            if age <= 5:
                bucket = "0-5 years"
            elif age <= 10:
                bucket = "6-10 years"
            elif age <= 15:
                bucket = "11-15 years"
            elif age <= 20:
                bucket = "16-20 years"
            elif age <= 30:
                bucket = "21-30 years"
            else:
                bucket = "Over 30 years"
        buckets[bucket]["equipment"] += 1
        buckets[bucket]["defects"] += item.defect_count
    return {
        "supplierDefects": {"labels": [row["equipment__supplier__name"] or "Unknown supplier" for row in supplier_rows], "data": [row["count"] for row in supplier_rows]},
        "supplierDefectRate": supplier_rate_chart(supplier_rate_rows, "defect_rate"),
        "supplierSafetyDefectRate": supplier_rate_chart(supplier_rate_rows, "safety_defect_rate"),
        "equipmentAgeDefects": {"labels": bucket_names, "series": [chart_series("Defects", [buckets[name]["defects"] for name in bucket_names]), chart_series("Play equipment", [buckets[name]["equipment"] for name in bucket_names])]},
    }


def build_dashboard_context(scope):
    organization = scope["organization"]
    playgrounds = Playground.objects.select_related("organization")
    defects = Defect.objects.select_related("playground", "playground__organization", "equipment", "equipment__supplier")
    inspections = Inspection.objects.select_related("playground", "playground__organization")
    maintenance_actions = MaintenanceAction.objects.select_related("defect", "defect__playground", "defect__playground__organization")
    inspection_tasks = InspectionTask.objects.select_related("playground", "organization")
    equipment = PlayEquipment.objects.select_related("playground", "playground__organization", "supplier")
    if organization is not None:
        playgrounds = playgrounds.filter(organization=organization)
        defects = defects.filter(playground__organization=organization)
        inspections = inspections.filter(playground__organization=organization)
        maintenance_actions = maintenance_actions.filter(defect__playground__organization=organization)
        inspection_tasks = inspection_tasks.filter(organization=organization)
        equipment = equipment.filter(playground__organization=organization)
    open_defects = defects.exclude(status__in=[Defect.STATUS_DONE, Defect.STATUS_VERIFIED])
    safety_risk_defects = open_defects.filter(has_safety_risk=True)
    planned_maintenance_actions = maintenance_actions.exclude(status__in=[MaintenanceAction.STATUS_DONE, MaintenanceAction.STATUS_CANCELLED])
    completed_inspections = inspections.filter(status=Inspection.STATUS_COMPLETED)
    draft_inspections = inspections.filter(status=Inspection.STATUS_DRAFT)
    defects_by_status = choice_count_map(
        defects.exclude(status__in=EXCLUDED_DASHBOARD_DEFECT_STATUSES),
        "status",
        [choice for choice in Defect.STATUS_CHOICES if choice[0] not in EXCLUDED_DASHBOARD_DEFECT_STATUSES],
    )
    inspections_by_status = inspection_task_status_count_map(inspection_tasks)
    time_charts = build_time_charts(defects, inspections, maintenance_actions, inspection_tasks)
    equipment_charts = build_equipment_charts(defects, equipment)
    organizations_count = Organization.objects.count() if organization is None else 1
    return {**scope, "organizations_count": organizations_count, "playgrounds_count": playgrounds.count(), "active_playgrounds_count": playgrounds.filter(is_active=True).count(), "public_playgrounds_count": playgrounds.filter(is_active=True, public_visible=True).count(), "open_defects_count": open_defects.count(), "verified_defects_count": defects.filter(status=Defect.STATUS_VERIFIED).count(), "safety_risk_defects_count": safety_risk_defects.count(), "planned_maintenance_actions_count": planned_maintenance_actions.count(), "completed_inspections_count": completed_inspections.count(), "draft_inspections_count": draft_inspections.count(), "defects_by_status_json": dashboard_json(defects_by_status), "defects_by_source_json": dashboard_json(choice_count_map(defects, "source_type", Defect.SOURCE_CHOICES)), "maintenance_by_status_json": dashboard_json(choice_count_map(maintenance_actions, "status", MaintenanceAction.STATUS_CHOICES)), "inspections_by_type_json": dashboard_json(choice_count_map(inspections, "inspection_type", Inspection.TYPE_CHOICES)), "inspections_by_status_json": dashboard_json(inspections_by_status), "time_charts_json": dashboard_json(time_charts), "equipment_charts_json": dashboard_json(equipment_charts), "latest_inspections": list(completed_inspections.select_related("playground", "playground__organization", "inspector").order_by("-inspected_at", "-completed_at", "-created_at")[:10]), "open_safety_risk_defects": list(safety_risk_defects.select_related("playground", "playground__organization", "equipment", "surface", "accessory").order_by("planned_resolution_date", "-created_at")[:10]), "planned_maintenance_actions": list(planned_maintenance_actions.select_related("defect", "defect__playground", "defect__playground__organization").order_by("planned_date", "-created_at")[:10]), "defects_by_playground": top_playground_defect_counts(open_defects), "playgrounds_without_recent_completed_inspection": build_playgrounds_without_recent_completed_inspection(playgrounds), "recent_inspection_days": RECENT_INSPECTION_DAYS}


@login_required
def dashboard(request):
    scope = get_dashboard_scope(request.user)
    if not scope or not scope["can_view_internal"]:
        raise PermissionDenied("Keine Berechtigung für das interne Dashboard.")
    return render(request, "internal/dashboard.html", build_dashboard_context(scope))
