# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404

from playgrounds.models import PlayEquipment, Playground

from .models import ImageAsset


def user_may_view_organization_image(user, image):
    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    profile = getattr(user, "profile", None)

    if not (
        profile
        and profile.is_active_for_organization
        and profile.may_view_internal
    ):
        return False

    if image.organization_id == profile.organization_id:
        return True

    return image.defect_images.filter(
        defect__playground__organization_id=profile.organization_id,
    ).exists()


def image_is_used_as_defect_image(image):
    return image.defect_images.exists()


def image_is_public_playground_or_equipment_photo(image):
    if image_is_used_as_defect_image(image):
        return False

    if Playground.objects.filter(
        photo=image,
        is_active=True,
        public_visible=True,
        organization__is_active=True,
        organization__is_public=True,
    ).exists():
        return True

    return PlayEquipment.objects.filter(
        photo=image,
        is_active=True,
        public_visible=True,
        playground__is_active=True,
        playground__public_visible=True,
        playground__organization__is_active=True,
        playground__organization__is_public=True,
    ).exists()


def user_may_view_image(user, image):
    if image_is_public_playground_or_equipment_photo(image):
        return True

    if image_is_used_as_defect_image(image):
        return user_may_view_organization_image(user, image)

    if image.public_visible:
        return True

    return user_may_view_organization_image(user, image)


def get_permitted_image_or_404(request, image_id):
    image = get_object_or_404(ImageAsset, id=image_id)

    if not user_may_view_image(request.user, image):
        raise Http404("Bild nicht gefunden.")

    return image


def image_content(request, image_id):
    image = get_permitted_image_or_404(request, image_id)

    return HttpResponse(
        image.data,
        content_type=image.mime_type,
    )


def image_thumbnail(request, image_id):
    image = get_permitted_image_or_404(request, image_id)

    if image.thumbnail_data:
        return HttpResponse(
            image.thumbnail_data,
            content_type=image.mime_type,
        )

    return HttpResponse(
        image.data,
        content_type=image.mime_type,
    )
