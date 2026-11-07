"""Pandoc adapter that renders HTML and Markdown sources to DOCX."""

from __future__ import annotations

import re
import shutil
import tempfile
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from gordon_doc_converter.exceptions import (
    ConversionTimeoutError,
    EngineFailedError,
    EngineUnavailableError,
)
from gordon_doc_converter.models import ConversionOptions, PageOrientation, SourceFormat
from gordon_doc_converter.process import ProcessStartError, ProcessTimeoutError, run_process

_W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
_R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_REL_BASE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_HEADER_REL_ID = "rIdGordonHeader"
_FOOTER_REL_ID = "rIdGordonFooter"
_HEADER_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"
_FOOTER_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"
_PAGE_PLACEHOLDER = re.compile(r"(\{pages?\})")
_RUNNING_TEXT_HALF_POINTS = "18"
_RUNNING_TEXT_COLOR = "6B7280"
_NS = {"w": _W}
ET.register_namespace("w", _W)
ET.register_namespace("r", _R)
_A4_TWIPS = (11906, 16838)
_MARGIN_TWIPS = 1134
# Half-point units, matching the 10.5pt body size of the HTML print stylesheet.
_BODY_HALF_POINTS = "21"
_LATIN_FONT = "Segoe UI"
_EAST_ASIAN_FONT = "Microsoft JhengHei"
_THEME_FONT_ATTRIBUTES = ("asciiTheme", "hAnsiTheme", "eastAsiaTheme", "cstheme")
# GFM is the dialect our Markdown reader accepts, so Pandoc must read the same one.
_MARKDOWN_DIALECT = "gfm"
_MONOSPACE_FONT = "Consolas"
_CODE_HALF_POINTS = "20"
_TABLE_BORDER_COLOR = "BFC5CD"
_TABLE_HEADER_FILL = "F1F3F5"
_CODE_BLOCK_FILL = "F3F4F6"
_PAGE_BREAK_STYLE = "GordonPageBreak"
_TITLE_STYLES = frozenset({"Title", "Subtitle"})
# Pandoc prints these from <meta> tags; in HTML they are document properties, not content.
_HTML_METADATA_STYLES = frozenset({"Author", "Date"})
# Pandoc drops CSS, so this filter turns "break before page" requests into marker
# paragraphs that _apply_document_fixes later folds into pageBreakBefore.
_PAGE_BREAK_FILTER = r"""
local marker = pandoc.RawBlock('openxml',
  '<w:p><w:pPr><w:pStyle w:val="@@MARKER@@"/></w:pPr></w:p>')

local function wants_page_break(element)
  local style = (element.attributes['style'] or ''):lower()
  return style:find('break%-before%s*:%s*page') ~= nil
    or style:find('break%-before%s*:%s*always') ~= nil
    or style:find('page%-break%-before%s*:%s*always') ~= nil
end

local function escape(text)
  return (text:gsub('&', '&amp;'):gsub('<', '&lt;'))
end

-- <div class="toc" data-depth="3" data-title="Contents"></div> becomes a TOC field.
local function toc_block(element)
  local depth = tonumber(element.attributes['depth']) or 3
  local title = element.attributes['title'] or element.attributes['data-title']
  if title == nil then title = 'Table of Contents' end
  local xml = ''
  if title ~= '' then
    xml = '<w:p><w:pPr><w:pStyle w:val="TOCHeading"/></w:pPr><w:r><w:t>'
      .. escape(title) .. '</w:t></w:r></w:p>'
  end
  xml = xml .. '<w:p><w:r><w:fldChar w:fldCharType="begin" w:dirty="true"/>'
    .. '<w:instrText xml:space="preserve">TOC \\o "1-' .. depth .. '" \\h \\z \\u</w:instrText>'
    .. '<w:fldChar w:fldCharType="separate"/>'
    .. '<w:t>Update this field to build the table of contents.</w:t>'
    .. '<w:fldChar w:fldCharType="end"/></w:r></w:p>'
  return pandoc.RawBlock('openxml', xml)
end

function Header(element)
  if wants_page_break(element) then return {marker, element} end
end

function Div(element)
  if element.classes:includes('toc') then return toc_block(element) end
  if wants_page_break(element) then return {marker, element} end
end
""".replace("@@MARKER@@", _PAGE_BREAK_STYLE)


class _RunningText(HTMLParser):
    """Collect the ``gordon-header`` and ``gordon-footer`` meta tags of an HTML source."""

    def __init__(self) -> None:
        super().__init__()
        self.header: str | None = None
        self.footer: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "meta":
            return
        values = dict(attrs)
        content = values.get("content")
        if content is None or not content.strip():
            return
        if values.get("name") == "gordon-header":
            self.header = content
        elif values.get("name") == "gordon-footer":
            self.footer = content


def _read_running_text(source_path: Path) -> tuple[str | None, str | None]:
    parser = _RunningText()
    parser.feed(source_path.read_text(encoding="utf-8", errors="replace"))
    return parser.header, parser.footer


def _field_runs(parent: ET.Element, instruction: str) -> None:
    """Append a complex field (PAGE or NUMPAGES) whose cached result is 1."""
    for kind in ("begin", None, "separate", "result", "end"):
        run = ET.SubElement(parent, f"{{{_W}}}r")
        _running_run_properties(run)
        if kind == "result":
            ET.SubElement(run, f"{{{_W}}}t").text = "1"
        elif kind is None:
            ET.SubElement(run, f"{{{_W}}}instrText").set(
                "{http://www.w3.org/XML/1998/namespace}space", "preserve"
            )
            run[-1].text = f" {instruction} "
        else:
            ET.SubElement(run, f"{{{_W}}}fldChar").set(f"{{{_W}}}fldCharType", kind)


def _running_run_properties(run: ET.Element) -> None:
    properties = ET.SubElement(run, f"{{{_W}}}rPr")
    ET.SubElement(properties, f"{{{_W}}}color").set(f"{{{_W}}}val", _RUNNING_TEXT_COLOR)
    ET.SubElement(properties, f"{{{_W}}}sz").set(f"{{{_W}}}val", _RUNNING_TEXT_HALF_POINTS)


def _running_part(tag: str, text: str, alignment: str) -> bytes:
    """Build a header or footer part; ``{page}`` and ``{pages}`` become live fields."""
    root = ET.Element(f"{{{_W}}}{tag}")
    paragraph = ET.SubElement(root, f"{{{_W}}}p")
    properties = ET.SubElement(paragraph, f"{{{_W}}}pPr")
    ET.SubElement(properties, f"{{{_W}}}jc").set(f"{{{_W}}}val", alignment)
    for piece in _PAGE_PLACEHOLDER.split(text):
        if piece == "{page}":
            _field_runs(paragraph, "PAGE")
        elif piece == "{pages}":
            _field_runs(paragraph, "NUMPAGES")
        elif piece:
            run = ET.SubElement(paragraph, f"{{{_W}}}r")
            _running_run_properties(run)
            text_element = ET.SubElement(run, f"{{{_W}}}t")
            text_element.text = piece
            text_element.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    data: bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    return data


def _attach_running_text(sect_pr: ET.Element, *, header: bool, footer: bool) -> None:
    """Point the section at the generated header and footer parts."""
    for reference in sect_pr.findall("w:headerReference", _NS) + sect_pr.findall(
        "w:footerReference", _NS
    ):
        if reference.get(f"{{{_W}}}type") == "default":
            sect_pr.remove(reference)
    position = 0
    for present, tag, rel_id in (
        (header, "headerReference", _HEADER_REL_ID),
        (footer, "footerReference", _FOOTER_REL_ID),
    ):
        if present:
            reference = ET.Element(f"{{{_W}}}{tag}")
            reference.set(f"{{{_W}}}type", "default")
            reference.set(f"{{{_R}}}id", rel_id)
            sect_pr.insert(position, reference)
            position += 1


def _paragraph_style(paragraph: ET.Element) -> str | None:
    style = paragraph.find("w:pPr/w:pStyle", _NS)
    return None if style is None else style.get(f"{{{_W}}}val")


def _apply_document_fixes(root: ET.Element, *, html_source: bool = False) -> None:
    """Drop duplicate title paragraphs and turn page-break markers into real breaks."""
    body = root.find("w:body", _NS)
    if body is None:
        return
    paragraphs = [child for child in body if child.tag == f"{{{_W}}}p"]
    # A body that has its own Heading 1 does not need the <title> echoed above it.
    if any(_paragraph_style(paragraph) == "Heading1" for paragraph in paragraphs):
        for paragraph in paragraphs:
            if _paragraph_style(paragraph) in _TITLE_STYLES:
                body.remove(paragraph)
    if html_source:
        for paragraph in paragraphs:
            if _paragraph_style(paragraph) in _HTML_METADATA_STYLES:
                body.remove(paragraph)
    children = list(body)
    for index, child in enumerate(children):
        if child.tag != f"{{{_W}}}p" or _paragraph_style(child) != _PAGE_BREAK_STYLE:
            continue
        following = children[index + 1] if index + 1 < len(children) else None
        if following is not None and following.tag == f"{{{_W}}}p":
            body.remove(child)
            properties = following.find("w:pPr", _NS)
            if properties is None:
                properties = ET.Element(f"{{{_W}}}pPr")
                following.insert(0, properties)
            if properties.find("w:pageBreakBefore", _NS) is None:
                leading = {f"{{{_W}}}pStyle", f"{{{_W}}}keepNext", f"{{{_W}}}keepLines"}
                position = sum(1 for item in properties if item.tag in leading)
                properties.insert(position, ET.Element(f"{{{_W}}}pageBreakBefore"))
        elif following is not None:
            # Tables and other blocks cannot carry the property, so break explicitly.
            for item in list(child):
                child.remove(item)
            run = ET.SubElement(child, f"{{{_W}}}r")
            ET.SubElement(run, f"{{{_W}}}br").set(f"{{{_W}}}type", "page")
        else:
            body.remove(child)


def _set_docx_page_layout(
    path: Path,
    orientation: PageOrientation,
    header: str | None = None,
    footer: str | None = None,
    *,
    html_source: bool = False,
) -> None:
    """Set A4 section properties in a Pandoc-generated OOXML package."""
    width, height = _A4_TWIPS
    if orientation is PageOrientation.LANDSCAPE:
        width, height = height, width
    with tempfile.TemporaryDirectory(prefix="gordon-docx-layout-") as directory:
        replacement = Path(directory) / path.name
        with ZipFile(path, "r") as source, ZipFile(replacement, "w", ZIP_DEFLATED) as target:
            for item in source.infolist():
                data = source.read(item.filename)
                if item.filename == "word/document.xml":
                    root = ET.fromstring(data)
                    _apply_document_fixes(root, html_source=html_source)
                    sect_pr = root.find(".//w:sectPr", _NS)
                    if sect_pr is None:
                        sect_pr = ET.SubElement(root, f"{{{_W}}}sectPr")
                    page_size = sect_pr.find("w:pgSz", _NS)
                    if page_size is None:
                        page_size = ET.SubElement(sect_pr, f"{{{_W}}}pgSz")
                    page_size.set(f"{{{_W}}}w", str(width))
                    page_size.set(f"{{{_W}}}h", str(height))
                    margins = sect_pr.find("w:pgMar", _NS)
                    if margins is None:
                        margins = ET.SubElement(sect_pr, f"{{{_W}}}pgMar")
                    for side in ("top", "right", "bottom", "left"):
                        margins.set(f"{{{_W}}}{side}", str(_MARGIN_TWIPS))
                    if header or footer:
                        _attach_running_text(sect_pr, header=bool(header), footer=bool(footer))
                    data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
                elif item.filename == "word/_rels/document.xml.rels" and (header or footer):
                    data = _add_relationships(data, header=bool(header), footer=bool(footer))
                elif item.filename == "[Content_Types].xml" and (header or footer):
                    data = _add_content_types(data, header=bool(header), footer=bool(footer))
                target.writestr(item, data)
            if header:
                target.writestr("word/gordon-header.xml", _running_part("hdr", header, "right"))
            if footer:
                target.writestr("word/gordon-footer.xml", _running_part("ftr", footer, "center"))
        replacement.replace(path)


def _add_relationships(data: bytes, *, header: bool, footer: bool) -> bytes:
    text = data.decode("utf-8")
    additions = ""
    if header:
        additions += (
            f'<Relationship Id="{_HEADER_REL_ID}" Type="{_REL_BASE}/header" '
            'Target="gordon-header.xml"/>'
        )
    if footer:
        additions += (
            f'<Relationship Id="{_FOOTER_REL_ID}" Type="{_REL_BASE}/footer" '
            'Target="gordon-footer.xml"/>'
        )
    return text.replace("</Relationships>", additions + "</Relationships>").encode("utf-8")


def _add_content_types(data: bytes, *, header: bool, footer: bool) -> bytes:
    text = data.decode("utf-8")
    additions = ""
    if header:
        additions += (
            f'<Override PartName="/word/gordon-header.xml" ContentType="{_HEADER_CONTENT_TYPE}"/>'
        )
    if footer:
        additions += (
            f'<Override PartName="/word/gordon-footer.xml" ContentType="{_FOOTER_CONTENT_TYPE}"/>'
        )
    return text.replace("</Types>", additions + "</Types>").encode("utf-8")


def _apply_fonts(rpr: ET.Element, font_family: str | None) -> None:
    """Point one run-properties element at the requested Latin and CJK fonts."""
    fonts = rpr.find("w:rFonts", _NS)
    if fonts is None:
        fonts = ET.Element(f"{{{_W}}}rFonts")
        rpr.insert(0, fonts)
    for attribute in _THEME_FONT_ATTRIBUTES:
        fonts.attrib.pop(f"{{{_W}}}{attribute}", None)
    latin_font = font_family or _LATIN_FONT
    east_asian_font = font_family or _EAST_ASIAN_FONT
    for attribute in ("ascii", "hAnsi", "cs"):
        fonts.set(f"{{{_W}}}{attribute}", latin_font)
    fonts.set(f"{{{_W}}}eastAsia", east_asian_font)


def _child(parent: ET.Element, name: str, *, first: bool = False) -> ET.Element:
    """Return the named child of ``parent``, creating it when it is missing."""
    found = parent.find(f"w:{name}", _NS)
    if found is not None:
        return found
    created = ET.Element(f"{{{_W}}}{name}")
    if first:
        parent.insert(0, created)
    else:
        parent.append(created)
    return created


def _shading(fill: str) -> ET.Element:
    shading = ET.Element(f"{{{_W}}}shd")
    shading.set(f"{{{_W}}}val", "clear")
    shading.set(f"{{{_W}}}color", "auto")
    shading.set(f"{{{_W}}}fill", fill)
    return shading


def _apply_code_run_style(style: ET.Element) -> None:
    """Render code in a monospace face; the East Asian fallback font stays as it was."""
    run_properties = _child(style, "rPr")
    fonts = _child(run_properties, "rFonts", first=True)
    for attribute in ("ascii", "hAnsi", "cs"):
        fonts.set(f"{{{_W}}}{attribute}", _MONOSPACE_FONT)
    _child(run_properties, "sz").set(f"{{{_W}}}val", _CODE_HALF_POINTS)


def _apply_code_block_style(style: ET.Element) -> None:
    """Give code blocks a light background so they read apart from prose."""
    paragraph_properties = _child(style, "pPr")
    if paragraph_properties.find("w:shd", _NS) is None:
        paragraph_properties.append(_shading(_CODE_BLOCK_FILL))


def _apply_table_style(style: ET.Element) -> None:
    """Add grid borders, cell padding, and a shaded bold header row to the table style."""
    table_properties = _child(style, "tblPr")
    if table_properties.find("w:tblBorders", _NS) is None:
        borders = ET.Element(f"{{{_W}}}tblBorders")
        for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
            edge = ET.SubElement(borders, f"{{{_W}}}{side}")
            edge.set(f"{{{_W}}}val", "single")
            edge.set(f"{{{_W}}}sz", "4")
            edge.set(f"{{{_W}}}space", "0")
            edge.set(f"{{{_W}}}color", _TABLE_BORDER_COLOR)
        margins = table_properties.find("w:tblCellMar", _NS)
        position = (
            len(table_properties) if margins is None else list(table_properties).index(margins)
        )
        table_properties.insert(position, borders)
    margins = table_properties.find("w:tblCellMar", _NS)
    if margins is not None:
        for side in ("top", "bottom"):
            cell = margins.find(f"w:{side}", _NS)
            if cell is not None:
                cell.set(f"{{{_W}}}w", "40")
    for override in style.findall("w:tblStylePr", _NS):
        if override.get(f"{{{_W}}}type") != "firstRow":
            continue
        _child(_child(override, "rPr", first=True), "b")
        cell_properties = _child(override, "tcPr")
        if cell_properties.find("w:shd", _NS) is None:
            after = [
                index
                for index, item in enumerate(cell_properties)
                if item.tag == f"{{{_W}}}tcBorders"
            ]
            cell_properties.insert(after[0] + 1 if after else 0, _shading(_TABLE_HEADER_FILL))


def _restyle_reference_docx(path: Path, font_family: str | None) -> None:
    """Rewrite a reference document so headings and body text use CJK-capable fonts."""
    with tempfile.TemporaryDirectory(prefix="gordon-docx-reference-") as directory:
        replacement = Path(directory) / path.name
        with ZipFile(path, "r") as source, ZipFile(replacement, "w", ZIP_DEFLATED) as target:
            for item in source.infolist():
                data = source.read(item.filename)
                if item.filename == "word/styles.xml":
                    root = ET.fromstring(data)
                    defaults = root.find("w:docDefaults/w:rPrDefault/w:rPr", _NS)
                    if defaults is None:
                        defaults = root.find("w:docDefaults/w:rPrDefault", _NS)
                        if defaults is None:
                            rpr_default = ET.SubElement(
                                ET.SubElement(root, f"{{{_W}}}docDefaults"),
                                f"{{{_W}}}rPrDefault",
                            )
                            defaults = ET.SubElement(rpr_default, f"{{{_W}}}rPr")
                        else:
                            defaults = ET.SubElement(defaults, f"{{{_W}}}rPr")
                    _apply_fonts(defaults, font_family)
                    size = defaults.find("w:sz", _NS)
                    if size is None:
                        size = ET.SubElement(defaults, f"{{{_W}}}sz")
                    size.set(f"{{{_W}}}val", _BODY_HALF_POINTS)
                    # Named styles carry their own fonts, which would win over the defaults.
                    for style in root.findall("w:style", _NS):
                        run_properties = style.find("w:rPr", _NS)
                        if (
                            run_properties is not None
                            and run_properties.find("w:rFonts", _NS) is not None
                        ):
                            _apply_fonts(run_properties, font_family)
                    for style in root.findall("w:style", _NS):
                        style_id = style.get(f"{{{_W}}}styleId")
                        if style_id == "VerbatimChar":
                            _apply_code_run_style(style)
                        elif style_id == "SourceCode":
                            _apply_code_block_style(style)
                        elif style_id == "Table":
                            _apply_table_style(style)
                    data = ET.tostring(root, encoding="utf-8", xml_declaration=True)
                target.writestr(item, data)
        replacement.replace(path)


class PandocConverter:
    """Convert HTML or Markdown sources to A4 DOCX using Pandoc.

    PDF output does not come through here: Pandoc's HTML reader keeps only the body and
    the document metadata, which would discard the page setup a print document carries.
    """

    def __init__(self, executable: str | None = None) -> None:
        self._executable = executable or shutil.which("pandoc")

    def convert(
        self,
        source_path: Path,
        output_path: Path,
        *,
        source_format: SourceFormat,
        options: ConversionOptions,
    ) -> None:
        """Run Pandoc with bounded execution and apply the requested A4 layout."""
        if self._executable is None:
            raise EngineUnavailableError("Pandoc is required for HTML or Markdown conversion")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        input_format = _MARKDOWN_DIALECT if source_format is SourceFormat.MARKDOWN else "html"
        arguments: list[str] = [
            self._executable,
            str(source_path),
            "--from",
            input_format,
            "--output",
            str(output_path),
            # Relative image paths belong to the source document, not to our working directory.
            "--resource-path",
            str(source_path.parent),
        ]
        with tempfile.TemporaryDirectory(prefix="gordon-pandoc-") as directory:
            reference = self._reference_docx(
                Path(directory), options.timeout_seconds, options.font_family
            )
            if reference is not None:
                arguments += ["--reference-doc", str(reference)]
            if source_format is SourceFormat.HTML:
                page_break_filter = Path(directory) / "page-break.lua"
                page_break_filter.write_text(_PAGE_BREAK_FILTER, encoding="utf-8", newline="\n")
                arguments += ["--lua-filter", str(page_break_filter)]
            self._run(arguments, options.timeout_seconds)
        if not output_path.is_file() or output_path.stat().st_size == 0:
            raise EngineFailedError("Pandoc did not create the requested output", engine="pandoc")
        header, footer = (
            _read_running_text(source_path) if source_format is SourceFormat.HTML else (None, None)
        )
        _set_docx_page_layout(
            output_path,
            options.page_orientation,
            header,
            footer,
            html_source=source_format is SourceFormat.HTML,
        )

    def _reference_docx(
        self,
        workspace: Path,
        timeout_seconds: float,
        font_family: str | None,
    ) -> Path | None:
        """Build a restyled copy of Pandoc's own reference document, or skip it on failure."""
        if self._executable is None:
            return None
        empty = workspace / "reference-source.md"
        empty.write_text("", encoding="utf-8", newline="\n")
        reference = workspace / "reference.docx"
        arguments = [
            self._executable,
            str(empty),
            "--from",
            _MARKDOWN_DIALECT,
            "--output",
            str(reference),
        ]
        try:
            result = run_process(arguments, timeout_seconds)
        except (ProcessStartError, ProcessTimeoutError):
            return None
        if result.returncode != 0 or not reference.is_file():
            return None
        try:
            _restyle_reference_docx(reference, font_family)
        except (OSError, ET.ParseError, ValueError):
            return None
        return reference

    def _run(self, arguments: list[str], timeout_seconds: float) -> None:
        """Execute one bounded Pandoc invocation and translate its failures."""
        try:
            result = run_process(arguments, timeout_seconds)
        except ProcessStartError as exc:
            raise EngineUnavailableError("Pandoc could not be started") from exc
        except ProcessTimeoutError as exc:
            raise ConversionTimeoutError("Pandoc conversion timed out", engine="pandoc") from exc
        if result.returncode != 0:
            detail = result.stderr.strip()
            message = "Pandoc conversion failed"
            if detail:
                message += f": {detail.splitlines()[-1][:240]}"
            raise EngineFailedError(message, engine="pandoc")
