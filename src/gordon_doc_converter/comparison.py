"""Machine-readable PDF comparison built on the shared rasterizer."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Protocol

from pypdf import PdfReader

from gordon_doc_converter.exceptions import InvalidInputError, PdfValidationError
from gordon_doc_converter.models_types import JsonValue
from gordon_doc_converter.raster import ImageFormat, PdfRasterizer, RasterOptions
from gordon_doc_converter.validation import validate_pdf


class PageDifference(StrEnum):
    """Stable visual comparison outcome for one page position."""

    EQUAL = "equal"
    DIFFERENT = "different"
    LEFT_ONLY = "left-only"
    RIGHT_ONLY = "right-only"


@dataclass(frozen=True, slots=True)
class FontDiagnostic:
    """One normalized PDF font resource observation."""

    name: str
    embedded: bool

    def to_dict(self) -> dict[str, JsonValue]:
        """Serialize the diagnostic for a machine-readable report."""
        return {"name": self.name, "embedded": self.embedded}


@dataclass(frozen=True, slots=True)
class PageComparison:
    """Visual comparison facts for one one-based page position."""

    page_number: int
    status: PageDifference
    difference_ratio: float | None = None
    diff_path: Path | None = None

    def to_dict(self) -> dict[str, JsonValue]:
        """Serialize this page result using stable primitives."""
        return {
            "page_number": self.page_number,
            "status": self.status.value,
            "difference_ratio": self.difference_ratio,
            "diff_path": None if self.diff_path is None else str(self.diff_path),
        }


@dataclass(frozen=True, slots=True)
class PdfComparisonReport:
    """Aggregate structural, raster, size, and font comparison facts."""

    equal: bool
    left_page_count: int
    right_page_count: int
    left_size_bytes: int
    right_size_bytes: int
    size_difference_bytes: int
    pages: tuple[PageComparison, ...]
    left_fonts: tuple[FontDiagnostic, ...]
    right_fonts: tuple[FontDiagnostic, ...]

    def to_dict(self) -> dict[str, JsonValue]:
        """Return a deterministic JSON-compatible comparison report."""
        return {
            "equal": self.equal,
            "left_page_count": self.left_page_count,
            "right_page_count": self.right_page_count,
            "left_size_bytes": self.left_size_bytes,
            "right_size_bytes": self.right_size_bytes,
            "size_difference_bytes": self.size_difference_bytes,
            "pages": [page.to_dict() for page in self.pages],
            "left_fonts": [font.to_dict() for font in self.left_fonts],
            "right_fonts": [font.to_dict() for font in self.right_fonts],
        }


class ImageDiffer(Protocol):
    """Narrow backend contract for pixel-aware image comparison."""

    def compare(self, left: Path, right: Path, diff_output: Path | None) -> float:
        """Return a normalized 0..1 difference ratio and optionally write a diff image."""
        ...


class ExactImageDiffer:
    """Dependency-free exact-image differ used when pixel tooling is unavailable."""

    def compare(self, left: Path, right: Path, diff_output: Path | None) -> float:
        """Return zero for byte-identical images and one otherwise."""
        del diff_output
        return 0.0 if left.read_bytes() == right.read_bytes() else 1.0


class PillowImageDiffer:
    """Compare decoded pixels and optionally publish a deterministic PNG diff."""

    def compare(self, left: Path, right: Path, diff_output: Path | None) -> float:
        """Return the normalized per-channel absolute pixel difference."""
        try:
            from PIL import Image, ImageChops
        except ImportError as exc:
            raise InvalidInputError(
                "visual comparison requires the 'images' optional dependency"
            ) from exc

        with Image.open(left) as left_source, Image.open(right) as right_source:
            left_image = left_source.convert("RGB")
            right_image = right_source.convert("RGB")
            if left_image.size != right_image.size:
                ratio = 1.0
                difference = Image.new(
                    "RGB",
                    (
                        max(left_image.width, right_image.width),
                        max(left_image.height, right_image.height),
                    ),
                    "#ff0000",
                )
            else:
                difference = ImageChops.difference(left_image, right_image)
                histogram = difference.histogram()
                absolute_difference = sum(
                    value * count for value, count in enumerate(histogram[:256])
                )
                absolute_difference += sum(
                    value * count for value, count in enumerate(histogram[256:512])
                )
                absolute_difference += sum(
                    value * count for value, count in enumerate(histogram[512:768])
                )
                maximum = left_image.width * left_image.height * 3 * 255
                ratio = absolute_difference / maximum
            if diff_output is not None and ratio > 0:
                diff_output.parent.mkdir(parents=True, exist_ok=True)
                difference.save(diff_output, format="PNG", optimize=False)
            return ratio


def _font_diagnostics(path: Path) -> tuple[FontDiagnostic, ...]:
    observations: set[tuple[str, bool]] = set()
    reader = PdfReader(path, strict=False)
    for page in reader.pages:
        resources = page.get("/Resources")
        if resources is None:
            continue
        resources = resources.get_object()
        fonts = resources.get("/Font")
        if fonts is None:
            continue
        fonts = fonts.get_object()
        for font_reference in fonts.values():
            font = font_reference.get_object()
            base_name = str(font.get("/BaseFont", "unknown")).lstrip("/")
            descriptor = font.get("/FontDescriptor")
            embedded = False
            if descriptor is not None:
                descriptor = descriptor.get_object()
                embedded = any(
                    key in descriptor for key in ("/FontFile", "/FontFile2", "/FontFile3")
                )
            observations.add((base_name, embedded))
    return tuple(FontDiagnostic(name, embedded) for name, embedded in sorted(observations))


class PdfComparisonService:
    """Compare validated PDFs using page rasters and an injected image differ."""

    def __init__(self, rasterizer: PdfRasterizer, differ: ImageDiffer | None = None) -> None:
        self._rasterizer = rasterizer
        self._differ = differ or ExactImageDiffer()

    def compare(
        self,
        left_path: Path,
        right_path: Path,
        *,
        dpi: int = 144,
        diff_directory: Path | None = None,
        max_pages: int = 200,
    ) -> PdfComparisonReport:
        """Compare page count, size, fonts, and rasterized page appearance."""
        if left_path.resolve() == right_path.resolve():
            raise InvalidInputError("comparison inputs must be different paths")
        left_validation = validate_pdf(left_path)
        right_validation = validate_pdf(right_path)
        if not left_validation.valid or left_validation.page_count is None:
            raise PdfValidationError("left PDF input is invalid")
        if not right_validation.valid or right_validation.page_count is None:
            raise PdfValidationError("right PDF input is invalid")
        largest_page_count = max(left_validation.page_count, right_validation.page_count)
        if largest_page_count > max_pages:
            raise InvalidInputError("PDF page count exceeds max_pages")

        with TemporaryDirectory(prefix="gordon-doc-compare-") as temporary:
            workspace = Path(temporary)
            options = RasterOptions(dpi=dpi, image_format=ImageFormat.PNG, max_pages=max_pages)
            left_images = self._rasterizer.rasterize(left_path, workspace / "left", options=options)
            right_images = self._rasterizer.rasterize(
                right_path, workspace / "right", options=options
            )
            pages: list[PageComparison] = []
            if diff_directory is not None:
                diff_directory.mkdir(parents=True, exist_ok=True)
            common_count = min(len(left_images), len(right_images))
            for index in range(common_count):
                page_number = index + 1
                diff_path = (
                    None
                    if diff_directory is None
                    else diff_directory / f"diff-page-{page_number:04d}.png"
                )
                ratio = self._differ.compare(
                    left_images[index].path, right_images[index].path, diff_path
                )
                if not 0.0 <= ratio <= 1.0:
                    raise InvalidInputError("image differ returned a ratio outside 0..1")
                if diff_path is not None and not diff_path.is_file():
                    diff_path = None
                pages.append(
                    PageComparison(
                        page_number=page_number,
                        status=(PageDifference.EQUAL if ratio == 0.0 else PageDifference.DIFFERENT),
                        difference_ratio=ratio,
                        diff_path=diff_path,
                    )
                )
            for page_number in range(common_count + 1, largest_page_count + 1):
                pages.append(
                    PageComparison(
                        page_number=page_number,
                        status=(
                            PageDifference.LEFT_ONLY
                            if page_number <= len(left_images)
                            else PageDifference.RIGHT_ONLY
                        ),
                    )
                )

        left_size = left_validation.file_size
        right_size = right_validation.file_size
        return PdfComparisonReport(
            equal=all(page.status is PageDifference.EQUAL for page in pages),
            left_page_count=left_validation.page_count,
            right_page_count=right_validation.page_count,
            left_size_bytes=left_size,
            right_size_bytes=right_size,
            size_difference_bytes=right_size - left_size,
            pages=tuple(pages),
            left_fonts=_font_diagnostics(left_path),
            right_fonts=_font_diagnostics(right_path),
        )
