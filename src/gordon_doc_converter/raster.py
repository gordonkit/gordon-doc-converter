"""Engine-neutral, resource-bounded PDF page rasterization."""

from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Protocol, cast

from pypdf import PdfReader

from gordon_doc_converter.exceptions import InvalidInputError, OutputExistsError, PdfValidationError
from gordon_doc_converter.models import PageImageFormat
from gordon_doc_converter.validation import validate_pdf

_COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")

ImageFormat = PageImageFormat


@dataclass(frozen=True, slots=True)
class RasterOptions:
    """Limits and rendering options applied before any page is rendered."""

    dpi: int = 144
    image_format: ImageFormat = ImageFormat.PNG
    quality: int = 90
    pages: tuple[int, ...] | None = None
    background: str = "#ffffff"
    overwrite: bool = False
    max_pages: int = 200
    max_dimension_pixels: int = 20_000
    max_total_bytes: int = 512 * 1024 * 1024

    def __post_init__(self) -> None:
        if not 1 <= self.dpi <= 600:
            raise InvalidInputError("dpi must be between 1 and 600")
        if not 1 <= self.quality <= 100:
            raise InvalidInputError("quality must be between 1 and 100")
        if not _COLOR_PATTERN.fullmatch(self.background):
            raise InvalidInputError("background must use #RRGGBB notation")
        if self.max_pages < 1 or self.max_dimension_pixels < 1 or self.max_total_bytes < 1:
            raise InvalidInputError("raster resource limits must be greater than zero")
        if self.pages is not None:
            if not self.pages or any(page < 1 for page in self.pages):
                raise InvalidInputError("pages must contain positive one-based page numbers")
            if len(set(self.pages)) != len(self.pages):
                raise InvalidInputError("pages must not contain duplicates")
            if tuple(sorted(self.pages)) != self.pages:
                raise InvalidInputError("pages must be in ascending order")


@dataclass(frozen=True, slots=True)
class PageImageArtifact:
    """Metadata for one page image, ordered by its one-based PDF page number."""

    page_number: int
    path: Path
    width_pixels: int
    height_pixels: int
    size_bytes: int
    sha256: str
    image_format: ImageFormat

    def to_dict(self) -> dict[str, str | int]:
        """Return deterministic machine-readable artifact metadata."""
        return {
            "page_number": self.page_number,
            "path": str(self.path),
            "width_pixels": self.width_pixels,
            "height_pixels": self.height_pixels,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
            "image_format": self.image_format.value,
        }


class PageRenderer(Protocol):
    """Narrow backend contract for rendering a single validated PDF page."""

    def render_page(
        self,
        pdf_path: Path,
        page_number: int,
        output_path: Path,
        *,
        dpi: int,
        image_format: ImageFormat,
        quality: int,
        background: str,
    ) -> None:
        """Render one one-based page to the requested output path."""
        ...


class PdfiumPageRenderer:
    """Render PDF pages with the optional pypdfium2 and Pillow dependencies."""

    def render_page(
        self,
        pdf_path: Path,
        page_number: int,
        output_path: Path,
        *,
        dpi: int,
        image_format: ImageFormat,
        quality: int,
        background: str,
    ) -> None:
        """Render one page while keeping image dependencies optional at import time."""
        try:
            import pypdfium2 as pdfium
            from PIL import Image
        except ImportError as exc:
            raise InvalidInputError(
                "page-image output requires the 'images' optional dependency"
            ) from exc

        document = pdfium.PdfDocument(pdf_path)
        try:
            page = document[page_number - 1]
            try:
                # pypdfium2's runtime accepts fractional scale values, but its bundled
                # type information currently infers ``scale`` from the integer default.
                bitmap = cast("Any", page).render(scale=dpi / 72)
                image = bitmap.to_pil()
                if image.mode in {"RGBA", "LA"}:
                    canvas = Image.new("RGB", image.size, background)
                    alpha = image.getchannel("A")
                    canvas.paste(image.convert("RGB"), mask=alpha)
                    image = canvas
                elif image.mode != "RGB":
                    image = image.convert("RGB")
                if image_format is ImageFormat.PNG:
                    image.save(output_path, format="PNG", optimize=False)
                else:
                    image.save(
                        output_path,
                        format="JPEG",
                        quality=quality,
                        optimize=False,
                        progressive=False,
                    )
            finally:
                page.close()
        finally:
            document.close()


class PdfRasterizer:
    """Convert a validated PDF into deterministically named page images."""

    def __init__(self, renderer: PageRenderer) -> None:
        self._renderer = renderer

    def rasterize(
        self,
        pdf_path: Path,
        output_directory: Path,
        *,
        options: RasterOptions | None = None,
    ) -> tuple[PageImageArtifact, ...]:
        """Rasterize selected pages after enforcing configured resource limits."""
        options = options or RasterOptions()
        validation = validate_pdf(pdf_path)
        if not validation.valid or validation.page_count is None:
            raise PdfValidationError("PDF input is invalid")
        page_count = validation.page_count
        selected = options.pages or tuple(range(1, page_count + 1))
        if any(page > page_count for page in selected):
            raise InvalidInputError("requested page exceeds the PDF page count")
        if len(selected) > options.max_pages:
            raise InvalidInputError("requested pages exceed max_pages")

        reader = PdfReader(pdf_path, strict=False)
        dimensions: dict[int, tuple[int, int]] = {}
        for page_number in selected:
            box = reader.pages[page_number - 1].mediabox
            width = round(float(box.width) * options.dpi / 72)
            height = round(float(box.height) * options.dpi / 72)
            if width < 1 or height < 1:
                raise PdfValidationError("PDF page has invalid dimensions")
            if max(width, height) > options.max_dimension_pixels:
                raise InvalidInputError("raster dimensions exceed max_dimension_pixels")
            dimensions[page_number] = (width, height)

        extension = "jpg" if options.image_format is ImageFormat.JPEG else "png"
        width_digits = max(4, len(str(page_count)))
        destinations = {
            page: output_directory / f"{page:0{width_digits}d}.{extension}" for page in selected
        }
        if not options.overwrite and any(path.exists() for path in destinations.values()):
            raise OutputExistsError("one or more page-image outputs already exist")

        artifacts: list[PageImageArtifact] = []
        published: list[Path] = []
        with TemporaryDirectory(prefix="gordon-doc-raster-") as temporary:
            workspace = Path(temporary)
            total_size = 0
            staged: dict[int, Path] = {}
            for page_number in selected:
                staged_path = workspace / destinations[page_number].name
                self._renderer.render_page(
                    pdf_path,
                    page_number,
                    staged_path,
                    dpi=options.dpi,
                    image_format=options.image_format,
                    quality=options.quality,
                    background=options.background,
                )
                if not staged_path.is_file() or staged_path.stat().st_size == 0:
                    raise PdfValidationError("page renderer did not create a non-empty image")
                data = staged_path.read_bytes()
                expected_signature = b"\x89PNG\r\n\x1a\n" if extension == "png" else b"\xff\xd8\xff"
                if not data.startswith(expected_signature):
                    raise PdfValidationError("page renderer created an invalid image format")
                total_size += len(data)
                if total_size > options.max_total_bytes:
                    raise InvalidInputError("page images exceed max_total_bytes")
                staged[page_number] = staged_path

            output_directory.mkdir(parents=True, exist_ok=True)
            try:
                for page_number in selected:
                    destination = destinations[page_number]
                    if options.overwrite:
                        temporary_destination = destination.with_name(f".{destination.name}.tmp")
                        temporary_destination.unlink(missing_ok=True)
                        with (
                            staged[page_number].open("rb") as source,
                            temporary_destination.open("xb") as target,
                        ):
                            shutil.copyfileobj(source, target)
                        os.replace(temporary_destination, destination)
                    else:
                        with (
                            staged[page_number].open("rb") as source,
                            destination.open("xb") as target,
                        ):
                            shutil.copyfileobj(source, target)
                    published.append(destination)
                    data = destination.read_bytes()
                    width, height = dimensions[page_number]
                    artifacts.append(
                        PageImageArtifact(
                            page_number=page_number,
                            path=destination,
                            width_pixels=width,
                            height_pixels=height,
                            size_bytes=len(data),
                            sha256=sha256(data).hexdigest(),
                            image_format=options.image_format,
                        )
                    )
            except OSError:
                for path in published:
                    path.unlink(missing_ok=True)
                raise
        return tuple(artifacts)
