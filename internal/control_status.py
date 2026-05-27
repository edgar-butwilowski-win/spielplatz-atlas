# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import F, Q
from django.shortcuts import render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from inspections.models import Inspection, InspectionTask
from inspections.planning import refresh_task_statuses
from tenants.models import Organization

from .permissions import require_org_admin_permission
from .planning_views import ACTIVE_TASK_STATUSES, get_planning_scope, get_selected_organization


DUE_SOON_DAYS = 14
RECENT_COMPLETION_DAYS = 90


def get_control_status_tasks(scope, selected_organization):
    tasks = InspectionTask.objects.select_related("organization", "playground", "assigned_to", "completed_by_inspection")
    if scope["is_superadmin"]:
        if selected_organization:
            tasks = tasks.filter(organization=selected_organization)
    else:
        tasks = tasks.filter(organization=scope["organization"])
    return tasks


def get_status_bucket_choices():
    return [
        ("active", _("Active inspection tasks")),
        ("overdue", _("Overdue")),
        ("due_soon", _("Due soon")),
        ("planned", _("Planned")),
        ("unassigned", _("Without assignment")),
        ("suspended", _("Suspended")),
        ("completed", _("Done")),
        ("cancelled", _("Cancelled")),
    ]


def apply_status_bucket_filter(tasks, bucket, today, due_soon_until):
    if bucket == "active":
        return tasks.filter(status__in=ACTIVE_TASK_STATUSES)
    if bucket == "overdue":
        return tasks.filter(status=InspectionTask.STATUS_OVERDUE)
    if bucket == "due_soon":
        return tasks.filter(status__in=[InspectionTask.STATUS_OPEN, InspectionTask.STATUS_PLANNED], due_date__gte=today, due_date__lte=due_soon_until)
    if bucket == "planned":
        return tasks.filter(status=InspectionTask.STATUS_PLANNED)
    if bucket == "unassigned":
        return tasks.filter(status__in=ACTIVE_TASK_STATUSES, assigned_to__isnull=True)
    if bucket == "suspended":
        return tasks.filter(status=InspectionTask.STATUS_SUSPENDED)
    if bucket == "completed":
        return tasks.filter(status=InspectionTask.STATUS_COMPLETED)
    if bucket == "cancelled":
        return tasks.filter(status=InspectionTask.STATUS_CANCELLED)
    return tasks.filter(status__in=ACTIVE_TASK_STATUSES)


def build_control_status_metrics(tasks, today):
    due_soon_until = today + timedelta(days=DUE_SOON_DAYS)
    recent_completion_cutoff = today - timedelta(days=RECENT_COMPLETION_DAYS)
    active_tasks = tasks.filter(status__in=ACTIVE_TASK_STATUSES)
    completed_tasks = tasks.filter(status=InspectionTask.STATUS_COMPLETED)
    return {
        "active_count": active_tasks.count(),
        "overdue_count": tasks.filter(status=InspectionTask.STATUS_OVERDUE).count(),
        "due_soon_count": tasks.filter(status__in=[InspectionTask.STATUS_OPEN, InspectionTask.STATUS_PLANNED], due_date__gte=today, due_date__lte=due_soon_until).count(),
        "planned_count": tasks.filter(status=InspectionTask.STATUS_PLANNED).count(),
        "unassigned_count": active_tasks.filter(assigned_to__isnull=True).count(),
        "suspended_count": tasks.filter(status=InspectionTask.STATUS_SUSPENDED).count(),
        "completed_count": completed_tasks.count(),
        "completed_on_time_recent_count": completed_tasks.filter(completed_by_inspection__inspected_at__gte=recent_completion_cutoff, completed_by_inspection__inspected_at__lte=F("due_date")).count(),
        "recent_completion_days": RECENT_COMPLETION_DAYS,
    }


def add_traffic_light(task, today):
    due_soon_until = today + timedelta(days=DUE_SOON_DAYS)
    if task.status == InspectionTask.STATUS_SUSPENDED:
        task.traffic_light = "grey"
        task.traffic_label = _("Suspended")
    elif task.status == InspectionTask.STATUS_OVERDUE or task.due_date < today:
        task.traffic_light = "red"
        task.traffic_label = _("Overdue")
    elif task.due_date <= due_soon_until:
        task.traffic_light = "orange"
        task.traffic_label = _("Due soon")
    elif task.status == InspectionTask.STATUS_PLANNED:
        task.traffic_light = "green"
        task.traffic_label = _("Planned")
    else:
        task.traffic_light = "green"
        task.traffic_label = _("On time")
    task.days_overdue = (today - task.due_date).days if task.due_date < today else 0
    return task


def build_task_rows(tasks, today):
    return [add_traffic_light(task, today) for task in tasks[:150]]


@login_required
def control_status(request):
    scope = get_planning_scope(request.user)
    if not scope:
        raise PermissionDenied(_("No permission for control status."))
    selected_organization = get_selected_organization(request, scope)
    if scope["is_superadmin"]:
        if selected_organization:
            require_org_admin_permission(request.user, selected_organization)
    else:
        selected_organization = scope["organization"]
        require_org_admin_permission(request.user, selected_organization)
    today = timezone.localdate()
    due_soon_until = today + timedelta(days=DUE_SOON_DAYS)
    tasks = get_control_status_tasks(scope, selected_organization)
    refresh_task_statuses(tasks.exclude(status__in=[InspectionTask.STATUS_COMPLETED, InspectionTask.STATUS_CANCELLED]))
    status_bucket = request.GET.get("status") or "active"
    inspection_type = request.GET.get("inspection_type") or ""
    assignment = request.GET.get("assignment") or ""
    filtered_tasks = apply_status_bucket_filter(tasks, status_bucket, today, due_soon_until)
    if inspection_type:
        filtered_tasks = filtered_tasks.filter(inspection_type=inspection_type)
    if assignment == "assigned":
        filtered_tasks = filtered_tasks.filter(assigned_to__isnull=False)
    elif assignment == "unassigned":
        filtered_tasks = filtered_tasks.filter(assigned_to__isnull=True)
    filtered_tasks = filtered_tasks.order_by("due_date", "planned_date", "playground__name")
    organizations = Organization.objects.filter(is_active=True).order_by("name") if scope["is_superadmin"] else []
    return render(request, "internal/control_status.html", {**scope, "selected_organization": selected_organization, "organizations": organizations, "metrics": build_control_status_metrics(tasks, today), "tasks": build_task_rows(filtered_tasks, today), "today": today, "due_soon_days": DUE_SOON_DAYS, "due_soon_until": due_soon_until, "status_bucket": status_bucket, "inspection_type": inspection_type, "assignment": assignment, "status_bucket_choices": get_status_bucket_choices(), "inspection_type_choices": Inspection.TYPE_CHOICES, "assignment_choices": [("", _("All assignments")), ("assigned", _("Assigned")), ("unassigned", _("Without assignment"))]})
