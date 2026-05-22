from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404

from accounts.permissions import user_may_view_internal
from playgrounds.models import PlayEquipment, Playground

from .models import ImageAsset


def image_is_used_as_defect_image(image):
    return image.defect_images.exists()


def image_is_public_playground_photo(image):
    return Playground.objects.filter(
        photo=image,
        is_active=True,
        public_visible=True,
        organization__is_active=True,
        organization__is_public=True,
    ).exists()


def image_is_public_equipment_photo(image):
    return PlayEquipment.objects.filter(
        photo=image,
        is_active=True,
        public_visible=True,
        playground__is_active=True,
        playground__public_visible=True,
        playground__organization__is_active=True,
        playground__organization__is_public=True,
    ).exists()


def image_is_public_playground_or_equipment_photo(image):
    return image_is_public_playground_photo(image) or image_is_public_equipment_photo(image)


def user_may_view_organization_image(user, image):
    if user.is_superuser:
        return True

    if image.organization_id and user_may_view_internal(user, image.organization):
        return True

    return False


def user_may_view_image(user, image):
    if image_is_used_as_defect_image(image):
        return user_may_view_organization_image(user, image)

    if image_is_public_playground_or_equipment_photo(image):
        return True

    return user_may_view_organization_image(user, image)


def get_permitted_image_or_404(request, image_id):
    image = get_object_or_404(ImageAsset.objects.select_related("organization"), id=image_id)

    if not user_may_view_image(request.user, image):
        raise Http404("Bild nicht gefunden.")

    return image


def image_content(request, image_id):
    image = get_permitted_image_or_404(request, image_id)

    return HttpResponse(image.data, content_type=image.mime_type)


def image_thumbnail(request, image_id):
    image = get_permitted_image_or_404(request, image_id)

    if image.thumbnail_data:
        return HttpResponse(image.thumbnail_data, content_type=image.mime_type)

    return HttpResponse(image.data, content_type=image.mime_type)
