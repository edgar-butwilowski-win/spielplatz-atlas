# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

from django.contrib import messages
from django.db.models import Prefetch
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from inspections.models import Defect, Inspection
from playgrounds.models import PlayEquipment, Playground
from tenants.forms import OrganizationRegistrationRequestForm


def index(request):
    return render(request, "public/index.html")


def public_playgrounds_api(request):
    playgrounds = (
        Playground.objects
        .select_related("organization", "photo")
        .prefetch_related(
            Prefetch(
                "equipment",
                queryset=(
                    PlayEquipment.objects
                    .filter(
                        is_active=True,
                        public_visible=True,
                        photo__isnull=False,
                    )
                    .select_related("photo", "equipment_type")
                    .order_by("name")
                ),
            )
        )
        .filter(
            is_active=True,
            public_visible=True,
            organization__is_active=True,
            organization__is_public=True,
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


def playground_detail(request, organization_slug, playground_slug):
    playground = get_object_or_404(
        Playground.objects
        .select_related("organization", "photo")
        .prefetch_related(
            Prefetch(
                "equipment",
                queryset=(
                    PlayEquipment.objects
                    .filter(is_active=True, public_visible=True)
                    .select_related("equipment_type", "photo")
                    .order_by("name")
                ),
            )
        ),
        organization__slug=organization_slug,
        slug=playground_slug,
        is_active=True,
        public_visible=True,
        organization__is_active=True,
        organization__is_public=True,
    )

    preview_photo = playground.get_preview_photo()

    equipment_list = list(playground.equipment.all())

    public_defects = (
        Defect.objects
        .select_related(
            "equipment",
            "surface",
            "accessory",
            "inspection",
        )
        .filter(
            playground=playground,
            public_visible=True,
        )
        .exclude(
            status__in=[
                Defect.STATUS_DONE,
                Defect.STATUS_VERIFIED,
            ]
        )
        .order_by(
            "-has_safety_risk",
            "planned_resolution_date",
            "-created_at",
        )
    )

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

    for defect in public_defects:
        if defect.equipment_id:
            defects_by_equipment_id.setdefault(defect.equipment_id, []).append(defect)

    for equipment in equipment_list:
        equipment.public_defects = defects_by_equipment_id.get(equipment.id, [])
        equipment.has_public_defect = bool(equipment.public_defects)
        equipment.has_public_safety_risk = any(
            defect.has_safety_risk for defect in equipment.public_defects
        )

    can_create_inspection = False
    can_create_defect = False

    if request.user.is_authenticated:
        if request.user.is_superuser:
            can_create_inspection = True
            can_create_defect = True
        else:
            profile = getattr(request.user, "profile", None)

            if profile and profile.organization_id == playground.organization_id:
                can_create_inspection = profile.may_inspect
                can_create_defect = profile.may_maintain

    context = {
        "playground": playground,
        "equipment_list": equipment_list,
        "public_defects": public_defects,
        "can_create_inspection": can_create_inspection,
        "can_create_defect": can_create_defect,
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