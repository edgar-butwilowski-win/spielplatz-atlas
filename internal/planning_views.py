# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

from datetime import timedelta

from django import forms
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import UserProfile
from inspections.models import Inspection, InspectionTask
from inspections.planning import rebuild_planning_for_organization, refresh_task_statuses
from tenants.models import Organization

from .permissions import (
    get_active_profile_for_organization,
    require_inspection_permission,
    require_internal_view_permission,
    require_org_admin_permission,
)
from .views import create_default_answers


ACTIVE_TASK_STATUSES = [
    InspectionTask.STATUS_OPEN,
    InspectionTask.STATUS_PLANNED,
    InspectionTask.STATUS_OVERDUE,
    InspectionTask.STATUS_SUSPENDED,
]

CLOSED_TASK_STATUSES = [
    InspectionTask.STATUS_COMPLETED,
    InspectionTask.STATUS_CANCELLED,
]

HTML_DATE_FORMAT = "%Y-%m-%d"


class PlanningUserChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, user):
        full_name = user.get_full_name().strip()

        if full_name and user.email:
            return f"{full_name} ({user.email})"

        return full_name or user.email or "Benutzer ohne E-Mail"


class InspectionTaskPlanningForm(forms.ModelForm):
    assigned_to = PlanningUserChoiceField(
        queryset=get_user_model().objects.none(),
        required=False,
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    class Meta:
        model = InspectionTask
        fields = (
            "planned_date",
            "assigned_to",
            "note",
        )
        widgets = {
            "planned_date": forms.DateInput(format=HTML_DATE_FORMAT, attrs={"type": "date", "class": "form-control"}),
            "note": forms.Textarea(attrs={"rows": 2, "class": "form-control"}),
        }

    def __init__(self, *args, organization=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.organization = organization
        self.fields["planned_date"].required = False
        self.fields["planned_date"].input_formats = [HTML_DATE_FORMAT]
        self.fields["planned_date"].widget.format = HTML_DATE_FORMAT
        self.fields["assigned_to"].required = False
        self.fields["note"].required = False
        self.fields["assigned_to"].queryset = self.get_assignable_users()

    def get_assignable_users(self):
        User = get_user_model()

        if not self.organization:
            return User.objects.none()

        return (
            User.objects
            .filter(is_active=True)
            .filter(
                Q(is_superuser=True)
                | (
                    Q(profile__organization=self.organization)
                    & Q(profile__is_active_for_organization=True)
                    & Q(profile__role__in=[
                        UserProfile.ROLE_ORG_ADMIN,
                        UserProfile.ROLE_INSPECTOR,
                    ])
                )
            )
            .distinct()
            .order_by("last_name", "first_name", "email")
        )

    def clean_planned_date(self):
        planned_date = self.cleaned_data.get("planned_date")

        if planned_date and planned_date < timezone.localdate():
            raise forms.ValidationError("Das geplante Datum darf nicht in der Vergangenheit liegen.")

        return planned_date


def get_planning_scope(user):
    if user.is_superuser:
        return {
            "organization": None,
            "is_superadmin": True,
            "can_manage": True,
            "can_inspect": True,
            "can_view_internal": True,
        }

    profile = getattr(user, "profile", None)

    if not profile:
        return None

    profile = get_active_profile_for_organization(user, profile.organization)

    if not profile or not profile.may_view_internal:
        return None

    return {
        "organization": profile.organization,
        "is_superadmin": False,
        "can_manage": profile.may_manage_organization,
        "can_inspect": profile.may_inspect,
        "can_view_internal": profile.may_view_internal,
    }


def get_selected_organization(request, scope):
    if not scope["is_superadmin"]:
        return scope["organization"]

    organization_id = request.GET.get("organization") or request.POST.get("organization")

    if organization_id:
        return get_object_or_404(Organization, id=organization_id, is_active=True)

    return None


def get_task_queryset_for_scope(scope, selected_organization):
    tasks = InspectionTask.objects.select_related(
        "organization",
        "playground",
        "assigned_to",
        "created_from_inspection",
        "completed_by_inspection",
    )

    if scope["is_superadmin"]:
        if selected_organization:
            tasks = tasks.filter(organization=selected_organization)
    else:
        tasks = tasks.filter(organization=scope["organization"])

    return tasks


def get_inspection_task_for_user(task_id, user):
    task = get_object_or_404(
        InspectionTask.objects.select_related("organization", "playground", "assigned_to"),
        id=task_id,
    )

    require_inspection_permission(user, task.organization)

    if user.is_superuser:
        return task

    if task.assigned_to_id and task.assigned_to_id != user.id:
        raise PermissionDenied("Dieser Kontrollauftrag ist einer anderen Person zugewiesen.")

    return task


def user_can_start_inspection_task(task, user):
    if user.is_superuser:
        return True

    return not task.assigned_to_id or task.assigned_to_id == user.id


def is_task_planning_editable(task):
    return task.status not in CLOSED_TASK_STATUSES


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


def add_planning_forms(tasks, user=None):
    task_list = list(tasks[:100])

    for task in task_list:
        task.planning_form = InspectionTaskPlanningForm(
            instance=task,
            organization=task.organization,
        )
        task.can_be_started_by_current_user = user_can_start_inspection_task(task, user) if user else False
        task.planning_can_be_edited = is_task_planning_editable(task)

    return task_list


def planning_redirect_url(organization_id=None):
    url = reverse("internal:inspection_planning")

    if organization_id:
        return f"{url}?organization={organization_id}"

    return url


@login_required
def inspection_planning(request):
    scope = get_planning_scope(request.user)

    if not scope:
        raise PermissionDenied("Keine Berechtigung für die interne Einsatzplanung.")

    if scope["organization"]:
        require_internal_view_permission(request.user, scope["organization"])

    selected_organization = get_selected_organization(request, scope)
    tasks = get_task_queryset_for_scope(scope, selected_organization)
    refresh_task_statuses(tasks.exclude(
        status__in=CLOSED_TASK_STATUSES
    ))

    status_filter = request.GET.get("status") or "active"
    inspection_type_filter = request.GET.get("inspection_type") or ""

    filtered_tasks = tasks

    if status_filter == "active":
        filtered_tasks = filtered_tasks.filter(status__in=ACTIVE_TASK_STATUSES)
    elif status_filter:
        filtered_tasks = filtered_tasks.filter(status=status_filter)

    if inspection_type_filter:
        filtered_tasks = filtered_tasks.filter(inspection_type=inspection_type_filter)

    organizations = Organization.objects.filter(is_active=True).order_by("name") if scope["is_superadmin"] else []
    can_manage_selected_organization = scope["can_manage"] and selected_organization is not None

    return render(
        request,
        "internal/inspection_planning.html",
        {
            **scope,
            "selected_organization": selected_organization,
            "organizations": organizations,
            "tasks": add_planning_forms(filtered_tasks, request.user),
            "status_filter": status_filter,
            "inspection_type_filter": inspection_type_filter,
            "status_choices": [("active", "Aktive Aufträge")] + list(InspectionTask.STATUS_CHOICES),
            "inspection_type_choices": Inspection.TYPE_CHOICES,
            "task_counts_by_status": choice_count_map(tasks, "status", InspectionTask.STATUS_CHOICES),
            "can_manage_selected_organization": can_manage_selected_organization,
            "today": timezone.localdate(),
        },
    )


@login_required
def my_inspections(request):
    scope = get_planning_scope(request.user)

    if not scope or not scope["can_inspect"]:
        raise PermissionDenied("Keine Berechtigung für die persönliche Kontrollliste.")

    if scope["organization"]:
        require_inspection_permission(request.user, scope["organization"])

    tasks = InspectionTask.objects.select_related(
        "organization",
        "playground",
        "assigned_to",
    ).filter(status__in=ACTIVE_TASK_STATUSES)

    if request.user.is_superuser:
        assigned_tasks = tasks.filter(assigned_to=request.user)
        unassigned_tasks = tasks.filter(assigned_to__isnull=True)
    else:
        assigned_tasks = tasks.filter(
            organization=scope["organization"],
            assigned_to=request.user,
        )
        unassigned_tasks = tasks.filter(
            organization=scope["organization"],
            assigned_to__isnull=True,
        )

    refresh_task_statuses(assigned_tasks)
    refresh_task_statuses(unassigned_tasks)

    today = timezone.localdate()
    upcoming_limit = today + timedelta(days=30)

    assigned_tasks = assigned_tasks.order_by("planned_date", "due_date", "playground__name")
    unassigned_tasks = unassigned_tasks.order_by("due_date", "playground__name")

    return render(
        request,
        "internal/my_inspections.html",
        {
            **scope,
            "today": today,
            "assigned_today": assigned_tasks.filter(planned_date=today),
            "assigned_overdue": assigned_tasks.filter(status=InspectionTask.STATUS_OVERDUE),
            "assigned_upcoming": assigned_tasks.exclude(status=InspectionTask.STATUS_OVERDUE).filter(
                Q(planned_date__isnull=True, due_date__lte=upcoming_limit)
                | Q(planned_date__gte=today, planned_date__lte=upcoming_limit)
            ),
            "unassigned_due": unassigned_tasks.filter(
                status__in=[InspectionTask.STATUS_OPEN, InspectionTask.STATUS_OVERDUE]
            )[:25],
        },
    )


@login_required
@require_POST
def rebuild_inspection_planning(request):
    scope = get_planning_scope(request.user)

    if not scope:
        raise PermissionDenied("Keine Berechtigung für die interne Einsatzplanung.")

    organization = get_selected_organization(request, scope)

    if not organization:
        messages.error(request, "Bitte zuerst eine Organisation auswählen.")
        return redirect("internal:inspection_planning")

    require_org_admin_permission(request.user, organization)

    result = rebuild_planning_for_organization(organization)

    messages.success(
        request,
        (
            "Die Kontrollplanung wurde neu berechnet. "
            f"Erstellt: {result['created']}, aktualisiert: {result['updated']}, unverändert: {result['unchanged']}."
        ),
    )
    return redirect(planning_redirect_url(organization.id))


@login_required
@require_POST
def update_inspection_task(request, task_id):
    task = get_object_or_404(
        InspectionTask.objects.select_related("organization", "playground"),
        id=task_id,
    )

    require_org_admin_permission(request.user, task.organization)

    if not is_task_planning_editable(task):
        messages.error(request, "Erledigte oder abgebrochene Kontrollaufträge können nicht mehr geplant werden.")
        return redirect(planning_redirect_url(task.organization_id))

    form = InspectionTaskPlanningForm(
        request.POST,
        instance=task,
        organization=task.organization,
    )

    if form.is_valid():
        task = form.save(commit=False)

        if task.status not in CLOSED_TASK_STATUSES:
            if task.planned_date or task.assigned_to_id:
                task.status = InspectionTask.STATUS_PLANNED
            else:
                task.status = InspectionTask.STATUS_OPEN

        try:
            task.full_clean()
            task.save()
            task.refresh_status(save=True)
            messages.success(request, "Der Kontrollauftrag wurde gespeichert.")
        except ValidationError as error:
            messages.error(request, error.messages[0] if error.messages else str(error))
    else:
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)

    return redirect(planning_redirect_url(task.organization_id))


@login_required
@require_POST
def accept_inspection_task(request, task_id):
    task = get_inspection_task_for_user(task_id, request.user)

    if task.status in CLOSED_TASK_STATUSES:
        messages.error(request, "Dieser Kontrollauftrag kann nicht übernommen werden.")
        return redirect("internal:my_inspections")

    if task.assigned_to_id and task.assigned_to_id != request.user.id:
        raise PermissionDenied("Dieser Kontrollauftrag ist bereits zugewiesen.")

    task.assigned_to = request.user

    if not task.planned_date:
        task.planned_date = timezone.localdate()

    task.status = InspectionTask.STATUS_PLANNED
    task.full_clean()
    task.save(update_fields=["assigned_to", "planned_date", "status", "updated_at"])
    task.refresh_status(save=True)

    messages.success(request, "Der Kontrollauftrag wurde in Ihre persönliche Liste übernommen.")
    return redirect("internal:my_inspections")


@login_required
@require_POST
def start_inspection_from_task(request, task_id):
    try:
        task = get_inspection_task_for_user(task_id, request.user)
    except PermissionDenied as error:
        messages.error(request, str(error) or "Sie dürfen diesen Kontrollauftrag nicht starten.")
        return redirect("internal:my_inspections")

    if task.status in CLOSED_TASK_STATUSES:
        messages.error(request, "Aus diesem Kontrollauftrag kann keine neue Kontrolle gestartet werden.")
        return redirect("internal:my_inspections")

    if task.playground.is_inspection_suspended:
        messages.error(
            request,
            "Für diesen Spielplatz ist die Inspektion aktuell ausgesetzt. Es kann keine neue Kontrolle erfasst werden.",
        )
        return redirect("internal:my_inspections")

    inspection = Inspection.objects.create(
        playground=task.playground,
        inspection_type=task.inspection_type,
        inspected_at=timezone.localdate(),
        inspector=request.user,
        result=Inspection.RESULT_OK,
    )

    create_default_answers(inspection)

    if not task.assigned_to_id:
        task.assigned_to = request.user
        task.status = InspectionTask.STATUS_PLANNED
        task.save(update_fields=["assigned_to", "status", "updated_at"])

    messages.success(request, "Die Kontrolle wurde aus der Einsatzplanung gestartet.")
    return redirect("internal:inspection_detail", inspection_id=inspection.id)
