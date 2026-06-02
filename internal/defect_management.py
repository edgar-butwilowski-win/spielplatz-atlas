# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import UserProfile
from accounts.utils import display_user
from inspections.models import Defect
from notifications.forms import DefectAssignmentForm
from notifications.models import SystemNotification
from notifications.services import assign_defect
from playgrounds.models import Playground
from tenants.models import Organization

from .permissions import (
    get_active_profile_for_organization,
    require_internal_view_permission,
    require_org_admin_permission,
)


OPEN_DEFECT_STATUSES = [
    Defect.STATUS_OPEN,
    Defect.STATUS_IN_PROGRESS,
    Defect.STATUS_PLANNED,
]

DEFECT_FILTER_CHOICES = [
    ("open", "Offene Mängel"),
    ("assigned", "Zugewiesen"),
    ("review", "Zur Prüfung"),
    ("verified", "Abgeschlossen"),
    ("all", "Alle Mängel"),
]

DEFECT_STATUS_ACTIONS = {
    Defect.STATUS_OPEN,
    Defect.STATUS_IN_PROGRESS,
    Defect.STATUS_PLANNED,
    Defect.STATUS_DONE,
    Defect.STATUS_VERIFIED,
}


def get_defect_management_scope(user):
    if user.is_superuser:
        return {
            "organization": None,
            "is_superadmin": True,
            "can_manage": True,
            "can_view_internal": True,
        }

    profile = getattr(user, "profile", None)

    if not profile:
        return None

    profile = get_active_profile_for_organization(user, profile.organization)

    if not profile or not profile.may_view_internal or not profile.may_manage_organization:
        return None

    return {
        "organization": profile.organization,
        "is_superadmin": False,
        "can_manage": profile.may_manage_organization,
        "can_view_internal": profile.may_view_internal,
    }


def get_selected_organization(request, scope):
    if not scope["is_superadmin"]:
        return scope["organization"]

    organization_id = request.GET.get("organization") or request.POST.get("organization")

    if organization_id:
        return get_object_or_404(Organization, id=organization_id, is_active=True)

    return None


def get_defect_queryset_for_scope(scope, selected_organization):
    defects = Defect.objects.select_related(
        "playground",
        "playground__organization",
        "equipment",
        "surface",
        "accessory",
        "assignment",
        "assignment__assigned_to",
    )

    if scope["is_superadmin"]:
        if selected_organization:
            defects = defects.filter(playground__organization=selected_organization)
    else:
        defects = defects.filter(playground__organization=scope["organization"])

    return defects


def defect_management_redirect_url(request, organization_id=None):
    base_url = reverse("internal:defect_management")
    query = request.POST.get("next_query") or ""

    if query:
        return f"{base_url}?{query}"

    if organization_id:
        return f"{base_url}?organization={organization_id}"

    return base_url


def format_notification_status(notification):
    if not notification:
        return "Keine Meldung"

    if notification.delivery_status == SystemNotification.STATUS_SENT:
        if notification.read_at:
            return "Push gesendet, gelesen"
        return "Push gesendet"

    if notification.delivery_status == SystemNotification.STATUS_NO_SUBSCRIPTION:
        return "Kein Push-Gerät"

    if notification.delivery_status == SystemNotification.STATUS_FAILED:
        return "Push fehlgeschlagen"

    return "Systemnachricht gespeichert"


def enrich_defects(defects):
    defect_list = list(defects[:100])
    defect_ids = [defect.id for defect in defect_list]

    latest_notifications = {}
    notifications = (
        SystemNotification.objects
        .filter(
            related_defect_id__in=defect_ids,
            notification_type=SystemNotification.TYPE_DEFECT_ASSIGNED,
        )
        .select_related("recipient")
        .order_by("related_defect_id", "-created_at")
    )

    for notification in notifications:
        latest_notifications.setdefault(notification.related_defect_id, notification)

    for defect in defect_list:
        assignment = getattr(defect, "assignment", None)
        notification = latest_notifications.get(defect.id)
        target_parts = []

        if defect.equipment:
            target_parts.append(defect.equipment.name)
        if defect.surface:
            target_parts.append(defect.surface.name)
        if defect.accessory:
            target_parts.append(defect.accessory.name)

        defect.management_target = ", ".join(target_parts) or "Allgemeiner Mangel"
        defect.assignment_display = display_user(assignment.assigned_to) if assignment and assignment.assigned_to else "Nicht zugewiesen"
        defect.latest_assignment_notification = notification
        defect.notification_status_display = format_notification_status(notification)
        defect.is_overdue = bool(
            defect.planned_resolution_date
            and defect.planned_resolution_date < timezone.localdate()
            and defect.status in OPEN_DEFECT_STATUSES
        )

    return defect_list


def build_status_counts(defects):
    return {
        "open": defects.filter(status__in=OPEN_DEFECT_STATUSES).count(),
        "safety": defects.filter(status__in=OPEN_DEFECT_STATUSES, has_safety_risk=True).count(),
        "overdue": defects.filter(
            status__in=OPEN_DEFECT_STATUSES,
            planned_resolution_date__lt=timezone.localdate(),
        ).count(),
        "done": defects.filter(status=Defect.STATUS_DONE).count(),
        "verified": defects.filter(status=Defect.STATUS_VERIFIED).count(),
    }


def apply_defect_filters(defects, request):
    status_filter = request.GET.get("status") or "open"
    safety_filter = request.GET.get("safety") or ""
    playground_filter = request.GET.get("playground") or ""
    source_filter = request.GET.get("source") or ""
    search_query = (request.GET.get("q") or "").strip()

    filtered_defects = defects

    if status_filter == "open":
        filtered_defects = filtered_defects.filter(status__in=OPEN_DEFECT_STATUSES)
    elif status_filter == "assigned":
        filtered_defects = filtered_defects.filter(assignment__assigned_to__isnull=False).exclude(status=Defect.STATUS_VERIFIED)
    elif status_filter == "review":
        filtered_defects = filtered_defects.filter(status=Defect.STATUS_DONE)
    elif status_filter == "verified":
        filtered_defects = filtered_defects.filter(status=Defect.STATUS_VERIFIED)
    elif status_filter in dict(Defect.STATUS_CHOICES):
        filtered_defects = filtered_defects.filter(status=status_filter)

    if safety_filter == "yes":
        filtered_defects = filtered_defects.filter(has_safety_risk=True)
    elif safety_filter == "no":
        filtered_defects = filtered_defects.filter(has_safety_risk=False)

    if playground_filter:
        filtered_defects = filtered_defects.filter(playground_id=playground_filter)

    if source_filter:
        filtered_defects = filtered_defects.filter(source_type=source_filter)

    if search_query:
        filtered_defects = filtered_defects.filter(
            Q(internal_description__icontains=search_query)
            | Q(internal_note__icontains=search_query)
            | Q(playground__name__icontains=search_query)
            | Q(equipment__name__icontains=search_query)
            | Q(surface__name__icontains=search_query)
            | Q(accessory__name__icontains=search_query)
        )

    return filtered_defects, {
        "status": status_filter,
        "safety": safety_filter,
        "playground": playground_filter,
        "source": source_filter,
        "q": search_query,
    }


def get_playgrounds_for_filter(defects):
    playground_ids = defects.exclude(playground__isnull=True).values_list("playground_id", flat=True).distinct()
    return Playground.objects.filter(id__in=playground_ids).select_related("organization").order_by("name")


def user_must_manage_defect(user, defect):
    if not defect.playground:
        raise PermissionDenied("Dieser Mangel ist keinem Spielplatz zugeordnet.")

    require_org_admin_permission(user, defect.playground.organization)


def get_manageable_defect(defect_id):
    return get_object_or_404(
        Defect.objects.select_related(
            "playground",
            "playground__organization",
            "assignment",
            "assignment__assigned_to",
        ),
        id=defect_id,
    )


@login_required
def defect_management(request):
    scope = get_defect_management_scope(request.user)

    if not scope:
        raise PermissionDenied("Keine Berechtigung für die operative Mängelverwaltung.")

    if scope["organization"]:
        require_internal_view_permission(request.user, scope["organization"])

    selected_organization = get_selected_organization(request, scope)
    defects = get_defect_queryset_for_scope(scope, selected_organization)
    filtered_defects, filters = apply_defect_filters(defects, request)
    filtered_defects = filtered_defects.order_by(
        "-has_safety_risk",
        "planned_resolution_date",
        "-created_at",
    )

    organizations = Organization.objects.filter(is_active=True).order_by("name") if scope["is_superadmin"] else []
    playgrounds = get_playgrounds_for_filter(defects)
    status_counts = build_status_counts(defects)

    return render(
        request,
        "internal/defect_management.html",
        {
            **scope,
            "selected_organization": selected_organization,
            "organizations": organizations,
            "defects": enrich_defects(filtered_defects),
            "filters": filters,
            "defect_filter_choices": DEFECT_FILTER_CHOICES,
            "defect_status_choices": Defect.STATUS_CHOICES,
            "defect_source_choices": Defect.SOURCE_CHOICES,
            "playgrounds": playgrounds,
            "status_counts": status_counts,
            "next_query": request.GET.urlencode(),
        },
    )


@login_required
@require_POST
def update_defect_assignment(request, defect_id):
    defect = get_manageable_defect(defect_id)
    user_must_manage_defect(request.user, defect)

    form = DefectAssignmentForm(
        request.POST,
        organization=defect.playground.organization,
        current_user=request.user,
    )

    if form.is_valid():
        assigned_to = form.cleaned_data["assigned_to"]
        _, notification = assign_defect(
            defect=defect,
            assigned_to=assigned_to,
            assigned_by=request.user,
        )

        if assigned_to:
            if notification and notification.delivery_status == SystemNotification.STATUS_SENT:
                messages.success(request, "Der Mangel wurde zugewiesen. Die Push-Meldung wurde gesendet.")
            elif notification and notification.delivery_status == SystemNotification.STATUS_NO_SUBSCRIPTION:
                messages.info(request, "Der Mangel wurde zugewiesen. Die Person hat noch kein Push-Gerät registriert.")
            else:
                messages.info(request, "Der Mangel wurde zugewiesen. Die Systemnachricht wurde gespeichert.")
        else:
            messages.success(request, "Die Zuweisung wurde entfernt.")
    else:
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)

    return redirect(defect_management_redirect_url(request, defect.playground.organization_id))


@login_required
@require_POST
def update_defect_status(request, defect_id):
    defect = get_manageable_defect(defect_id)
    user_must_manage_defect(request.user, defect)

    status = request.POST.get("status")

    if status not in DEFECT_STATUS_ACTIONS:
        messages.error(request, "Dieser Mangelstatus ist nicht zulässig.")
        return redirect(defect_management_redirect_url(request, defect.playground.organization_id))

    defect.status = status
    defect.save(update_fields=["status", "updated_at"])

    if status == Defect.STATUS_DONE:
        messages.success(request, "Die Erledigung wurde gemeldet.")
    elif status == Defect.STATUS_VERIFIED:
        messages.success(request, "Der Mangel wurde geprüft und abgeschlossen.")
    else:
        messages.success(request, "Der Mangelstatus wurde aktualisiert.")

    return redirect(defect_management_redirect_url(request, defect.playground.organization_id))
