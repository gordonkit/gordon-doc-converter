from __future__ import annotations

from pathlib import Path

from pypdf import PdfWriter

from gordon_doc_converter.comparison import PageDifference, PdfComparisonService
from gordon_doc_converter.raster import ImageFormat, PdfRasterizer


class Renderer:
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
        del dpi, image_format, quality, background
        marker = b"same" if "same" in pdf_path.stem else pdf_path.stem.encode()
        output_path.write_bytes(b"\x89PNG\r\n\x1a\n" + marker + bytes([page_number]))


def make_pdf(path: Path, pages: int) -> None:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=72, height=72)
    with path.open("wb") as stream:
        writer.write(stream)


def test_comparison_reports_equal_rasters_and_size_delta(tmp_path: Path) -> None:
    left = tmp_path / "same-left.pdf"
    right = tmp_path / "same-right.pdf"
    make_pdf(left, 1)
    make_pdf(right, 1)

    report = PdfComparisonService(PdfRasterizer(Renderer())).compare(left, right, dpi=72)

    assert report.equal
    assert report.pages[0].status is PageDifference.EQUAL
    assert report.pages[0].difference_ratio == 0.0
    assert report.size_difference_bytes == right.stat().st_size - left.stat().st_size
    assert report.to_dict()["equal"] is True


def test_comparison_reports_changed_and_added_pages(tmp_path: Path) -> None:
    left = tmp_path / "left.pdf"
    right = tmp_path / "right.pdf"
    make_pdf(left, 1)
    make_pdf(right, 2)

    report = PdfComparisonService(PdfRasterizer(Renderer())).compare(left, right)

    assert not report.equal
    assert [page.status for page in report.pages] == [
        PageDifference.DIFFERENT,
        PageDifference.RIGHT_ONLY,
    ]
    assert report.left_page_count == 1
    assert report.right_page_count == 2
    assert report.left_fonts == ()
    assert report.right_fonts == ()
