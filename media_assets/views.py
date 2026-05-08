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


def image_content(request, image_id):
    image = get_object_or_404(ImageAsset, id=image_id)

    if not image.public_visible and not request.user.is_authenticated:
        raise Http404("Bild nicht gefunden.")

    return HttpResponse(
        image.data,
        content_type=image.mime_type,
    )


def image_thumbnail(request, image_id):
    image = get_object_or_404(ImageAsset, id=image_id)

    if not image.public_visible and not request.user.is_authenticated:
        raise Http404("Bild nicht gefunden.")

    if image.thumbnail_data:
        return HttpResponse(
            image.thumbnail_data,
            content_type=image.mime_type,
        )

    return HttpResponse(
        image.data,
        content_type=image.mime_type,
    )