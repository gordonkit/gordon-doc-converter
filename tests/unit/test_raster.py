from __future__ import annotations

from pathlib import Path

import pytest
from pypdf import PdfWriter

from gordon_doc_converter.exceptions import InvalidInputError, OutputExistsError
from gordon_doc_converter.raster import ImageFormat, PdfRasterizer, RasterOptions


class Renderer:
    def __init__(self, payload: bytes = b"\x89PNG\r\n\x1a\nimage") -> None:
        self.payload = payload
        self.calls: list[int] = []

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
        del pdf_path, dpi, image_format, quality, background
        self.calls.append(page_number)
        output_path.write_bytes(self.payload + bytes([page_number]))


def make_pdf(path: Path, pages: int = 3) -> None:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=72, height=144)
    with path.open("wb") as stream:
        writer.write(stream)


def test_rasterize_names_orders_and_describes_selected_pages(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source)
    renderer = Renderer()

    artifacts = PdfRasterizer(renderer).rasterize(
        source,
        tmp_path / "images",
        options=RasterOptions(dpi=72, pages=(1, 3)),
    )

    assert renderer.calls == [1, 3]
    assert [artifact.path.name for artifact in artifacts] == ["0001.png", "0003.png"]
    assert [(item.width_pixels, item.height_pixels) for item in artifacts] == [(72, 144)] * 2
    assert all(len(item.sha256) == 64 for item in artifacts)


def test_rasterize_supports_jpeg_and_background(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, 1)
    renderer = Renderer(b"\xff\xd8\xffimage")

    artifacts = PdfRasterizer(renderer).rasterize(
        source,
        tmp_path / "images",
        options=RasterOptions(image_format=ImageFormat.JPEG, background="#000000"),
    )

    assert artifacts[0].path.name == "0001.jpg"


def test_raster_limits_are_checked_before_render(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, 2)
    renderer = Renderer()

    with pytest.raises(InvalidInputError, match="max_pages"):
        PdfRasterizer(renderer).rasterize(
            source, tmp_path / "images", options=RasterOptions(max_pages=1)
        )
    assert renderer.calls == []


def test_raster_rejects_out_of_range_and_existing_output(tmp_path: Path) -> None:
    source = tmp_path / "source.pdf"
    make_pdf(source, 1)
    renderer = Renderer()
    rasterizer = PdfRasterizer(renderer)
    with pytest.raises(InvalidInputError, match="page count"):
        rasterizer.rasterize(source, tmp_path / "a", options=RasterOptions(pages=(2,)))

    directory = tmp_path / "b"
    directory.mkdir()
    (directory / "0001.png").write_bytes(b"existing")
    with pytest.raises(OutputExistsError):
        rasterizer.rasterize(source, directory)


def test_raster_options_validate_ranges() -> None:
    with pytest.raises(InvalidInputError):
        RasterOptions(dpi=0)
    with pytest.raises(InvalidInputError):
        RasterOptions(background="white")
    with pytest.raises(InvalidInputError):
        RasterOptions(pages=(2, 1))
