"""Bounded `data:` URI image decoding shared by the markup content readers."""

from __future__ import annotations

from base64 import b64decode
from binascii import Error as BinasciiError
from enum import StrEnum
from urllib.parse import unquote_to_bytes

from gordon_doc_converter.content.models import ContentAsset

MAX_EMBEDDED_ASSET_BYTES = 32 * 1024 * 1024
IMAGE_EXTENSIONS = {
    "image/gif": ".gif",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/svg+xml": ".svg",
    "image/tiff": ".tiff",
    "image/webp": ".webp",
}


class DataUriReason(StrEnum):
    """Why one `data:` URI produced no embedded asset.

    Each reader maps these to its own source-prefixed warning code, so the
    shared decoder stays free of format-specific vocabulary.
    """

    NOT_A_DATA_URI = "not-a-data-uri"
    DECODE_FAILED = "decode-failed"
    LIMIT_EXCEEDED = "limit-exceeded"


def decode_data_uri_image(
    source: str,
    *,
    index: int,
    consumed_bytes: int,
    limit: int = MAX_EMBEDDED_ASSET_BYTES,
) -> tuple[ContentAsset | None, DataUriReason | None]:
    """Decode one inline `data:` image into an asset within the byte budget.

    `index` numbers the asset within its document and `consumed_bytes` is the
    total already extracted, so a document cannot embed unbounded binary data.
    """
    if not source.casefold().startswith("data:"):
        return None, DataUriReason.NOT_A_DATA_URI
    header, _, payload = source[len("data:") :].partition(",")
    parameters = header.split(";")
    media_type = parameters[0].strip().casefold() or "text/plain"
    if not media_type.startswith("image/"):
        return None, DataUriReason.DECODE_FAILED
    try:
        data = (
            b64decode(payload, validate=True)
            if "base64" in {item.strip().casefold() for item in parameters[1:]}
            else unquote_to_bytes(payload)
        )
    except (BinasciiError, ValueError):
        return None, DataUriReason.DECODE_FAILED
    if not data or consumed_bytes + len(data) > limit:
        return None, DataUriReason.LIMIT_EXCEEDED
    suffix = IMAGE_EXTENSIONS.get(media_type, ".bin")
    filename = f"image-{index:04d}{suffix}"
    return ContentAsset(filename, filename, media_type, data), None
