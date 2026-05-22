import base64
import binascii
import mimetypes
import re
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image as PillowImage

from .models import ImageAsset


DATA_URL_RE = re.compile(
    r"^data:(?P<mime>[-\w.+/]+);base64,(?P<data>.*)$",
    re.IGNORECASE | re.DOTALL,
)


MIME_BY_SIGNATURE = (
    (b"\xff\xd8\xff", "image/jpeg", ".jpg"),
    (b"\x89PNG\r\n\x1a\n", "image/png", ".png"),
    (b"GIF87a", "image/gif", ".gif"),
    (b"GIF89a", "image/gif", ".gif"),
    (b"RIFF", "image/webp", ".webp"),
)


@dataclass(frozen=True)
class DecodedImageData:
    data: bytes
    mime_type: str
    extension: str
    width: int | None = None
    height: int | None = None


def normalize_legacy_image_value(value):
    """Normalize common legacy image representations to bytes.

    Supported inputs include:
    - raw image bytes
    - PostgreSQL bytea as memoryview
    - encode(bytea, 'hex') strings
    - PostgreSQL textual bytea values like \xFFD8...
    - data URLs stored as bytes/text, for example data:image/jpeg;base64,...
    - plain base64 image payloads
    """

    if value is None:
        return b""

    if isinstance(value, memoryview):
        value = value.tobytes()

    if isinstance(value, bytearray):
        value = bytes(value)

    if isinstance(value, bytes):
        stripped = value.strip()

        # Legacy PostgreSQL bytea can contain a text data URL as bytes.
        if looks_like_text(stripped):
            return normalize_legacy_image_value(stripped.decode("utf-8", errors="replace"))

        return stripped

    if isinstance(value, Path):
        return normalize_legacy_image_value(value.read_bytes())

    if not isinstance(value, str):
        return bytes(value)

    text = value.strip()

    if not text:
        return b""

    # PostgreSQL bytea hex output can be \x...., while encode(bytea, 'hex')
    # returns the hex digits without prefix.
    if text.startswith("\\x") and is_hex_string(text[2:]):
        return normalize_legacy_image_value(binascii.unhexlify(text[2:]))

    if is_hex_string(text):
        return normalize_legacy_image_value(binascii.unhexlify(text))

    data_url_match = DATA_URL_RE.match(text)
    if data_url_match:
        return base64.b64decode(data_url_match.group("data"), validate=False)

    if looks_like_base64(text):
        try:
            return base64.b64decode(text, validate=False)
        except binascii.Error:
            pass

    return text.encode("utf-8")


def decode_legacy_image_value(value, fallback_mime_type="application/octet-stream"):
    normalized = normalize_legacy_image_value(value)

    if not normalized:
        raise ValueError("Leerer Bildwert.")

    mime_type, extension = detect_image_type(normalized, fallback_mime_type=fallback_mime_type)
    width, height = detect_image_dimensions(normalized)

    return DecodedImageData(
        data=normalized,
        mime_type=mime_type,
        extension=extension,
        width=width,
        height=height,
    )


def create_image_asset_from_legacy_value(
    value,
    organization,
    original_filename="legacy-image",
    public_visible=True,
    fallback_mime_type="application/octet-stream",
):
    decoded = decode_legacy_image_value(value, fallback_mime_type=fallback_mime_type)
    filename = ensure_filename_extension(original_filename, decoded.extension)

    return ImageAsset.objects.create(
        organization=organization,
        original_filename=filename,
        mime_type=decoded.mime_type,
        size_bytes=len(decoded.data),
        width=decoded.width,
        height=decoded.height,
        sha256=ImageAsset.calculate_sha256(decoded.data),
        data=decoded.data,
        public_visible=public_visible,
    )


def create_image_asset_from_upload(uploaded_file, organization, public_visible=True):
    binary_data = uploaded_file.read()
    decoded = decode_legacy_image_value(
        binary_data,
        fallback_mime_type=uploaded_file.content_type or "application/octet-stream",
    )

    return ImageAsset.objects.create(
        organization=organization,
        original_filename=ensure_filename_extension(uploaded_file.name, decoded.extension),
        mime_type=decoded.mime_type,
        size_bytes=len(decoded.data),
        width=decoded.width,
        height=decoded.height,
        sha256=ImageAsset.calculate_sha256(decoded.data),
        data=decoded.data,
        public_visible=public_visible,
    )


def is_hex_string(text):
    if len(text) < 2 or len(text) % 2 != 0:
        return False
    return bool(re.fullmatch(r"[0-9a-fA-F]+", text))


def looks_like_text(value):
    prefix = value[:80].lower()
    return (
        prefix.startswith(b"data:image/")
        or prefix.startswith(b"/9j/")
        or prefix.startswith(b"ivbor")
        or prefix.startswith(b"r0lgod")
    )


def looks_like_base64(text):
    compact = "".join(text.split())
    if len(compact) < 16:
        return False
    if len(compact) % 4 not in {0, 2, 3}:
        return False
    return bool(re.fullmatch(r"[A-Za-z0-9+/=_-]+", compact))


def detect_image_type(data, fallback_mime_type="application/octet-stream"):
    for signature, mime_type, extension in MIME_BY_SIGNATURE:
        if data.startswith(signature):
            if mime_type == "image/webp" and data[8:12] != b"WEBP":
                continue
            return mime_type, extension

    extension = mimetypes.guess_extension(fallback_mime_type) or ".bin"
    return fallback_mime_type, extension


def detect_image_dimensions(data):
    try:
        image = PillowImage.open(BytesIO(data))
        return image.size
    except Exception:
        return None, None


def ensure_filename_extension(filename, extension):
    path = Path(filename or "image")
    if path.suffix:
        return path.name
    return f"{path.name}{extension}"
