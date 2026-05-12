# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

from django.contrib import messages
from django.db.models import Prefetch, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from inspections.models import Defect, Inspection
from playgrounds.models import PlayEquipment, Playground
from tenants.forms import OrganizationRegistrationRequestForm


def public_equipment_queryset():
    today = timezone.localdate()

    return (
        PlayEquipment.objects
        .filter(is_active=True, public_visible=True)
        .filter(Q(demolition_date__isnull=True) | Q(demolition_date__gte=today))
        .select_related("equipment_type", "photo", "supplier")
        .order_by("sequence_number", "name")
    )


def user_can_view_private_playground(user, playground):
    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    profile = getattr(user, "profile", None)

    return bool(
        profile
        and profile.is_active_for_organization
        and profile.organization_id == playground.organization_id
        and profile.may_view_internal
    )


def playground_base_queryset_for_user(user):
    qs = Playground.objects.filter(
        is_active=True,
        organization__is_active=True,
        organization__is_public=True,
    )

    if not user.is_authenticated:
        return qs.filter(public_visible=True)

    if user.is_superuser:
        return qs

    profile = getattr(user, "profile", None)

    if profile and profile.is_active_for_organization and profile.may_view_internal:
        return qs.filter(
            Q(public_visible=True)
            | Q(organization_id=profile.organization_id)
        )

    return qs.filter(public_visible=True)


def index(request):
    return render(request, "public/index.html")


def about(request):
    return render(request, "public/about.html")


def imprint(request):
    return render(request, "public/imprint.html")


def public_playgrounds_api(request):
    playgrounds = (
        playground_base_queryset_for_user(request.user)
        .select_related("organization", "photo")
        .prefetch_related(
            Prefetch(
                "equipment",
                queryset=public_equipment_queryset().filter(photo__isnull=False),
            )
        )
        .filter(
            latitude__isnull=False,
            longitude__isnull=False,
        )
        .order_by("organization__name", "name")
    )

    features = []

    for playground in playgrounds:
        preview_photo = playground.get_preview_photo()
        preview_photo_url = None

        if preview_photo:
            preview_photo_url = reverse(
                "media_assets:image_content",
                args=[preview_photo.id],
            )

        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [
                    float(playground.longitude),
                    float(playground.latitude),
                ],
            },
            "properties": {
                "id": playground.id,
                "name": playground.name,
                "address": playground.address,
                "district": playground.district,
                "organization": playground.organization.name,
                "is_public": playground.public_visible,
                "preview_photo_url": preview_photo_url,
                "detail_url": reverse(
                    "public:playground_detail",
                    kwargs={
                        "organization_slug": playground.organization.slug,
                        "playground_slug": playground.slug,
                    },
                ),
            },
        })

    return JsonResponse({
        "type": "FeatureCollection",
        "features": features,
    })


def get_defect_group_key(defect):
    if defect.equipment_id:
        return ("equipment", defect.equipment_id)

    if defect.surface_id:
        return ("surface", defect.surface_id)

    if defect.accessory_id:
        return ("accessory", defect.accessory_id)

    return ("playground", defect.playground_id)


def get_defect_group_label(defect):
    if defect.equipment:
        return defect.equipment.name

    if defect.surface:
        return defect.surface.name

    if defect.accessory:
        return defect.accessory.name

    return "Allgemeiner Spielplatzmangel"


def build_defect_groups(defects):
    groups_by_key = {}
    groups = []

    for defect in defects:
        key = get_defect_group_key(defect)
        group = groups_by_key.get(key)

        if group is None:
            group = {
                "key": key,
                "label": get_defect_group_label(defect),
                "representative": defect,
                "defects": [],
                "has_safety_risk": False,
                "has_internal_defect": False,
            }
            groups_by_key[key] = group
            groups.append(group)

        group["defects"].append(defect)
        group["has_safety_risk"] = group["has_safety_risk"] or defect.has_safety_risk
        group["has_internal_defect"] = group["has_internal_defect"] or not defect.public_visible

    return groups


def playground_detail(request, organization_slug, playground_slug):
    playground = get_object_or_404(
        playground_base_queryset_for_user(request.user)
        .select_related("organization", "photo")
        .prefetch_related(
            Prefetch(
                "equipment",
                queryset=public_equipment_queryset(),
            )
        ),
        organization__slug=organization_slug,
        slug=playground_slug,
    )

    preview_photo = playground.get_preview_photo()
    equipment_list = list(playground.equipment.all())

    can_create_inspection = False
    can_create_defect = False
    can_open_defect = False
    can_view_equipment_renovation = False
    can_edit_equipment_renovation = False

    if request.user.is_authenticated:
        if request.user.is_superuser:
            can_create_inspection = True
            can_create_defect = True
            can_open_defect = True
            can_view_equipment_renovation = True
            can_edit_equipment_renovation = True
        else:
            profile = getattr(request.user, "profile", None)

            if profile and profile.organization_id == playground.organization_id:
                can_create_inspection = profile.may_inspect
                can_create_defect = profile.may_maintain
                can_open_defect = profile.may_view_internal
                can_view_equipment_renovation = profile.may_view_internal
                can_edit_equipment_renovation = profile.may_maintain

    inspection_is_suspended = playground.is_inspection_suspended
    can_start_inspection = can_create_inspection and not inspection_is_suspended

    visible_defects = (
        Defect.objects
        .select_related(
            "equipment",
            "surface",
            "accessory",
            "inspection",
        )
        .filter(playground=playground)
        .exclude(
            status__in=[
                Defect.STATUS_DONE,
                Defect.STATUS_VERIFIED,
            ]
        )
    )

    if not can_open_defect:
        visible_defects = visible_defects.filter(public_visible=True)

    visible_defects = list(
        visible_defects.order_by(
            "public_visible",
            "-has_safety_risk",
            "planned_resolution_date",
            "-created_at",
        )
    )

    defect_groups = build_defect_groups(visible_defects)

    latest_completed_inspection = (
        Inspection.objects
        .filter(
            playground=playground,
            status=Inspection.STATUS_COMPLETED,
        )
        .select_related("inspector", "completed_by")
        .order_by("-inspected_at", "-completed_at", "-created_at")
        .first()
    )

    defects_by_equipment_id = {}

    for defect in visible_defects:
        if defect.equipment_id:
            defects_by_equipment_id.setdefault(defect.equipment_id, []).append(defect)

    for equipment in equipment_list:
        equipment.public_defects = defects_by_equipment_id.get(equipment.id, [])
        equipment.has_public_defect = bool(equipment.public_defects)
        equipment.has_public_safety_risk = any(
            defect.has_safety_risk for defect in equipment.public_defects
        )
        equipment.has_internal_defect = any(
            not defect.public_visible for defect in equipment.public_defects
        )

    context = {
        "playground": playground,
        "equipment_list": equipment_list,
        "public_defects": visible_defects,
        "defect_groups": defect_groups,
        "can_create_inspection": can_create_inspection,
        "can_start_inspection": can_start_inspection,
        "inspection_is_suspended": inspection_is_suspended,
        "can_create_defect": can_create_defect,
        "can_open_defect": can_open_defect,
        "can_view_equipment_renovation": can_view_equipment_renovation,
        "can_edit_equipment_renovation": can_edit_equipment_renovation,
        "renovation_type_choices": PlayEquipment.RENOVATION_TYPE_CHOICES,
        "preview_photo": preview_photo,
        "latest_completed_inspection": latest_completed_inspection,
    }

    return render(request, "public/playground_detail.html", context)


def register_organization(request):
    if request.method == "POST":
        form = OrganizationRegistrationRequestForm(request.POST)

        if form.is_valid():
            form.save()
            messages.success(
                request,
                "Vielen Dank. Ihre Organisationsanfrage wurde eingereicht und wird geprüft.",
            )
            return redirect("public:register_organization_done")
    else:
        form = OrganizationRegistrationRequestForm()

    return render(
        request,
        "public/register_organization.html",
        {
            "form": form,
        },
    )


def register_organization_done(request):
    return render(request, "public/register_organization_done.html")
