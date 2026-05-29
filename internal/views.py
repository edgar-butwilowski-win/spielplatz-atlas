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
from inspections.planning import update_planning_after_completed_inspection
from notifications.forms import DefectAssignmentForm
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
    EquipmentRenovationForm,
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
        organization__is_active=True,
    )

    require_inspection_permission(request.user, playground.organization)

    if playground.is_inspection_suspended:
        messages.error(
            request,
            "Für diesen Spielplatz ist die Inspektion aktuell ausgesetzt. Es kann keine neue Kontrolle erfasst werden.",
        )
        return redirect(
            "public:playground_detail",
            organization_slug=playground.organization.slug,
            playground_slug=playground.slug,
        )

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
@require_POST
def update_equipment_renovation(request, equipment_id):
    equipment = get_object_or_404(
        PlayEquipment.objects.select_related("playground", "playground__organization"),
        id=equipment_id,
    )
    playground = equipment.playground

    require_maintenance_permission(request.user, playground.organization)

    form = EquipmentRenovationForm(request.POST, instance=equipment)

    if form.is_valid():
        form.save()
        messages.success(request, "Die Sanierungsangaben wurden gespeichert.")
    else:
        for errors in form.errors.values():
            for error in errors:
                messages.error(request, error)

    return redirect(
        "public:playground_detail",
        organization_slug=playground.organization.slug,
        playground_slug=playground.slug,
    )


@login_required
def create_defect(request, organization_slug, playground_slug):
    playground = get_object_or_404(
        Playground.objects.select_related("organization"),
        organization__slug=organization_slug,
        slug=playground_slug,
        is_active=True,
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
            "assignment",
            "assignment__assigned_to",
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
            "scope__equipment__photo",
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
            "equipment__photo",
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

    update_planning_after_completed_inspection(inspection)

    messages.success(request, "Die Kontrolle wurde abgeschlossen. Die nächste fällige Kontrolle wurde in der Einsatzplanung aktualisiert.")
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
        return [InspectionCriterion.MINIMUM_VISUAL]

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

    return [InspectionCriterion.MINIMUM_VISUAL]


def get_active_criteria_for_inspection(inspection):
    minimum_types = get_allowed_minimum_inspection_types(inspection.inspection_type)

    return (
        InspectionCriterion.objects
        .filter(is_active=True)
        .filter(
            models.Q(organization=inspection.playground.organization)
            | models.Q(organization__isnull=True, is_standard=True)
        )
        .filter(minimum_inspection_type__in=minimum_types)
        .distinct()
    )


def create_default_answers(inspection):
    criteria = get_active_criteria_for_inspection(inspection)
    playground = inspection.playground

    InspectionScope.objects.create(
        inspection=inspection,
        scope_type=InspectionScope.SCOPE_PLAYGROUND,
        label="Allgemeine Spielplatzprüfung",
        sort_order=0,
    )

    equipment_list = playground.equipment.filter(
        is_active=True,
        public_visible=True,
        not_to_inspect=False,
    ).select_related("equipment_type").order_by("sequence_number", "name")

    surfaces = playground.surfaces.filter(is_active=True, public_visible=True).order_by("name")
    accessories = playground.accessories.filter(is_active=True, public_visible=True).order_by("name")

    sort_order = 10

    for equipment in equipment_list:
        InspectionScope.objects.create(
            inspection=inspection,
            scope_type=InspectionScope.SCOPE_EQUIPMENT,
            label=equipment.name,
            equipment=equipment,
            sort_order=sort_order,
        )
        sort_order += 10

    for surface in surfaces:
        InspectionScope.objects.create(
            inspection=inspection,
            scope_type=InspectionScope.SCOPE_SURFACE,
            label=surface.name,
            surface=surface,
            sort_order=sort_order,
        )
        sort_order += 10

    for accessory in accessories:
        InspectionScope.objects.create(
            inspection=inspection,
            scope_type=InspectionScope.SCOPE_ACCESSORY,
            label=accessory.name,
            accessory=accessory,
            sort_order=sort_order,
        )
        sort_order += 10

    scopes = inspection.scopes.select_related("equipment", "surface", "accessory")

    for scope in scopes:
        if scope.scope_type == InspectionScope.SCOPE_PLAYGROUND:
            applicable_criteria = criteria.filter(
                applicabilities__scope_type=InspectionCriterionApplicability.SCOPE_PLAYGROUND,
            )
        elif scope.scope_type == InspectionScope.SCOPE_EQUIPMENT and scope.equipment:
            applicable_criteria = (
                criteria
                .filter(applicabilities__scope_type=InspectionCriterionApplicability.SCOPE_EQUIPMENT)
                .filter(
                    models.Q(applicabilities__applies_to_all_equipment=True)
                    | models.Q(applicabilities__equipment_types=scope.equipment.equipment_type)
                )
                .distinct()
            )
        elif scope.scope_type == InspectionScope.SCOPE_SURFACE:
            applicable_criteria = criteria.filter(
                applicabilities__scope_type=InspectionCriterionApplicability.SCOPE_SURFACE,
            )
        elif scope.scope_type == InspectionScope.SCOPE_ACCESSORY:
            applicable_criteria = criteria.filter(
                applicabilities__scope_type=InspectionCriterionApplicability.SCOPE_ACCESSORY,
            )
        else:
            applicable_criteria = InspectionCriterion.objects.none()

        for criterion in applicable_criteria:
            InspectionAnswer.objects.create(
                inspection=inspection,
                scope=scope,
                criterion=criterion,
                equipment=scope.equipment if scope.scope_type == InspectionScope.SCOPE_EQUIPMENT else None,
            )
