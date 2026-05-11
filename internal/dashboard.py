# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

import json
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count, Max, Q
from django.shortcuts import render
from django.utils import timezone

from inspections.models import Defect, Inspection, MaintenanceAction
from playgrounds.models import Playground
from tenants.models import Organization

from .permissions import get_active_profile_for_organization


RECENT_INSPECTION_DAYS = 365


def get_dashboard_scope(user):
    if user.is_superuser:
        return {
            "organization": None,
            "is_superadmin": True,
            "can_manage": True,
            "can_inspect": True,
            "can_maintain": True,
            "can_view_internal": True,
        }

    profile = getattr(user, "profile", None)

    if not profile:
        return None

    profile = get_active_profile_for_organization(user, profile.organization)

    if not profile:
        return None

    return {
        "organization": profile.organization,
        "is_superadmin": False,
        "can_manage": profile.may_manage_organization,
        "can_inspect": profile.may_inspect,
        "can_maintain": profile.may_maintain,
        "can_view_internal": profile.may_view_internal,
    }


def choice_count_map(queryset, field_name, choices):
    raw_counts = queryset.values(field_name).annotate(count=Count("id"))
    counts = {entry[field_name]: entry["count"] for entry in raw_counts}

    return [
        {
            "key": key,
            "label": label,
            "count": counts.get(key, 0),
        }
        for key, label in choices
    ]


def top_playground_defect_counts(defects):
    return list(
        defects
        .values("playground__name", "playground__organization__name")
        .annotate(count=Count("id"))
        .order_by("-count", "playground__organization__name", "playground__name")[:10]
    )


def build_playgrounds_without_recent_completed_inspection(playgrounds):
    cutoff_date = timezone.localdate() - timedelta(days=RECENT_INSPECTION_DAYS)

    return list(
        playgrounds
        .annotate(
            latest_completed_inspection=Max(
                "inspections__inspected_at",
                filter=Q(inspections__status=Inspection.STATUS_COMPLETED),
            )
        )
        .filter(
            Q(latest_completed_inspection__isnull=True)
            | Q(latest_completed_inspection__lt=cutoff_date)
        )
        .select_related("organization")
        .order_by("organization__name", "name")[:25]
    )


def build_dashboard_context(scope):
    organization = scope["organization"]

    playgrounds = Playground.objects.select_related("organization")
    defects = Defect.objects.select_related("playground", "playground__organization")
    inspections = Inspection.objects.select_related("playground", "playground__organization")
    maintenance_actions = MaintenanceAction.objects.select_related(
        "defect",
        "defect__playground",
        "defect__playground__organization",
    )

    if organization is not None:
        playgrounds = playgrounds.filter(organization=organization)
        defects = defects.filter(playground__organization=organization)
        inspections = inspections.filter(playground__organization=organization)
        maintenance_actions = maintenance_actions.filter(defect__playground__organization=organization)

    open_defects = defects.exclude(
        status__in=[
            Defect.STATUS_DONE,
            Defect.STATUS_VERIFIED,
        ]
    )
    safety_risk_defects = open_defects.filter(has_safety_risk=True)
    planned_maintenance_actions = maintenance_actions.exclude(
        status__in=[
            MaintenanceAction.STATUS_DONE,
            MaintenanceAction.STATUS_CANCELLED,
        ]
    )
    completed_inspections = inspections.filter(status=Inspection.STATUS_COMPLETED)
    draft_inspections = inspections.filter(status=Inspection.STATUS_DRAFT)

    defects_by_status = choice_count_map(defects, "status", Defect.STATUS_CHOICES)
    defects_by_source = choice_count_map(defects, "source_type", Defect.SOURCE_CHOICES)
    maintenance_by_status = choice_count_map(
        maintenance_actions,
        "status",
        MaintenanceAction.STATUS_CHOICES,
    )
    inspections_by_type = choice_count_map(
        inspections,
        "inspection_type",
        Inspection.TYPE_CHOICES,
    )
    inspections_by_status = choice_count_map(
        inspections,
        "status",
        Inspection.STATUS_CHOICES,
    )
    organizations_count = Organization.objects.count() if organization is None else 1

    return {
        **scope,
        "organizations_count": organizations_count,
        "playgrounds_count": playgrounds.count(),
        "active_playgrounds_count": playgrounds.filter(is_active=True).count(),
        "public_playgrounds_count": playgrounds.filter(is_active=True, public_visible=True).count(),
        "open_defects_count": open_defects.count(),
        "safety_risk_defects_count": safety_risk_defects.count(),
        "planned_maintenance_actions_count": planned_maintenance_actions.count(),
        "completed_inspections_count": completed_inspections.count(),
        "draft_inspections_count": draft_inspections.count(),
        "defects_by_status": defects_by_status,
        "defects_by_source": defects_by_source,
        "defects_by_playground": top_playground_defect_counts(open_defects),
        "maintenance_by_status": maintenance_by_status,
        "inspections_by_type": inspections_by_type,
        "inspections_by_status": inspections_by_status,
        "defects_by_status_json": json.dumps(defects_by_status),
        "defects_by_source_json": json.dumps(defects_by_source),
        "maintenance_by_status_json": json.dumps(maintenance_by_status),
        "inspections_by_type_json": json.dumps(inspections_by_type),
        "inspections_by_status_json": json.dumps(inspections_by_status),
        "latest_inspections": list(
            completed_inspections
            .select_related("playground", "playground__organization", "inspector")
            .order_by("-inspected_at", "-completed_at", "-created_at")[:10]
        ),
        "open_safety_risk_defects": list(
            safety_risk_defects
            .select_related("playground", "playground__organization", "equipment", "surface", "accessory")
            .order_by("planned_resolution_date", "-created_at")[:10]
        ),
        "planned_maintenance_actions": list(
            planned_maintenance_actions
            .select_related("defect", "defect__playground", "defect__playground__organization")
            .order_by("planned_date", "-created_at")[:10]
        ),
        "playgrounds_without_recent_completed_inspection": build_playgrounds_without_recent_completed_inspection(playgrounds),
        "recent_inspection_days": RECENT_INSPECTION_DAYS,
    }


@login_required
def dashboard(request):
    scope = get_dashboard_scope(request.user)

    if not scope or not scope["can_view_internal"]:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("Keine Berechtigung für das interne Dashboard.")

    return render(
        request,
        "internal/dashboard.html",
        build_dashboard_context(scope),
    )
