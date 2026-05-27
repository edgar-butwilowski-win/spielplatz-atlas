from django.db.models import Prefetch, Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone

from accounts.permissions import get_active_profile
from inspections.planning import get_next_public_task_for_playground
from playgrounds.models import PlayEquipment, Playground
from tenants.models import Organization


MONTH_NAMES_DE = {
    1: "Januar",
    2: "Februar",
    3: "März",
    4: "April",
    5: "Mai",
    6: "Juni",
    7: "Juli",
    8: "August",
    9: "September",
    10: "Oktober",
    11: "November",
    12: "Dezember",
}


def organization_index(request, organization_slug):
    organization = get_object_or_404(
        Organization,
        slug=organization_slug,
        is_active=True,
        is_public=True,
    )
    return render(
        request,
        "public/index.html",
        {
            "organization_filter": organization,
        },
    )


def format_month_year(date_value):
    if not date_value:
        return "wird geplant"

    return f"{MONTH_NAMES_DE[date_value.month]} {date_value.year}"


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

    profile = get_active_profile(user)

    if profile and profile.may_view_internal:
        return qs.filter(
            Q(public_visible=True)
            | Q(organization_id=profile.organization_id)
        )

    return qs.filter(public_visible=True)


def public_equipment_with_photo_queryset():
    today = timezone.localdate()

    return (
        PlayEquipment.objects
        .filter(is_active=True, public_visible=True, photo__isnull=False)
        .filter(Q(demolition_date__isnull=True) | Q(demolition_date__gte=today))
        .select_related("photo")
        .order_by("name")
    )


def get_public_next_inspection_label(playground):
    if playground.is_inspection_suspended:
        return "wird geplant"

    task = get_next_public_task_for_playground(playground)

    if not task:
        return "wird geplant"

    return format_month_year(task.planned_date or task.due_date)


def public_playgrounds_api(request):
    playgrounds = playground_base_queryset_for_user(request.user)
    organization_slug = (request.GET.get("organization") or "").strip()

    if organization_slug:
        organization = get_object_or_404(
            Organization,
            slug=organization_slug,
            is_active=True,
            is_public=True,
        )
        playgrounds = playgrounds.filter(organization=organization)

    playgrounds = (
        playgrounds
        .select_related("organization")
        .filter(latitude__isnull=False, longitude__isnull=False)
        .only(
            "id",
            "name",
            "address",
            "district",
            "latitude",
            "longitude",
            "public_visible",
            "slug",
            "organization__name",
            "organization__slug",
        )
        .order_by("organization__name", "name")
    )

    features = []

    for playground in playgrounds.iterator(chunk_size=500):
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
                "detail_url": reverse(
                    "public:playground_detail",
                    kwargs={
                        "organization_slug": playground.organization.slug,
                        "playground_slug": playground.slug,
                    },
                ),
                "popup_url": reverse("public:playground_popup_api", args=[playground.id]),
            },
        })

    return JsonResponse({"type": "FeatureCollection", "features": features})


def public_playground_popup_api(request, playground_id):
    playground = get_object_or_404(
        playground_base_queryset_for_user(request.user)
        .select_related("organization", "photo")
        .prefetch_related(
            Prefetch("equipment", queryset=public_equipment_with_photo_queryset())
        ),
        id=playground_id,
        latitude__isnull=False,
        longitude__isnull=False,
    )

    preview_photo = playground.get_preview_photo()
    preview_photo_url = None

    if preview_photo:
        preview_photo_url = reverse("media_assets:image_content", args=[preview_photo.id])

    return JsonResponse({
        "preview_photo_url": preview_photo_url,
        "next_inspection_label": get_public_next_inspection_label(playground),
    })
