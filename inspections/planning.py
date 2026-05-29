from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from playgrounds.models import Playground

from .models import Inspection, InspectionRule, InspectionTask


def ensure_default_inspection_rules(organization):
    rules = []

    for inspection_type, _label in Inspection.TYPE_CHOICES:
        rule, _created = InspectionRule.objects.get_or_create(
            organization=organization,
            inspection_type=inspection_type,
            defaults={
                "interval_days": InspectionRule.get_default_interval_days(inspection_type),
                "applies_to_all_playgrounds": True,
                "is_active": True,
            },
        )
        rules.append(rule)

    return rules


def get_active_inspection_rules(organization):
    ensure_default_inspection_rules(organization)

    return InspectionRule.objects.filter(
        organization=organization,
        is_active=True,
        applies_to_all_playgrounds=True,
    ).order_by("inspection_type")


def get_default_inspector_for_playground(playground, inspection_type):
    inspector = playground.get_default_inspector_for_inspection_type(inspection_type)

    if not inspector or not inspector.is_active:
        return None

    if inspector.is_superuser:
        return inspector

    profile = getattr(inspector, "profile", None)

    if (
        profile
        and profile.organization_id == playground.organization_id
        and profile.is_active_for_organization
        and profile.may_inspect
    ):
        return inspector

    return None


def get_open_task_for(playground, inspection_type):
    return (
        InspectionTask.objects
        .filter(
            playground=playground,
            inspection_type=inspection_type,
            status__in=[
                InspectionTask.STATUS_OPEN,
                InspectionTask.STATUS_PLANNED,
                InspectionTask.STATUS_OVERDUE,
                InspectionTask.STATUS_SUSPENDED,
            ],
        )
        .order_by("due_date", "created_at")
        .first()
    )


def refresh_task_statuses(queryset=None):
    base_queryset = queryset or InspectionTask.objects.all()
    tasks = base_queryset.exclude(
        status__in=[
            InspectionTask.STATUS_COMPLETED,
            InspectionTask.STATUS_CANCELLED,
            InspectionTask.STATUS_SUSPENDED,
        ]
    ).select_related("playground")

    updated = 0

    for task in tasks:
        old_status = task.status
        task.refresh_status(save=True)

        if task.status != old_status:
            updated += 1

    return updated


def create_or_update_task_for_rule(playground, rule, reference_inspection=None):
    due_date = InspectionTask.calculate_due_date(
        playground,
        rule.inspection_type,
        reference_inspection=reference_inspection,
    )

    task = get_open_task_for(playground, rule.inspection_type)

    if task is None:
        task = InspectionTask.objects.create(
            organization=playground.organization,
            playground=playground,
            inspection_type=rule.inspection_type,
            due_date=due_date,
            assigned_to=get_default_inspector_for_playground(playground, rule.inspection_type),
            source=InspectionTask.SOURCE_AUTOMATIC,
            created_from_inspection=reference_inspection,
        )
        task.refresh_status(save=True)
        return task, True, False

    changed = False

    if reference_inspection and task.created_from_inspection_id is None:
        task.created_from_inspection = reference_inspection
        changed = True

    if task.due_date != due_date:
        task.due_date = due_date
        changed = True

    if changed:
        task.save()

    task.refresh_status(save=True)
    return task, False, changed


def rebuild_planning_for_organization(organization):
    rules = get_active_inspection_rules(organization)
    playgrounds = Playground.objects.filter(
        organization=organization,
        is_active=True,
    ).select_related(
        "organization",
        "default_visual_inspector",
        "default_operational_inspector",
        "default_annual_inspector",
        "default_visual_inspector__profile",
        "default_operational_inspector__profile",
        "default_annual_inspector__profile",
    )

    result = {
        "rules": rules.count(),
        "playgrounds": playgrounds.count(),
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "status_refreshed": 0,
    }

    with transaction.atomic():
        for playground in playgrounds:
            for rule in rules:
                _task, created, changed = create_or_update_task_for_rule(playground, rule)

                if created:
                    result["created"] += 1
                elif changed:
                    result["updated"] += 1
                else:
                    result["unchanged"] += 1

        result["status_refreshed"] = refresh_task_statuses(
            InspectionTask.objects.filter(organization=organization)
        )

    return result


def complete_matching_task_for_inspection(inspection):
    task = (
        InspectionTask.objects
        .filter(
            playground=inspection.playground,
            inspection_type=inspection.inspection_type,
            completed_by_inspection__isnull=True,
            status__in=[
                InspectionTask.STATUS_OPEN,
                InspectionTask.STATUS_PLANNED,
                InspectionTask.STATUS_OVERDUE,
                InspectionTask.STATUS_SUSPENDED,
            ],
        )
        .exclude(created_from_inspection=inspection)
        .order_by("due_date", "created_at")
        .first()
    )

    if task is None:
        return None

    task.status = InspectionTask.STATUS_COMPLETED
    task.completed_by_inspection = inspection
    task.save(update_fields=["status", "completed_by_inspection", "updated_at"])
    return task


def create_follow_up_task_for_inspection(inspection):
    rule, _created = InspectionRule.objects.get_or_create(
        organization=inspection.playground.organization,
        inspection_type=inspection.inspection_type,
        defaults={
            "interval_days": InspectionRule.get_default_interval_days(inspection.inspection_type),
            "applies_to_all_playgrounds": True,
            "is_active": True,
        },
    )

    if not rule.is_active or not rule.applies_to_all_playgrounds:
        return None

    existing_open_task = get_open_task_for(inspection.playground, inspection.inspection_type)

    if existing_open_task:
        return existing_open_task

    due_date = InspectionTask.calculate_due_date(
        inspection.playground,
        inspection.inspection_type,
        reference_inspection=inspection,
    )

    task = InspectionTask.objects.create(
        organization=inspection.playground.organization,
        playground=inspection.playground,
        inspection_type=inspection.inspection_type,
        due_date=due_date,
        assigned_to=get_default_inspector_for_playground(inspection.playground, inspection.inspection_type),
        source=InspectionTask.SOURCE_AUTOMATIC,
        created_from_inspection=inspection,
    )
    task.refresh_status(save=True)
    return task


def create_follow_up_task_for_cancelled_task(cancelled_task):
    rule, _created = InspectionRule.objects.get_or_create(
        organization=cancelled_task.organization,
        inspection_type=cancelled_task.inspection_type,
        defaults={
            "interval_days": InspectionRule.get_default_interval_days(cancelled_task.inspection_type),
            "applies_to_all_playgrounds": True,
            "is_active": True,
        },
    )

    if not rule.is_active or not rule.applies_to_all_playgrounds:
        return None

    existing_open_task = get_open_task_for(cancelled_task.playground, cancelled_task.inspection_type)

    if existing_open_task:
        return existing_open_task

    due_date = cancelled_task.due_date + timedelta(days=rule.interval_days)

    task = InspectionTask.objects.create(
        organization=cancelled_task.organization,
        playground=cancelled_task.playground,
        inspection_type=cancelled_task.inspection_type,
        due_date=due_date,
        assigned_to=get_default_inspector_for_playground(cancelled_task.playground, cancelled_task.inspection_type),
        source=InspectionTask.SOURCE_AUTOMATIC,
        note=f"Folgeauftrag aus abgebrochenem Auftrag #{cancelled_task.id}.",
    )
    task.refresh_status(save=True)
    return task


def cancel_task_and_create_follow_up_task(task, cancellation_reason):
    cancellation_reason = cancellation_reason.strip()

    if not cancellation_reason:
        raise ValueError("Ein Abbruchgrund ist erforderlich.")

    existing_note = task.note.strip()
    cancellation_note = f"Abbruchgrund: {cancellation_reason}"
    task.note = f"{existing_note}\n\n{cancellation_note}" if existing_note else cancellation_note
    task.status = InspectionTask.STATUS_CANCELLED
    task.save(update_fields=["note", "status", "updated_at"])

    return create_follow_up_task_for_cancelled_task(task)


def update_planning_after_completed_inspection(inspection):
    if inspection.status != Inspection.STATUS_COMPLETED:
        return {
            "completed_task": None,
            "follow_up_task": None,
        }

    with transaction.atomic():
        completed_task = complete_matching_task_for_inspection(inspection)
        follow_up_task = create_follow_up_task_for_inspection(inspection)

    return {
        "completed_task": completed_task,
        "follow_up_task": follow_up_task,
    }


def get_next_public_task_for_playground(playground):
    today = timezone.localdate()

    return (
        InspectionTask.objects
        .filter(
            playground=playground,
            status__in=[
                InspectionTask.STATUS_OPEN,
                InspectionTask.STATUS_PLANNED,
                InspectionTask.STATUS_OVERDUE,
                InspectionTask.STATUS_SUSPENDED,
            ],
            due_date__gte=today,
        )
        .order_by("due_date", "inspection_type")
        .first()
    )
