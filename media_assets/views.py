# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404

from .models import ImageAsset


def user_may_view_image(user, image):
    if image.public_visible:
        return True

    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    profile = getattr(user, "profile", None)

    return bool(
        profile
        and profile.is_active_for_organization
        and profile.may_view_internal
        and image.organization_id == profile.organization_id
    )


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
