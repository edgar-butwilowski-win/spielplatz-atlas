from io import BytesIO

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.decorators.http import require_POST
from PIL import Image, ImageOps

from accounts.permissions import user_may_inspect
from media_assets.models import ImageAsset
from playgrounds.models import PlayEquipment, Playground


def user_may_manage_photo(user, organization):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return user_may_inspect(user, organization)


def redirect_to_playground(playground):
    return redirect(
        reverse(
            "public:playground_detail",
            kwargs={
                "organization_slug": playground.organization.slug,
                "playground_slug": playground.slug,
            },
        )
    )


def image_asset_from_upload(uploaded_file, organization, public_visible=True):
    raw_data = uploaded_file.read()
    source = Image.open(BytesIO(raw_data))
    source = ImageOps.exif_transpose(source)
    if source.mode not in ("RGB", "RGBA"):
        source = source.convert("RGB")

    output = BytesIO()
    mime_type = "image/png" if source.mode == "RGBA" else "image/jpeg"
    image_format = "PNG" if source.mode == "RGBA" else "JPEG"
    save_kwargs = {"format": image_format}
    if image_format == "JPEG":
        save_kwargs.update({"quality": 88, "optimize": True})
    source.save(output, **save_kwargs)
    data = output.getvalue()

    thumbnail = source.copy()
    thumbnail.thumbnail((600, 600))
    thumb_output = BytesIO()
    thumbnail.save(thumb_output, **save_kwargs)

    return ImageAsset.objects.create(
        organization=organization,
        original_filename=uploaded_file.name,
        mime_type=mime_type,
        size_bytes=len(data),
        width=source.width,
        height=source.height,
        sha256=ImageAsset.calculate_sha256(data),
        data=data,
        thumbnail_data=thumb_output.getvalue(),
        public_visible=public_visible,
    )


def rotate_image_asset(image_asset):
    source = Image.open(BytesIO(image_asset.data))
    source = ImageOps.exif_transpose(source)
    rotated = source.rotate(-90, expand=True)
    if rotated.mode not in ("RGB", "RGBA"):
        rotated = rotated.convert("RGB")

    output = BytesIO()
    image_format = "PNG" if image_asset.mime_type == "image/png" or rotated.mode == "RGBA" else "JPEG"
    mime_type = "image/png" if image_format == "PNG" else "image/jpeg"
    save_kwargs = {"format": image_format}
    if image_format == "JPEG":
        save_kwargs.update({"quality": 88, "optimize": True})
    rotated.save(output, **save_kwargs)
    data = output.getvalue()

    thumbnail = rotated.copy()
    thumbnail.thumbnail((600, 600))
    thumb_output = BytesIO()
    thumbnail.save(thumb_output, **save_kwargs)

    image_asset.mime_type = mime_type
    image_asset.size_bytes = len(data)
    image_asset.width = rotated.width
    image_asset.height = rotated.height
    image_asset.sha256 = ImageAsset.calculate_sha256(data)
    image_asset.data = data
    image_asset.thumbnail_data = thumb_output.getvalue()
    image_asset.save(update_fields=["mime_type", "size_bytes", "width", "height", "sha256", "data", "thumbnail_data"])


@require_POST
def upload_playground_photo(request, organization_slug, playground_slug):
    playground = get_object_or_404(
        Playground.objects.select_related("organization"),
        organization__slug=organization_slug,
        slug=playground_slug,
    )
    if not user_may_manage_photo(request.user, playground.organization):
        raise PermissionDenied("Keine Berechtigung zum Bearbeiten von Fotos.")
    uploaded_file = request.FILES.get("photo")
    if not uploaded_file:
        messages.error(request, "Bitte wählen Sie ein Bild aus.")
        return redirect_to_playground(playground)
    playground.photo = image_asset_from_upload(uploaded_file, playground.organization, public_visible=True)
    playground.save(update_fields=["photo"])
    messages.success(request, "Das Spielplatzbild wurde aktualisiert.")
    return redirect_to_playground(playground)


@require_POST
def rotate_playground_photo(request, organization_slug, playground_slug):
    playground = get_object_or_404(
        Playground.objects.select_related("organization", "photo"),
        organization__slug=organization_slug,
        slug=playground_slug,
    )
    if not user_may_manage_photo(request.user, playground.organization):
        raise PermissionDenied("Keine Berechtigung zum Bearbeiten von Fotos.")
    if not playground.photo_id:
        messages.error(request, "Dieses Vorschaubild ist kein separates Spielplatzbild.")
        return redirect_to_playground(playground)
    rotate_image_asset(playground.photo)
    messages.success(request, "Das Spielplatzbild wurde gedreht.")
    return redirect_to_playground(playground)


@require_POST
def upload_equipment_photo(request, equipment_id):
    equipment = get_object_or_404(
        PlayEquipment.objects.select_related("playground", "playground__organization"),
        id=equipment_id,
    )
    if not user_may_manage_photo(request.user, equipment.playground.organization):
        raise PermissionDenied("Keine Berechtigung zum Bearbeiten von Fotos.")
    uploaded_file = request.FILES.get("photo")
    if not uploaded_file:
        messages.error(request, "Bitte wählen Sie ein Bild aus.")
        return redirect_to_playground(equipment.playground)
    equipment.photo = image_asset_from_upload(uploaded_file, equipment.playground.organization, public_visible=True)
    equipment.save(update_fields=["photo"])
    messages.success(request, "Das Spielgerätebild wurde aktualisiert.")
    return redirect_to_playground(equipment.playground)


@require_POST
def rotate_equipment_photo(request, equipment_id):
    equipment = get_object_or_404(
        PlayEquipment.objects.select_related("playground", "playground__organization", "photo"),
        id=equipment_id,
    )
    if not user_may_manage_photo(request.user, equipment.playground.organization):
        raise PermissionDenied("Keine Berechtigung zum Bearbeiten von Fotos.")
    if not equipment.photo_id:
        messages.error(request, "Für dieses Spielgerät ist noch kein Bild hinterlegt.")
        return redirect_to_playground(equipment.playground)
    rotate_image_asset(equipment.photo)
    messages.success(request, "Das Spielgerätebild wurde gedreht.")
    return redirect_to_playground(equipment.playground)
