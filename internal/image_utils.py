# Copyright (c) 2026 Fachstelle Geoinformation
# Author: Edgar Butwilowski
# All rights reserved.
#
# This source code is the property of the copyright holder.
# Unauthorized copying, modification, distribution, or use is prohibited
# unless expressly permitted in writing.

from io import BytesIO

from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError

from inspections.models import DefectImage
from media_assets.models import ImageAsset


MAX_DEFECT_IMAGES = 3
MAX_IMAGE_EDGE_PX = 1200
THUMBNAIL_EDGE_PX = 360
ALLOWED_IMAGE_FORMATS = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}


def _resize_image(image, max_edge):
    image = image.copy()
    image.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
    return image


def _normalise_image(uploaded_file, max_edge=MAX_IMAGE_EDGE_PX):
    try:
        image = Image.open(uploaded_file)
        image.load()
    except UnidentifiedImageError as exc:
        raise ValidationError("Bitte nur gültige Bilddateien hochladen.") from exc

    image_format = image.format

    if image_format not in ALLOWED_IMAGE_FORMATS:
        raise ValidationError("Bitte nur Bilder im Format JPEG, PNG oder WebP hochladen.")

    mime_type = ALLOWED_IMAGE_FORMATS[image_format]

    if image.mode not in ("RGB", "RGBA"):
        image = image.convert("RGB")

    if image.mode == "RGBA" and image_format == "JPEG":
        image = image.convert("RGB")

    resized_image = _resize_image(image, max_edge)

    output = BytesIO()
    save_format = image_format
    save_kwargs = {}

    if save_format == "JPEG":
        save_kwargs = {
            "quality": 85,
            "optimize": True,
        }
    elif save_format == "PNG":
        save_kwargs = {
            "optimize": True,
        }
    elif save_format == "WEBP":
        save_kwargs = {
            "quality": 85,
            "method": 6,
        }

    resized_image.save(output, format=save_format, **save_kwargs)
    binary_data = output.getvalue()

    thumbnail = _resize_image(image, THUMBNAIL_EDGE_PX)
    thumbnail_output = BytesIO()
    thumbnail.save(thumbnail_output, format=save_format, **save_kwargs)

    return {
        "data": binary_data,
        "thumbnail_data": thumbnail_output.getvalue(),
        "mime_type": mime_type,
        "width": resized_image.width,
        "height": resized_image.height,
    }


def create_defect_image(defect, uploaded_file):
    processed = _normalise_image(uploaded_file)

    image_asset = ImageAsset.objects.create(
        organization=defect.playground.organization if defect.playground else None,
        original_filename=uploaded_file.name or "mangelfoto",
        mime_type=processed["mime_type"],
        size_bytes=len(processed["data"]),
        width=processed["width"],
        height=processed["height"],
        sha256=ImageAsset.calculate_sha256(processed["data"]),
        data=processed["data"],
        thumbnail_data=processed["thumbnail_data"],
        public_visible=defect.public_visible,
    )

    return DefectImage.objects.create(
        defect=defect,
        image=image_asset,
        public_visible=defect.public_visible,
    )


def sync_defect_image_visibility(defect):
    DefectImage.objects.filter(defect=defect).update(public_visible=defect.public_visible)

    ImageAsset.objects.filter(defect_images__defect=defect).update(
        public_visible=defect.public_visible,
    )


def handle_defect_image_uploads(defect, files):
    uploaded_files = [
        uploaded_file for uploaded_file in files.getlist("images") if uploaded_file
    ]

    existing_count = defect.images.count()
    remaining_slots = max(0, MAX_DEFECT_IMAGES - existing_count)

    if len(uploaded_files) > remaining_slots:
        raise ValidationError(
            f"Pro Mangel sind höchstens {MAX_DEFECT_IMAGES} Fotos möglich."
        )

    for uploaded_file in uploaded_files:
        create_defect_image(defect, uploaded_file)


def delete_selected_defect_images(defect, post_data):
    image_ids_to_delete = post_data.getlist("delete_images")

    if not image_ids_to_delete:
        return

    defect_images = list(
        DefectImage.objects
        .select_related("image")
        .filter(defect=defect, id__in=image_ids_to_delete)
    )

    image_assets = [defect_image.image for defect_image in defect_images]

    for defect_image in defect_images:
        defect_image.delete()

    for image_asset in image_assets:
        if not image_asset.defect_images.exists():
            image_asset.delete()
