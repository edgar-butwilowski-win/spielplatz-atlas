# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

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
    tasks = queryset or InspectionTask.objects.exclude(
        status__in=[
            InspectionTask.STATUS_COMPLETED,
            InspectionTask.STATUS_CANCELLED,
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
    ).select_related("organization")

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

    # Falls bereits ein offener Folgeauftrag existiert, wird kein zweiter Auftrag erzeugt.
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
        source=InspectionTask.SOURCE_AUTOMATIC,
        created_from_inspection=inspection,
    )
    task.refresh_status(save=True)
    return task


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
