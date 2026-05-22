# Generated manually to normalize legacy image bytea values that contain data URLs.

import base64
import binascii
import hashlib
import re
from io import BytesIO

from django.db import migrations


DATA_URL_RE = re.compile(
    rb"^data:(?P<mime>[-\w.+/]+);base64,(?P<data>.*)$",
    re.IGNORECASE | re.DOTALL,
)


SIGNATURES = (
    (b"\xff\xd8\xff", "image/jpeg", ".jpg"),
    (b"\x89PNG\r\n\x1a\n", "image/png", ".png"),
    (b"GIF87a", "image/gif", ".gif"),
    (b"GIF89a", "image/gif", ".gif"),
)


def normalize_existing_image_assets(apps, schema_editor):
    ImageAsset = apps.get_model("media_assets", "ImageAsset")

    for image in ImageAsset.objects.all().iterator():
        raw_data = bytes(image.data or b"")
        normalized = decode_legacy_value(raw_data)

        if not normalized or normalized == raw_data:
            continue

        mime_type, extension = detect_image_type(normalized, image.mime_type)
        width, height = detect_dimensions(normalized)

        image.data = normalized
        image.mime_type = mime_type
        image.size_bytes = len(normalized)
        image.sha256 = hashlib.sha256(normalized).hexdigest()

        if width and height:
            image.width = width
            image.height = height

        if extension and image.original_filename and "." not in image.original_filename.rsplit("/", 1)[-1]:
            image.original_filename = f"{image.original_filename}{extension}"

        image.save(update_fields=[
            "data",
            "mime_type",
            "size_bytes",
            "sha256",
            "width",
            "height",
            "original_filename",
        ])


def decode_legacy_value(raw_data):
    stripped = raw_data.strip()

    if not stripped:
        return b""

    data_url_match = DATA_URL_RE.match(stripped)
    if data_url_match:
        return base64.b64decode(data_url_match.group("data"), validate=False)

    # Defensive fallback for rows where a textual hex representation was stored
    # in the binary field instead of the original bytea value.
    try:
        text = stripped.decode("ascii")
    except UnicodeDecodeError:
        return stripped

    if text.startswith("\\x") and is_hex_string(text[2:]):
        return decode_legacy_value(binascii.unhexlify(text[2:]))

    if is_hex_string(text):
        return decode_legacy_value(binascii.unhexlify(text))

    return stripped


def is_hex_string(text):
    return len(text) >= 2 and len(text) % 2 == 0 and bool(re.fullmatch(r"[0-9a-fA-F]+", text))


def detect_image_type(data, fallback_mime_type):
    for signature, mime_type, extension in SIGNATURES:
        if data.startswith(signature):
            return mime_type, extension

    return fallback_mime_type or "application/octet-stream", ""


def detect_dimensions(data):
    try:
        from PIL import Image as PillowImage

        image = PillowImage.open(BytesIO(data))
        return image.size
    except Exception:
        return None, None


class Migration(migrations.Migration):

    dependencies = [
        ("media_assets", "0002_initial"),
    ]

    operations = [
        migrations.RunPython(normalize_existing_image_assets, migrations.RunPython.noop),
    ]
