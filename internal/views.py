# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import models
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from inspections.models import (
    Defect,
    Inspection,
    InspectionAnswer,
    InspectionCriterion,
    InspectionCriterionApplicability,
    InspectionScope,
)
from playgrounds.models import (
    PlayEquipment,
    Playground,
    PlaygroundAccessory,
    PlaygroundSurface,
)

from .forms import (
    DefectCreateForm,
    DefectEditForm,
    DefectFromInspectionAnswerForm,
)
from .image_utils import (
    delete_selected_defect_images,
    handle_defect_image_uploads,
    sync_defect_image_visibility,
)
from .permissions import (
    require_inspection_permission,
    require_internal_view_permission,
    require_maintenance_permission,
)


@login_required
def create_inspection(request, organization_slug, playground_slug):
    playground = get_object_or_404(
        Playground.objects.select_related("organization"),
        organization__slug=organization_slug,
        slug=playground_slug,
        is_active=True,
        public_visible=True,
        organization__is_active=True,
    )

    require_inspection_permission(request.user, playground.organization)

    if request.method == "POST":
        inspection_type = request.POST.get("inspection_type") or Inspection.TYPE_VISUAL

        inspection = Inspection.objects.create(
            playground=playground,
            inspection_type=inspection_type,
            inspected_at=timezone.localdate(),
            inspector=request.user,
            result=Inspection.RESULT_OK,
        )

        create_default_answers(inspection)

        messages.success(request, "Neue Kontrolle wurde angelegt.")
        return redirect("internal:inspection_detail", inspection_id=inspection.id)

    return render(
        request,
        "internal/create_inspection.html",
        {
            "playground": playground,
            "inspection_types": Inspection.TYPE_CHOICES,
        },
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
def create_defect(request, organization_slug, playground_slug):
    playground = get_object_or_404(
        Playground.objects.select_related("organization"),
        organization__slug=organization_slug,
        slug=playground_slug,
        is_active=True,
        public_visible=True,
        organization__is_active=True,
    )

    require_maintenance_permission(request.user, playground.organization)

    selected_equipment = None
    selected_equipment_id = request.GET.get("equipment")

    if selected_equipment_id:
        selected_equipment = get_object_or_404(
            PlayEquipment.objects.select_related("equipment_type"),
            id=selected_equipment_id,
            playground=playground,
            is_active=True,
        )

    if request.method == "POST":
        form = DefectCreateForm(request.POST, playground=playground)

        if form.is_valid():
            defect = form.save(commit=False)
            defect.playground = playground
            defect.inspection = None
            defect.save()

            if not save_defect_images_or_add_error(request, defect):
                defect.delete()
            else:
                messages.success(request, "Der Mangel wurde erfasst.")
                return redirect(
                    "internal:edit_defect",
                    defect_id=defect.id,
                )
    else:
        initial = {}

        if selected_equipment:
            initial["equipment"] = selected_equipment

        form = DefectCreateForm(initial=initial, playground=playground)

    return render(
        request,
        "internal/create_defect.html",
        {
            "playground": playground,
            "form": form,
            "selected_equipment": selected_equipment,
            "defect_images": [],
        },
    )


@login_required
def create_defect_from_inspection_answer(request, answer_id):
    answer = get_object_or_404(
        InspectionAnswer.objects.select_related(
            "criterion",
            "inspection",
            "inspection__playground",
            "inspection__playground__organization",
            "scope",
            "scope__equipment",
            "scope__surface",
            "scope__accessory",
            "equipment",
        ),
        id=answer_id,
    )

    inspection = answer.inspection
    playground = inspection.playground
    organization = playground.organization

    require_maintenance_permission(request.user, organization)

    if inspection.status == Inspection.STATUS_COMPLETED:
        messages.error(
            request,
            "Aus einer abgeschlossenen Kontrolle kann kein neuer Mangel erfasst werden.",
        )
        return redirect("internal:inspection_detail", inspection_id=inspection.id)

    if answer.answer != InspectionAnswer.ANSWER_DEFECT:
        messages.error(
            request,
            "Ein Mangel kann erst aus einem Prüfpunkt erfasst werden, wenn die Prüfantwort auf «Mangel» gesetzt wurde.",
        )
        return redirect("internal:inspection_detail", inspection_id=inspection.id)

    if request.method == "POST":
        form = DefectFromInspectionAnswerForm(
            request.POST,
            inspection_answer=answer,
        )

        if form.is_valid():
            defect = form.save(commit=False)
            defect.playground = playground
            defect.inspection = inspection
            defect.inspection_answer = answer
            defect.source_type = Defect.SOURCE_INSPECTION

            scope = answer.scope

            if scope and scope.scope_type == InspectionScope.SCOPE_EQUIPMENT:
                defect.equipment = answer.equipment or scope.equipment
            elif scope and scope.scope_type == InspectionScope.SCOPE_SURFACE:
                defect.surface = scope.surface
            elif scope and scope.scope_type == InspectionScope.SCOPE_ACCESSORY:
                defect.accessory = scope.accessory

            defect.save()

            if not save_defect_images_or_add_error(request, defect):
                defect.delete()
            else:
                messages.success(request, "Der Mangel wurde aus dem Prüfpunkt erfasst.")
                return redirect("internal:edit_defect", defect_id=defect.id)
    else:
        form = DefectFromInspectionAnswerForm(inspection_answer=answer)

    existing_defects = answer.defects.all().order_by(
        "-has_safety_risk",
        "planned_resolution_date",
        "-created_at",
    )

    return render(
        request,
        "internal/create_defect_from_inspection_answer.html",
        {
            "answer": answer,
            "existing_defects": existing_defects,
            "form": form,
            "inspection": inspection,
            "playground": playground,
            "defect_images": [],
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
        ).prefetch_related("images", "images__image"),
        id=defect_id,
    )

    playground = defect.playground

    if not playground:
        messages.error(request, "Dieser Mangel ist keinem Spielplatz zugeordnet.")
        return redirect("public:index")

    require_internal_view_permission(request.user, playground.organization)
    can_edit_defect = user_can_create_defects(request.user, playground.organization)

    if request.method == "POST":
        require_maintenance_permission(request.user, playground.organization)

        form = DefectEditForm(
            request.POST,
            instance=defect,
            playground=playground,
        )

        if form.is_valid():
            defect = form.save(commit=False)
            defect.playground = playground
            defect.save()

            if save_defect_images_or_add_error(request, defect):
                messages.success(request, "Der Mangel wurde gespeichert.")
                return redirect("internal:edit_defect", defect_id=defect.id)
    else:
        form = DefectEditForm(instance=defect, playground=playground)

    if not can_edit_defect:
        for field in form.fields.values():
            field.disabled = True

    return render(
        request,
        "internal/edit_defect.html",
        {
            "defect": defect,
            "form": form,
            "playground": playground,
            "defect_images": defect.images.select_related("image").all(),
            "can_edit_defect": can_edit_defect,
        },
    )


@login_required
def inspection_detail(request, inspection_id):
    inspection = get_object_or_404(
        Inspection.objects
        .select_related("playground", "playground__organization", "inspector"),
        id=inspection_id,
    )

    require_inspection_permission(request.user, inspection.playground.organization)

    answers = (
        inspection.answers
        .select_related(
            "criterion",
            "scope",
            "scope__equipment",
            "scope__equipment__equipment_type",
            "scope__surface",
            "scope__accessory",
        )
        .prefetch_related("defects")
        .order_by("scope__sort_order", "criterion__area", "criterion__title")
    )

    scopes = (
        inspection.scopes
        .select_related(
            "equipment",
            "equipment__equipment_type",
            "surface",
            "accessory",
        )
        .prefetch_related("answers", "answers__criterion", "answers__defects")
        .order_by("sort_order", "label")
    )

    pending_answers_count = answers.filter(
        answer=InspectionAnswer.ANSWER_PENDING
    ).count()

    can_create_defects = user_can_create_defects(
        request.user,
        inspection.playground.organization,
    )

    return render(
        request,
        "internal/inspection_detail.html",
        {
            "inspection": inspection,
            "answers": answers,
            "can_create_defects": can_create_defects,
            "scopes": scopes,
            "pending_answers_count": pending_answers_count,
        },
    )


@login_required
@require_POST
def save_inspection_answers(request, inspection_id):
    inspection = get_object_or_404(
        Inspection.objects.select_related(
            "playground",
            "playground__organization",
            "inspector",
        ),
        id=inspection_id,
    )

    require_inspection_permission(request.user, inspection.playground.organization)

    if inspection.status == Inspection.STATUS_COMPLETED:
        messages.error(
            request,
            "Diese Kontrolle ist bereits abgeschlossen und kann nicht mehr bearbeitet werden.",
        )
        return redirect("internal:inspection_detail", inspection_id=inspection.id)

    answers = inspection.answers.select_related("criterion", "scope")

    updated_count = 0

    valid_answers = {
        InspectionAnswer.ANSWER_PENDING,
        InspectionAnswer.ANSWER_OK,
        InspectionAnswer.ANSWER_DEFECT,
        InspectionAnswer.ANSWER_NOT_APPLICABLE,
    }

    for answer in answers:
        answer_value = request.POST.get(f"answer_{answer.id}")
        comment_value = request.POST.get(f"comment_{answer.id}", "")

        if answer_value not in valid_answers:
            continue

        changed = False

        if answer.answer != answer_value:
            answer.answer = answer_value
            changed = True

        if answer.comment != comment_value:
            answer.comment = comment_value
            changed = True

        if changed:
            answer.save(update_fields=["answer", "comment"])
            updated_count += 1

    if updated_count:
        messages.success(
            request,
            f"{updated_count} Prüfantwort(en) gespeichert.",
        )
    else:
        messages.info(
            request,
            "Es gab keine Änderungen an den Prüfantworten.",
        )

    return redirect("internal:inspection_detail", inspection_id=inspection.id)


@login_required
@require_POST
def complete_inspection(request, inspection_id):
    inspection = get_object_or_404(
        Inspection.objects.select_related(
            "playground",
            "playground__organization",
            "inspector",
        ),
        id=inspection_id,
    )

    require_inspection_permission(request.user, inspection.playground.organization)

    if inspection.status == Inspection.STATUS_COMPLETED:
        messages.info(request, "Diese Kontrolle ist bereits abgeschlossen.")
        return redirect("internal:inspection_detail", inspection_id=inspection.id)

    pending_count = inspection.answers.filter(
        answer=InspectionAnswer.ANSWER_PENDING
    ).count()

    if pending_count:
        messages.error(
            request,
            (
                "Die Kontrolle kann noch nicht abgeschlossen werden. "
                f"Es sind noch {pending_count} Prüfpunkte offen."
            ),
        )
        return redirect("internal:inspection_detail", inspection_id=inspection.id)

    has_defects = inspection.answers.filter(
        answer=InspectionAnswer.ANSWER_DEFECT
    ).exists()

    inspection.status = Inspection.STATUS_COMPLETED
    inspection.completed_at = timezone.now()
    inspection.completed_by = request.user

    if has_defects:
        inspection.result = Inspection.RESULT_DEFECTS
    else:
        inspection.result = Inspection.RESULT_OK

    inspection.save(
        update_fields=[
            "status",
            "completed_at",
            "completed_by",
            "result",
        ]
    )

    messages.success(request, "Die Kontrolle wurde abgeschlossen.")
    return redirect("internal:inspection_detail", inspection_id=inspection.id)


def user_can_create_defects(user, organization):
    if user.is_superuser:
        return True

    profile = getattr(user, "profile", None)

    if not profile:
        return False

    if not profile.is_active_for_organization:
        return False

    if profile.organization_id != organization.id:
        return False

    return profile.may_maintain


def get_allowed_minimum_inspection_types(inspection_type):
    if inspection_type == Inspection.TYPE_VISUAL:
        return [
            InspectionCriterion.MINIMUM_VISUAL,
        ]

    if inspection_type == Inspection.TYPE_OPERATIONAL:
        return [
            InspectionCriterion.MINIMUM_VISUAL,
            InspectionCriterion.MINIMUM_OPERATIONAL,
        ]

    if inspection_type == Inspection.TYPE_ANNUAL:
        return [
            InspectionCriterion.MINIMUM_VISUAL,
            InspectionCriterion.MINIMUM_OPERATIONAL,
            InspectionCriterion.MINIMUM_ANNUAL,
        ]

    return [
        InspectionCriterion.MINIMUM_VISUAL,
        InspectionCriterion.MINIMUM_OPERATIONAL,
        InspectionCriterion.MINIMUM_ANNUAL,
    ]


def create_default_answers(inspection):
    organization = inspection.playground.organization

    allowed_minimum_types = get_allowed_minimum_inspection_types(
        inspection.inspection_type
    )

    base_criteria = (
        InspectionCriterion.objects
        .filter(is_active=True)
        .filter(minimum_inspection_type__in=allowed_minimum_types)
        .filter(
            models.Q(organization__isnull=True)
            | models.Q(organization=organization)
        )
        .distinct()
    )

    playground_criteria = list(
        base_criteria
        .filter(
            applicabilities__scope_type=InspectionCriterionApplicability.SCOPE_PLAYGROUND
        )
        .order_by("area", "title")
        .distinct()
    )

    surface_criteria = list(
        base_criteria
        .filter(
            applicabilities__scope_type=InspectionCriterionApplicability.SCOPE_SURFACE
        )
        .order_by("area", "title")
        .distinct()
    )

    accessory_criteria = list(
        base_criteria
        .filter(
            applicabilities__scope_type=InspectionCriterionApplicability.SCOPE_ACCESSORY
        )
        .order_by("area", "title")
        .distinct()
    )

    scopes_with_criteria = []

    playground_scope, _ = InspectionScope.objects.get_or_create(
        inspection=inspection,
        scope_type=InspectionScope.SCOPE_PLAYGROUND,
        equipment=None,
        surface=None,
        accessory=None,
        defaults={
            "label": "Allgemeine Spielplatzprüfung",
            "sort_order": 0,
        },
    )

    scopes_with_criteria.append((playground_scope, playground_criteria))

    if inspection.inspection_type == Inspection.TYPE_VISUAL:
        existing_pairs = set(
            InspectionAnswer.objects
            .filter(inspection=inspection)
            .values_list("scope_id", "criterion_id")
        )
    
        answers_to_create = []
    
        for criterion in playground_criteria:
            key = (playground_scope.id, criterion.id)
    
            if key in existing_pairs:
                continue
            
            answers_to_create.append(
                InspectionAnswer(
                    inspection=inspection,
                    scope=playground_scope,
                    criterion=criterion,
                    equipment=None,
                    answer=InspectionAnswer.ANSWER_PENDING,
                )
            )
    
        InspectionAnswer.objects.bulk_create(answers_to_create)
        return

    equipment_list = list(
        PlayEquipment.objects
        .filter(
            playground=inspection.playground,
            is_active=True,
            public_visible=True,
        )
        .select_related("equipment_type")
        .order_by("name")
    )

    for index, equipment in enumerate(equipment_list, start=1):
        equipment_scope, _ = InspectionScope.objects.get_or_create(
            inspection=inspection,
            scope_type=InspectionScope.SCOPE_EQUIPMENT,
            equipment=equipment,
            surface=None,
            accessory=None,
            defaults={
                "label": equipment.name,
                "sort_order": index * 10,
            },
        )

        equipment_criteria = list(
            base_criteria
            .filter(
                applicabilities__scope_type=InspectionCriterionApplicability.SCOPE_EQUIPMENT
            )
            .filter(
                models.Q(applicabilities__applies_to_all_equipment=True)
                | models.Q(applicabilities__equipment_types=equipment.equipment_type)
            )
            .order_by("area", "title")
            .distinct()
        )

        scopes_with_criteria.append((equipment_scope, equipment_criteria))

    surface_list = list(
        PlaygroundSurface.objects
        .filter(
            playground=inspection.playground,
            is_active=True,
            public_visible=True,
        )
        .order_by("name")
    )

    surface_offset = 1000

    for index, surface in enumerate(surface_list, start=1):
        surface_scope, _ = InspectionScope.objects.get_or_create(
            inspection=inspection,
            scope_type=InspectionScope.SCOPE_SURFACE,
            equipment=None,
            surface=surface,
            accessory=None,
            defaults={
                "label": surface.name,
                "sort_order": surface_offset + index * 10,
            },
        )

        scopes_with_criteria.append((surface_scope, surface_criteria))

    accessory_list = list(
        PlaygroundAccessory.objects
        .filter(
            playground=inspection.playground,
            is_active=True,
            public_visible=True,
        )
        .order_by("name")
    )

    accessory_offset = 2000

    for index, accessory in enumerate(accessory_list, start=1):
        accessory_scope, _ = InspectionScope.objects.get_or_create(
            inspection=inspection,
            scope_type=InspectionScope.SCOPE_ACCESSORY,
            equipment=None,
            surface=None,
            accessory=accessory,
            defaults={
                "label": accessory.name,
                "sort_order": accessory_offset + index * 10,
            },
        )

        scopes_with_criteria.append((accessory_scope, accessory_criteria))

    existing_pairs = set(
        InspectionAnswer.objects
        .filter(inspection=inspection)
        .values_list("scope_id", "criterion_id")
    )

    answers_to_create = []

    for scope, criteria in scopes_with_criteria:
        for criterion in criteria:
            key = (scope.id, criterion.id)

            if key in existing_pairs:
                continue

            answers_to_create.append(
                InspectionAnswer(
                    inspection=inspection,
                    scope=scope,
                    criterion=criterion,
                    equipment=scope.equipment,
                    answer=InspectionAnswer.ANSWER_PENDING,
                )
            )

    InspectionAnswer.objects.bulk_create(answers_to_create)
