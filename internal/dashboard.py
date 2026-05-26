import json
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Count, Max, Q
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone

from inspections.models import Defect, Inspection, MaintenanceAction
from playgrounds.models import Playground
from tenants.models import Organization

from .permissions import get_active_profile_for_organization

RECENT_INSPECTION_DAYS = 365


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


def build_dashboard_context(scope):
    organization = scope["organization"]
    playgrounds = Playground.objects.select_related("organization")
    defects = Defect.objects.select_related("playground", "playground__organization")
    inspections = Inspection.objects.select_related("playground", "playground__organization")
    maintenance_actions = MaintenanceAction.objects.select_related("defect", "defect__playground", "defect__playground__organization")
    if organization is not None:
        playgrounds = playgrounds.filter(organization=organization)
        defects = defects.filter(playground__organization=organization)
        inspections = inspections.filter(playground__organization=organization)
        maintenance_actions = maintenance_actions.filter(defect__playground__organization=organization)
    open_defects = defects.exclude(status__in=[Defect.STATUS_DONE, Defect.STATUS_VERIFIED])
    safety_risk_defects = open_defects.filter(has_safety_risk=True)
    planned_maintenance_actions = maintenance_actions.exclude(status__in=[MaintenanceAction.STATUS_DONE, MaintenanceAction.STATUS_CANCELLED])
    completed_inspections = inspections.filter(status=Inspection.STATUS_COMPLETED)
    draft_inspections = inspections.filter(status=Inspection.STATUS_DRAFT)
    defects_by_status = choice_count_map(defects.exclude(status=Defect.STATUS_VERIFIED), "status", [c for c in Defect.STATUS_CHOICES if c[0] != Defect.STATUS_VERIFIED])
    defects_by_source = choice_count_map(defects, "source_type", Defect.SOURCE_CHOICES)
    inspections_by_type = choice_count_map(inspections, "inspection_type", Inspection.TYPE_CHOICES)
    inspections_by_status = choice_count_map(inspections, "status", Inspection.STATUS_CHOICES)
    return {**scope, "organizations_count": Organization.objects.count() if organization is None else 1, "active_playgrounds_count": playgrounds.filter(is_active=True).count(), "open_defects_count": open_defects.count(), "verified_defects_count": defects.filter(status=Defect.STATUS_VERIFIED).count(), "safety_risk_defects_count": safety_risk_defects.count(), "planned_maintenance_actions_count": planned_maintenance_actions.count(), "completed_inspections_count": completed_inspections.count(), "draft_inspections_count": draft_inspections.count(), "defects_by_status_json": dashboard_json(defects_by_status), "defects_by_source_json": dashboard_json(defects_by_source), "inspections_by_type_json": dashboard_json(inspections_by_type), "inspections_by_status_json": dashboard_json(inspections_by_status), "recent_inspection_days": RECENT_INSPECTION_DAYS}


@login_required
def dashboard(request):
    scope = get_dashboard_scope(request.user)
    if not scope or not scope["can_view_internal"]:
        raise PermissionDenied("Keine Berechtigung für das interne Dashboard.")
    if request.GET.get("data"):
        return JsonResponse({"labels": []})
    return render(request, "internal/dashboard.html", build_dashboard_context(scope))
