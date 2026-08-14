"""Generate deterministic, synthetic Traditional Chinese DOCX fixtures."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ZIP_TIMESTAMP = (2020, 1, 1, 0, 0, 0)
A4_WIDTH = 11906
A4_HEIGHT = 16838


@dataclass(frozen=True)
class Fixture:
    """A generated DOCX fixture and the feature it exercises."""

    filename: str
    feature: str
    body: str
    section: str
    relationships: tuple[tuple[str, str, str], ...] = ()
    extra_parts: tuple[tuple[str, bytes], ...] = ()


def _paragraph(text: str, *, style: str | None = None, page_break: bool = False) -> str:
    properties = f'<w:pPr><w:pStyle w:val="{style}"/></w:pPr>' if style else ""
    break_xml = '<w:r><w:br w:type="page"/></w:r>' if page_break else ""
    return (
        f'<w:p>{properties}<w:r><w:t xml:space="preserve">{escape(text)}</w:t></w:r>'
        f"{break_xml}</w:p>"
    )


def _section(*, landscape: bool = False, header: bool = False, footer: bool = False) -> str:
    width, height = (A4_HEIGHT, A4_WIDTH) if landscape else (A4_WIDTH, A4_HEIGHT)
    orientation = ' w:orient="landscape"' if landscape else ""
    references = ""
    if header:
        references += '<w:headerReference w:type="default" r:id="rIdHeader"/>'
    if footer:
        references += '<w:footerReference w:type="default" r:id="rIdFooter"/>'
    return (
        f'<w:sectPr>{references}<w:pgSz w:w="{width}" w:h="{height}"{orientation}/>'
        '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" '
        'w:header="720" w:footer="720" w:gutter="0"/></w:sectPr>'
    )


def _document(body: str, section: str) -> bytes:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
        'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
        'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture" '
        'xmlns:v="urn:schemas-microsoft-com:vml" '
        'xmlns:o="urn:schemas-microsoft-com:office:office">'
        f"<w:body>{body}{section}</w:body></w:document>"
    ).encode()


def _styles() -> bytes:
    return (
        b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        b'<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        b'<w:style w:type="paragraph" w:default="1" w:styleId="Normal">'
        b'<w:name w:val="Normal"/><w:rPr><w:lang w:eastAsia="zh-TW"/></w:rPr></w:style>'
        b'<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/>'
        b'<w:basedOn w:val="Normal"/><w:rPr><w:b/><w:sz w:val="36"/></w:rPr></w:style>'
        b'<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/>'
        b'<w:basedOn w:val="Normal"/><w:outlineLvl w:val="0"/>'
        b'<w:rPr><w:b/><w:sz w:val="28"/></w:rPr></w:style>'
        b'<w:style w:type="paragraph" w:styleId="TOC1"><w:name w:val="toc 1"/>'
        b'<w:basedOn w:val="Normal"/></w:style></w:styles>'
    )


def _settings() -> bytes:
    return (
        b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        b'<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        b'<w:updateFields w:val="true"/></w:settings>'
    )


def _relationships(items: tuple[tuple[str, str, str], ...]) -> bytes:
    base = (
        "rIdStyles",
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles",
        "styles.xml",
    )
    settings = (
        "rIdSettings",
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings",
        "settings.xml",
    )
    relationships = (base, settings, *items)
    entries = "".join(
        f'<Relationship Id="{identifier}" Type="{kind}" Target="{target}"/>'
        for identifier, kind, target in relationships
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f"{entries}</Relationships>"
    ).encode()


def _content_types(extra_parts: tuple[tuple[str, bytes], ...]) -> bytes:
    names = {name for name, _ in extra_parts}
    overrides = ""
    if "word/header1.xml" in names:
        overrides += (
            '<Override PartName="/word/header1.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>'
        )
    if "word/footer1.xml" in names:
        overrides += (
            '<Override PartName="/word/footer1.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>'
        )
    png = (
        '<Default Extension="png" ContentType="image/png"/>'
        if any(name.endswith(".png") for name in names)
        else ""
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" '
        'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        f"{png}"
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        '<Override PartName="/word/styles.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
        '<Override PartName="/word/settings.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>'
        f"{overrides}</Types>"
    ).encode()


def _root_relationships() -> bytes:
    return (
        b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        b'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        b'<Relationship Id="rId1" '
        b'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/'
        b'officeDocument" '
        b'Target="word/document.xml"/></Relationships>'
    )


def _png() -> bytes:
    """Return a generated 64x32 RGB image with a blue and red split."""
    width, height = 64, 32
    rows = []
    for _ in range(height):
        pixels = b"".join(
            (b"\x20\x70\xd0" if column < width // 2 else b"\xd0\x50\x40") for column in range(width)
        )
        rows.append(b"\x00" + pixels)

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(b"".join(rows), 9))
        + chunk(b"IEND", b"")
    )


def _table(rows: int) -> str:
    table_rows = [
        "<w:tr><w:tc><w:p><w:r><w:t>項次</w:t></w:r></w:p></w:tc>"
        "<w:tc><w:p><w:r><w:t>合成測試內容</w:t></w:r></w:p></w:tc></w:tr>"
    ]
    table_rows.extend(
        f"<w:tr><w:tc><w:p><w:r><w:t>{number:03d}</w:t></w:r></w:p></w:tc>"
        f"<w:tc><w:p><w:r><w:t>第 {number} 列：臺灣文件轉換排版測試</w:t></w:r></w:p></w:tc></w:tr>"
        for number in range(1, rows + 1)
    )
    return (
        '<w:tbl><w:tblPr><w:tblW w:w="0" w:type="auto"/></w:tblPr>'
        + "".join(table_rows)
        + "</w:tbl>"
    )


def _field(instruction: str, result: str) -> str:
    return (
        '<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
        f'<w:r><w:instrText xml:space="preserve"> {instruction} </w:instrText></w:r>'
        '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
        f"<w:r><w:t>{escape(result)}</w:t></w:r>"
        '<w:r><w:fldChar w:fldCharType="end"/></w:r>'
    )


def _fixtures() -> tuple[Fixture, ...]:
    heading = _paragraph("GordonKit 繁體中文文件測試", style="Title")
    normal = _paragraph("這是自行產生的公開測試內容，不含客戶資料或個人資料。")
    mixed_break = f"<w:p><w:pPr>{_section()}</w:pPr><w:r><w:t>第一節：直式</w:t></w:r></w:p>"
    toc = (
        '<w:p><w:r><w:fldChar w:fldCharType="begin"/></w:r>'
        '<w:r><w:instrText xml:space="preserve"> TOC \\o "1-3" \\h \\z \\u </w:instrText></w:r>'
        '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
        "<w:r><w:t>目錄（開啟文件後更新欄位）</w:t></w:r>"
        '<w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>'
    )
    header = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:hdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:p><w:r><w:t>頁首：GordonKit 合成文件</w:t></w:r></w:p></w:hdr>"
    ).encode()
    footer = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:ftr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:p><w:r><w:t>頁尾 — 第 </w:t></w:r>{_field('PAGE', '1')}"
        "<w:r><w:t> 頁</w:t></w:r></w:p></w:ftr>"
    ).encode()
    textbox = (
        '<w:p><w:r><w:pict><v:shape id="TextBox1" '
        'style="width:240pt;height:72pt" type="#_x0000_t202">'
        '<v:textbox inset="6pt,6pt,6pt,6pt"><w:txbxContent>'
        "<w:p><w:r><w:t>文字方塊：臺北、臺中、高雄</w:t></w:r></w:p>"
        "</w:txbxContent></v:textbox></v:shape></w:pict></w:r></w:p>"
    )
    floating_image = (
        '<w:p><w:r><w:drawing><wp:anchor distT="0" distB="0" distL="114300" '
        'distR="114300" simplePos="0" relativeHeight="251658240" behindDoc="0" '
        'locked="0" layoutInCell="1" allowOverlap="1">'
        '<wp:simplePos x="0" y="0"/><wp:positionH relativeFrom="column">'
        "<wp:posOffset>914400</wp:posOffset>"
        '</wp:positionH><wp:positionV relativeFrom="paragraph"><wp:posOffset>0</wp:posOffset>'
        '</wp:positionV><wp:extent cx="1828800" cy="914400"/><wp:wrapSquare wrapText="bothSides"/>'
        '<wp:docPr id="1" name="Generated color sample" descr="自行產生的藍紅色測試圖片"/>'
        '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
        '<pic:pic><pic:nvPicPr><pic:cNvPr id="0" name="generated.png"/>'
        '<pic:cNvPicPr/></pic:nvPicPr><pic:blipFill><a:blip r:embed="rIdImage"/>'
        "<a:stretch><a:fillRect/></a:stretch></pic:blipFill>"
        '<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="1828800" cy="914400"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic>'
        "</a:graphicData></a:graphic></wp:anchor></w:drawing></w:r></w:p>"
    )
    image_relationship = (
        "rIdImage",
        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image",
        "media/generated.png",
    )
    return (
        Fixture("a4-portrait.docx", "A4 portrait", heading + normal, _section()),
        Fixture("a4-landscape.docx", "A4 landscape", heading + normal, _section(landscape=True)),
        Fixture(
            "mixed-sections.docx",
            "mixed portrait and landscape sections",
            heading + mixed_break + _paragraph("第二節：橫式"),
            _section(landscape=True),
        ),
        Fixture(
            "chinese-toc.docx",
            "Chinese table of contents field",
            heading + toc + _paragraph("第一章　計畫概述", style="Heading1") + normal,
            _section(),
        ),
        Fixture(
            "multi-page-table.docx",
            "multi-page Traditional Chinese table",
            heading + _table(120),
            _section(),
        ),
        Fixture(
            "headers-footers.docx",
            "Traditional Chinese header and footer with page field",
            heading + normal,
            _section(header=True, footer=True),
            relationships=(
                (
                    "rIdHeader",
                    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/header",
                    "header1.xml",
                ),
                (
                    "rIdFooter",
                    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer",
                    "footer1.xml",
                ),
            ),
            extra_parts=(("word/header1.xml", header), ("word/footer1.xml", footer)),
        ),
        Fixture(
            "text-box.docx",
            "VML text box with Traditional Chinese",
            heading + textbox + normal,
            _section(),
        ),
        Fixture(
            "floating-image.docx",
            "anchored generated PNG",
            heading + floating_image + normal,
            _section(),
            relationships=(image_relationship,),
            extra_parts=(("word/media/generated.png", _png()),),
        ),
        Fixture(
            "fields.docx",
            "PAGE, NUMPAGES, and DATE fields",
            heading
            + f"<w:p><w:r><w:t>頁碼：</w:t></w:r>{_field('PAGE', '1')}<w:r><w:t> / </w:t></w:r>"
            + f"{_field('NUMPAGES', '1')}<w:r><w:t>；日期：</w:t></w:r>"
            + f"{_field(r'DATE \\@ yyyy-MM-dd', '2020-01-01')}</w:p>",
            _section(),
        ),
        Fixture(
            "special-symbols.docx",
            "CJK and special-symbol coverage",
            heading
            + _paragraph("繁體中文：臺灣、龍巖、文件；全形標點：「測試」、甲—乙……")
            + _paragraph("符號：© ® ™ § ¶ № ℃ ± × ÷ ≤ ≥ ≠ ∞ → ← ↑ ↓ ✓ ★ ○ ●")
            + _paragraph("注音：ㄅㄆㄇㄈ；中日韓：中文 日本語 한글；補充字元：𠀀"),
            _section(),
        ),
    )


def _write_zip(path: Path, fixture: Fixture) -> None:
    parts = {
        "[Content_Types].xml": _content_types(fixture.extra_parts),
        "_rels/.rels": _root_relationships(),
        "word/_rels/document.xml.rels": _relationships(fixture.relationships),
        "word/document.xml": _document(fixture.body, fixture.section),
        "word/settings.xml": _settings(),
        "word/styles.xml": _styles(),
        **dict(fixture.extra_parts),
    }
    with ZipFile(path, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(parts.items()):
            info = ZipInfo(name, ZIP_TIMESTAMP)
            info.create_system = 3
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)


def generate_fixtures(destination: Path, *, check: bool = False) -> dict[str, object]:
    """Generate fixtures, or verify that checked-in copies are reproducible."""
    destination.mkdir(parents=True, exist_ok=True)
    generated: list[dict[str, str]] = []
    mismatches: list[str] = []
    for fixture in _fixtures():
        target = destination / fixture.filename
        candidate = destination / f".{fixture.filename}.generated"
        output = candidate if check else target
        _write_zip(output, fixture)
        data = output.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if check:
            if not target.exists() or target.read_bytes() != data:
                mismatches.append(fixture.filename)
            candidate.unlink()
        generated.append({"file": fixture.filename, "feature": fixture.feature, "sha256": digest})
    manifest: dict[str, object] = {
        "format": "gordon-doc-converter-cjk-fixtures-v1",
        "license": "CC0-1.0",
        "provenance": "Deterministically generated synthetic content; no customer data.",
        "fixtures": generated,
    }
    manifest_path = destination / "manifest.json"
    manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
    if check:
        if not manifest_path.exists() or manifest_path.read_bytes() != manifest_bytes:
            mismatches.append("manifest.json")
        if mismatches:
            raise RuntimeError("Generated fixtures differ: " + ", ".join(mismatches))
    else:
        manifest_path.write_bytes(manifest_bytes)
    return manifest


def main() -> int:
    """Run the fixture generator from the command line."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "destination",
        nargs="?",
        type=Path,
        default=Path("tests/fixtures/docx/cjk"),
    )
    parser.add_argument("--check", action="store_true", help="verify committed fixtures")
    arguments = parser.parse_args()
    generate_fixtures(arguments.destination, check=arguments.check)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
