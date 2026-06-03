# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.views.decorators.http import require_POST

from accounts.utils import display_user
from inspections.models import Defect
from notifications.forms import DefectAssignmentForm
from notifications.models import SystemNotification
from notifications.services import assign_defect
from playgrounds.models import Playground
from tenants.models import Organization

from .forms import DefectEditForm
from .image_utils import (
    delete_selected_defect_images,
    handle_defect_image_uploads,
    sync_defect_image_visibility,
)
from .permissions import get_active_profile_for_organization


OPEN_DEFECT_STATUSES = [
    Defect.STATUS_OPEN,
    Defect.STATUS_PLANNED,
]
LOCKED_PLANNING_STATUSES = [
    Defect.STATUS_DONE,
    Defect.STATUS_VERIFIED,
]
DEFECT_STATUS_OVERDUE = "overdue"

DEFECT_STATUS_FILTER_CHOICES = [
    ("", "Alle Status"),
    (Defect.STATUS_OPEN, "Offen"),
    (Defect.STATUS_PLANNED, "Geplant"),
    (DEFECT_STATUS_OVERDUE, "Überfällig"),
    (Defect.STATUS_DONE, "Behoben"),
    (Defect.STATUS_VERIFIED, "Geprüft / abgeschlossen"),
]

DEFECT_MANUAL_STATUS_CHOICES = [
    (Defect.STATUS_OPEN, "Offen"),
    (Defect.STATUS_DONE, "Behoben"),
    (Defect.STATUS_VERIFIED, "Geprüft / abgeschlossen"),
]

DEFECT_STATUS_ACTIONS = {
    Defect.STATUS_OPEN,
    Defect.STATUS_DONE,
    Defect.STATUS_VERIFIED,
}

AUTO_PLANNED_SOURCE_STATUSES = {
    Defect.STATUS_OPEN,
    Defect.STATUS_PLANNED,
}


def get_defect_management_scope(user):
    if user.is_superuser:
        return {
            "organization": None,
            "is_superadmin": True,
            "can_manage": True,
            "can_manage_assignment": True,
            "can_view_internal": True,
        }

    profile = getattr(user, "profile", None)
    if not profile or not profile.is_active_for_organization:
        return {
            "organization": None,
            "is_superadmin": False,
            "can_manage": False,
            "can_manage_assignment": False,
            "can_view_internal": False,
        }

    return {
        "organization": profile.organization,
        "is_superadmin": False,
        "can_manage": profile.may_manage_organization or profile.may_inspect,
        "can_manage_assignment": profile.may_manage_organization,
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
    elif scope["organization"]:
        defects = defects.filter(playground__organization=scope["organization"])
    else:
        defects = defects.none()
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
        return "Push gesendet, gelesen" if notification.read_at else "Push gesendet"
    if notification.delivery_status == SystemNotification.STATUS_NO_SUBSCRIPTION:
        return "Kein Push-Gerät"
    if notification.delivery_status == SystemNotification.STATUS_FAILED:
        return "Push fehlgeschlagen"
    return "Systemnachricht gespeichert"


def defect_has_assignment(defect):
    assignment = getattr(defect, "assignment", None)
    return bool(assignment and assignment.assigned_to_id)


def can_defect_be_planned(defect):
    return bool(defect.planned_resolution_date and defect_has_assignment(defect))


def sync_defect_planning_status(defect):
    if can_defect_be_planned(defect) and defect.status in AUTO_PLANNED_SOURCE_STATUSES:
        defect.status = Defect.STATUS_PLANNED
        return True
    if defect.status == Defect.STATUS_PLANNED and not can_defect_be_planned(defect):
        defect.status = Defect.STATUS_OPEN
        return True
    return False


def save_defect_with_planning_status(defect, update_fields=None):
    status_changed = sync_defect_planning_status(defect)
    if update_fields is not None and status_changed and "status" not in update_fields:
        update_fields = [*update_fields, "status"]
    defect.save(update_fields=update_fields)


def clear_defect_planning(defect, user=None):
    assign_defect(defect=defect, assigned_to=None, assigned_by=user)
    defect.planned_resolution_date = None


def defect_planning_is_locked(defect):
    return defect.status in LOCKED_PLANNING_STATUSES


def enrich_defects(defects, current_user):
    defect_list = list(defects[:100])
    defect_ids = [defect.id for defect in defect_list]
    latest_notifications = {}
    notifications = (
        SystemNotification.objects
        .filter(related_defect_id__in=defect_ids, notification_type=SystemNotification.TYPE_DEFECT_ASSIGNED)
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
        defect.assignment_form = DefectAssignmentForm(
            initial={"assigned_to": assignment.assigned_to if assignment else None},
            organization=defect.playground.organization,
            current_user=current_user,
        )
        defect.latest_assignment_notification = notification
        defect.notification_status_display = format_notification_status(notification)
        defect.planning_locked = defect_planning_is_locked(defect)
        defect.is_overdue = bool(
            defect.planned_resolution_date
            and defect.planned_resolution_date < timezone.localdate()
            and defect.status in OPEN_DEFECT_STATUSES
        )
    return defect_list


def build_status_counts(defects):
    return {
        "open": defects.filter(status=Defect.STATUS_OPEN).count(),
        "planned": defects.filter(status=Defect.STATUS_PLANNED).count(),
        "safety": defects.filter(status=Defect.STATUS_OPEN, has_safety_risk=True).count(),
        "overdue": defects.filter(status__in=OPEN_DEFECT_STATUSES, planned_resolution_date__lt=timezone.localdate()).count(),
        "done": defects.filter(status=Defect.STATUS_DONE).count(),
        "verified": defects.filter(status=Defect.STATUS_VERIFIED).count(),
    }


def apply_defect_filters(defects, request):
    status_filter = request.GET.get("status") or ""
    safety_filter = request.GET.get("safety") or ""
    playground_filter = request.GET.get("playground") or ""
    source_filter = request.GET.get("source") or ""
    search_query = (request.GET.get("q") or "").strip()
    filtered_defects = defects

    allowed_status_filters = {choice[0] for choice in DEFECT_STATUS_FILTER_CHOICES if choice[0]}
    if status_filter == DEFECT_STATUS_OVERDUE:
        filtered_defects = filtered_defects.filter(
            status__in=OPEN_DEFECT_STATUSES,
            planned_resolution_date__lt=timezone.localdate(),
        )
    elif status_filter in allowed_status_filters:
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


def user_can_manage_defect(user, defect, *, include_assignment=False):
    if not defect.playground:
        return False

    if user.is_superuser:
        return True

    profile = get_active_profile_for_organization(user, defect.playground.organization)
    if not profile:
        return False

    if include_assignment:
        return profile.may_manage_organization

    return profile.may_manage_organization or profile.may_inspect


def user_must_manage_defect(user, defect, *, include_assignment=False):
    if not defect.playground:
        raise PermissionDenied("Dieser Mangel ist keinem Spielplatz zugeordnet.")
    if user_can_manage_defect(user, defect, include_assignment=include_assignment):
        return True
    if include_assignment:
        raise PermissionDenied("Keine Berechtigung zum Ändern der Zuweisung.")
    raise PermissionDenied("Keine Berechtigung zum Bearbeiten dieses Mangels.")


def user_can_view_defect(user, defect):
    if not defect.playground:
        return False
    if user.is_superuser:
        return True
    return bool(get_active_profile_for_organization(user, defect.playground.organization))


def get_manageable_defect(defect_id):
    return get_object_or_404(
        Defect.objects.select_related("playground", "playground__organization", "assignment", "assignment__assigned_to"),
        id=defect_id,
    )


def save_defect_images_or_add_error(request, defect):
    try:
        delete_selected_defect_images(defect, request.POST)
        handle_defect_image_uploads(defect, request.FILES)
        sync_defect_image_visibility(defect)
    except ValidationError as error:
        messages.error(request, error.messages[0] if error.messages else str(error))
        return False

    return True


@login_required
def defect_management(request):
    scope = get_defect_management_scope(request.user)
    selected_organization = get_selected_organization(request, scope)
    defects = get_defect_queryset_for_scope(scope, selected_organization)
    filtered_defects, filters = apply_defect_filters(defects, request)
    filtered_defects = filtered_defects.order_by("-has_safety_risk", "planned_resolution_date", "-created_at")
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
            "defects": enrich_defects(filtered_defects, request.user),
            "filters": filters,
            "defect_status_filter_choices": DEFECT_STATUS_FILTER_CHOICES,
            "defect_manual_status_choices": DEFECT_MANUAL_STATUS_CHOICES,
            "defect_source_choices": Defect.SOURCE_CHOICES,
            "playgrounds": playgrounds,
            "status_counts": status_counts,
            "next_query": request.GET.urlencode(),
        },
    )


@login_required
def edit_defect(request, defect_id):
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
            "assignment",
            "assignment__assigned_to",
        ).prefetch_related("images", "images__image"),
        id=defect_id,
    )

    playground = defect.playground

    if not playground:
        messages.error(request, "Dieser Mangel ist keinem Spielplatz zugeordnet.")
        return redirect("public:index")

    if not user_can_view_defect(request.user, defect):
        raise PermissionDenied("Keine Berechtigung zum Anzeigen dieses Mangels.")

    can_edit_defect = user_can_manage_defect(request.user, defect)
    can_manage_assignment = user_can_manage_defect(request.user, defect, include_assignment=True)
    current_planned_resolution_date = defect.planned_resolution_date

    if request.method == "POST":
        user_must_manage_defect(request.user, defect)

        form = DefectEditForm(
            request.POST,
            instance=defect,
            playground=playground,
        )

        if form.is_valid():
            defect = form.save(commit=False)
            defect.playground = playground
            if not can_manage_assignment:
                defect.planned_resolution_date = current_planned_resolution_date
            save_defect_with_planning_status(defect)

            if save_defect_images_or_add_error(request, defect):
                messages.success(request, "Der Mangel wurde gespeichert.")
                return redirect("internal:edit_defect", defect_id=defect.id)
    else:
        form = DefectEditForm(instance=defect, playground=playground)

    if not can_edit_defect:
        for field in form.fields.values():
            field.disabled = True
    if not can_manage_assignment and "planned_resolution_date" in form.fields:
        form.fields["planned_resolution_date"].disabled = True

    current_assignment = getattr(defect, "assignment", None)
    assignment_form = DefectAssignmentForm(
        initial={"assigned_to": current_assignment.assigned_to if current_assignment else None},
        organization=playground.organization,
        current_user=request.user,
    )

    return render(
        request,
        "internal/edit_defect.html",
        {
            "defect": defect,
            "form": form,
            "assignment_form": assignment_form,
            "current_assignment": current_assignment,
            "playground": playground,
            "defect_images": defect.images.select_related("image").all(),
            "can_edit_defect": can_edit_defect,
            "can_manage_assignment": can_manage_assignment,
        },
    )


@login_required
@require_POST
def update_defect_assignment(request, defect_id):
    defect = get_manageable_defect(defect_id)
    user_must_manage_defect(request.user, defect, include_assignment=True)

    if defect_planning_is_locked(defect):
        messages.error(request, "Bei behobenen oder abgeschlossenen Mängeln kann die Planung nicht mehr geändert werden.")
        return redirect(defect_management_redirect_url(request, defect.playground.organization_id))

    form = DefectAssignmentForm(request.POST, organization=defect.playground.organization, current_user=request.user)

    if form.is_valid():
        assigned_to = form.cleaned_data["assigned_to"]
        _, notification = assign_defect(defect=defect, assigned_to=assigned_to, assigned_by=request.user)
        defect = get_manageable_defect(defect_id)
        save_defect_with_planning_status(defect, update_fields=["status", "updated_at"])
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
def update_defect_planning(request, defect_id):
    defect = get_manageable_defect(defect_id)
    user_must_manage_defect(request.user, defect, include_assignment=True)

    if defect_planning_is_locked(defect):
        messages.error(request, "Bei behobenen oder abgeschlossenen Mängeln kann die Planung nicht mehr geändert werden.")
        return redirect(defect_management_redirect_url(request, defect.playground.organization_id))

    form = DefectAssignmentForm(request.POST, organization=defect.playground.organization, current_user=request.user)
    raw_date = (request.POST.get("planned_resolution_date") or "").strip()

    if raw_date:
        planned_resolution_date = parse_date(raw_date)
        if planned_resolution_date is None:
            messages.error(request, "Bitte ein gültiges geplantes Behebungsdatum erfassen.")
            return redirect(defect_management_redirect_url(request, defect.playground.organization_id))
    else:
        planned_resolution_date = None

    if form.is_valid():
        assigned_to = form.cleaned_data["assigned_to"]
        _, notification = assign_defect(defect=defect, assigned_to=assigned_to, assigned_by=request.user)
        defect = get_manageable_defect(defect_id)
        defect.planned_resolution_date = planned_resolution_date
        save_defect_with_planning_status(defect, update_fields=["planned_resolution_date", "status", "updated_at"])

        if defect.status == Defect.STATUS_PLANNED:
            messages.success(request, "Die Planung wurde gespeichert. Der Mangel ist nun geplant.")
        elif assigned_to or planned_resolution_date:
            messages.info(request, "Die Planung wurde gespeichert. Für den Status «Geplant» braucht es Zuweisung und geplantes Behebungsdatum.")
        else:
            messages.success(request, "Die Planung wurde entfernt.")

        if assigned_to and notification and notification.delivery_status == SystemNotification.STATUS_NO_SUBSCRIPTION:
            messages.info(request, "Die zuständige Person hat noch kein Push-Gerät registriert.")
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

    if status == Defect.STATUS_OPEN:
        clear_defect_planning(defect, request.user)
        defect = get_manageable_defect(defect_id)
        defect.planned_resolution_date = None

    defect.status = status
    defect.save(update_fields=["status", "planned_resolution_date", "updated_at"] if status == Defect.STATUS_OPEN else ["status", "updated_at"])

    if status == Defect.STATUS_OPEN:
        messages.success(request, "Der Mangel wurde auf offen gesetzt. Zuweisung und geplantes Behebungsdatum wurden entfernt.")
    elif status == Defect.STATUS_DONE:
        messages.success(request, "Der Mangelstatus wurde auf behoben gesetzt.")
    elif status == Defect.STATUS_VERIFIED:
        messages.success(request, "Der Mangel wurde geprüft und abgeschlossen.")
    return redirect(defect_management_redirect_url(request, defect.playground.organization_id))
