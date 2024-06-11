"PDF export."

from icecream import ic

import copy
import datetime
import io
import os

import tkinter as tk
import tkinter.simpledialog
import tkinter.ttk

import fpdf

import utils
import constants
from utils import Tr

FONTDIR = "/usr/share/fonts/truetype/freefont"

HREF_COLOR = (20, 20, 255)
THEMATIC_BREAK_INDENT = 100

EACH_TEXT = "After each text"
EACH_CHAPTER = "After each chapter"
END_OF_BOOK = "At end of book"
FOOTNOTES_DISPLAY = (
    EACH_TEXT,
    EACH_CHAPTER,
    END_OF_BOOK,
)
    
PAGE_NUMBER = "Page number"
TEXT_FULL_NAME = "Text full name"
TEXT_HEADING = "Text heading"
INDEXED_XREF_DISPLAY = (
    PAGE_NUMBER,
    TEXT_FULL_NAME,
    TEXT_HEADING,
)

NO_XREF = "No xrefs"
REFERENCES_XREF_DISPLAY = (
    NO_XREF,
    PAGE_NUMBER,
    TEXT_FULL_NAME,
    TEXT_HEADING,
)


class Exporter:
    "HTML exporter."

    def __init__(self, main, source, config):
        self.main = main
        self.source = source
        self.config = config

    def write(self):
        "Output a PDF file."
        if self.config.get("contents_pages", True):
            for contents_pages in range(1, 20):
                try:
                    self.write_attempt(contents_pages)
                    return
                except fpdf.errors.FPDFException as msg:
                    pass
        # If 20 isn't enough, give up and skip the contents page.
        self.write_attempt(0)

    def write_attempt(self, contents_pages):
        "Attempt at writing PDF given the number of content pages to use."
        # Key: canonical; value: dict(ordinal, fullname, heading, page)
        self.indexed = {}
        self.indexed_count = 0
        # Key: reference id; value: dict(ordinal, fullname, heading, page)
        self.referenced = {}
        self.referenced_count = 0
        self.list_stack = []
        # Key: fullname; value: dict(label, number, ast_children)
        self.footnotes = {}

        self.pdf = fpdf.FPDF(format="a4", unit="pt")
        self.pdf.set_title(self.main.title)
        if self.main.language:
            self.pdf.set_lang(self.main.language)
        if self.main.authors:
            self.pdf.set_author(", ".join(self.main.authors))
        self.pdf.set_creator(f"Au {constants.__version__}")
        self.pdf.set_creation_date(datetime.datetime.now())

        self.pdf.add_font(
            "FreeSans", style="", fname=os.path.join(FONTDIR, "FreeSans.ttf")
        )
        self.pdf.add_font(
            "FreeSans", style="B", fname=os.path.join(FONTDIR, "FreeSansBold.ttf")
        )
        self.pdf.add_font(
            "FreeSans", style="I", fname=os.path.join(FONTDIR, "FreeSansOblique.ttf")
        )
        self.pdf.add_font(
            "FreeSans",
            style="BI",
            fname=os.path.join(FONTDIR, "FreeSansBoldOblique.ttf"),
        )
        self.pdf.add_font(
            "FreeSerif", style="", fname=os.path.join(FONTDIR, "FreeSerif.ttf")
        )
        self.pdf.add_font(
            "FreeSerif", style="B", fname=os.path.join(FONTDIR, "FreeSerifBold.ttf")
        )
        self.pdf.add_font(
            "FreeSerif", style="I", fname=os.path.join(FONTDIR, "FreeSerifItalic.ttf")
        )
        self.pdf.add_font(
            "FreeSerif",
            style="BI",
            fname=os.path.join(FONTDIR, "FreeSerifBoldItalic.ttf"),
        )
        self.pdf.add_font(
            "FreeMono", style="", fname=os.path.join(FONTDIR, "FreeMono.ttf")
        )
        self.pdf.add_font(
            "FreeMono", style="B", fname=os.path.join(FONTDIR, "FreeMonoBold.ttf")
        )
        self.pdf.add_font(
            "FreeMono", style="I", fname=os.path.join(FONTDIR, "FreeMonoOblique.ttf")
        )
        self.pdf.add_font(
            "FreeMono",
            style="BI",
            fname=os.path.join(FONTDIR, "FreeMonoBoldOblique.ttf"),
        )

        self.state = State(self.pdf)

        self.write_title_page()
        if contents_pages:
            self.pdf.add_page()
            self.pdf.start_section(Tr("Contents"), level=0)
            self.pdf.insert_toc_placeholder(self.write_toc, pages=contents_pages)
            self.skip_first_add_page = True
        else:
            self.skip_first_add_page = False

        self.current_text = None
        # First-level items are chapters.
        for item in self.source.items:
            if item.is_section:
                self.write_section(item, level=1)
            else:
                self.write_text(item, level=1)
            if self.config["footnotes"] == EACH_CHAPTER:
                self.write_footnotes_chapter(item)
        if self.config["footnotes"] == END_OF_BOOK:
            self.write_footnotes_book()
        self.write_references()
        self.write_indexed()

        # This may fail if the number of content pages is wrong.
        self.pdf.output(
            os.path.join(self.config["dirpath"], self.config["filename"])
        )

    def write_title_page(self):
        self.pdf.add_page()
        self.state.set(style="B", font_size=constants.FONT_TITLE_SIZE)
        self.state.ln()
        self.state.write(self.main.title)
        self.state.ln()
        self.state.reset()

        if self.main.subtitle:
            self.state.set(font_size=constants.FONT_LARGE_SIZE + 10)
            self.state.write(self.main.subtitle)
            self.state.ln()
            self.state.reset()

        self.state.set(font_size=constants.FONT_LARGE_SIZE + 5)
        self.state.ln()
        for author in self.main.authors:
            self.state.write(author)
            self.state.ln()
        self.state.reset()

        self.state.ln(3)
        status = str(
            min([t.status for t in self.source.all_texts] + [max(constants.STATUSES)])
        )
        self.state.write(f'{Tr("Status")}: {Tr(status)}')
        self.state.ln()

        now = datetime.datetime.now().strftime(constants.TIME_ISO_FORMAT)
        self.state.write(f'{Tr("Created")}: {now}')
        self.state.ln(2)

    def write_toc(self, pdf, outline):
        h1 = constants.H_LOOKUP[1]
        font_size = h1["font"][1]
        pdf.set_font(style="B", size=font_size)
        pdf.cell(h=1.5 * font_size, text=Tr("Contents"))
        pdf.ln(1.5 * font_size)
        pdf.set_font(style="", size=constants.FONT_NORMAL_SIZE)

        self.state.set(line_height=1.1)
        with pdf.table(first_row_as_headings=False, borders_layout="none") as table:
            for section in outline[1:]:  # Skip "Contents" entry.
                link = pdf.add_link(page=section.page_number)
                row = table.row()
                row.cell(f'{" " * section.level * 2} {section.name}', link=link)
                row.cell(str(section.page_number), link=link)
        self.state.reset()

    def write_section(self, section, level):
        if level <= self.config["page_break_level"]:
            if self.skip_first_add_page:
                self.skip_first_add_page = False
            else:
                self.pdf.add_page()
        if level <= self.config["contents_level"]:
            self.pdf.start_section(section.heading, level=level - 1)
        self.write_heading(section.heading, level)
        for item in section.items:
            if item.is_section:
                self.write_section(item, level=level + 1)
            else:
                self.write_text(item, level=level + 1)

    def write_text(self, text, level):
        if level <= self.config["page_break_level"]:
            if self.skip_first_add_page:
                self.skip_first_add_page = False
            else:
                self.pdf.add_page()
        if level <= self.config["contents_level"]:
            self.pdf.start_section(text.heading, level=level - 1)
        if text.get("display_heading", True):
            self.write_heading(text.heading, level)
        self.current_text = text
        self.render(text.ast)
        if self.config["footnotes"] == EACH_TEXT:
            self.write_footnotes_text(text)

    def write_heading(self, heading, level, factor=1.5):
        level = min(level, constants.MAX_H_LEVEL)
        self.state.set(style="B", font_size=constants.H_LOOKUP[level]["font"][1])
        self.state.write(heading)
        self.state.ln(factor)
        self.state.reset()

    def write_footnotes_text(self, text):
        "Write footnotes definitions at the end of each text."
        try:
            footnotes = self.footnotes[text.fullname]
        except KeyError:
            return
        self.state.ln()
        self.write_heading(Tr("Footnotes"), 6)
        self.state.set(line_height=1.1)
        for entry in sorted(footnotes.values(), key=lambda e: e["number"]):
            self.state.write(f"{entry['number']}. ")
            self.state.set(left_indent=20)
            for child in entry["ast_children"]:
                self.render(child)
            self.state.reset()
        self.state.reset()

    def write_footnotes_chapter(self, item):
        "Write footnotes definitions at the end of a chapter."
        try:
            footnotes = self.footnotes[item.chapter.fullname]
        except KeyError:
            return
        self.pdf.add_page()
        self.write_heading(Tr("Footnotes"), 4)
        self.state.set(line_height=1.1)
        for entry in sorted(footnotes.values(), key=lambda e: e["number"]):
            self.state.write(f"{entry['number']}. ")
            self.state.set(left_indent=20)
            for child in entry["ast_children"]:
                self.render(child)
            self.state.reset()
        self.state.reset()

    def write_footnotes_book(self):
        "Write footnotes definitions as a separate section at the end of the book."
        self.pdf.add_page()
        self.pdf.start_section(Tr("Footnotes"), level=0)
        self.write_heading(Tr("Footnotes"), 1)
        for item in self.source.items:
            footnotes = self.footnotes.get(item.fullname, {})
            if not footnotes:
                continue
            self.write_heading(item.heading, 2)
            self.state.set(line_height=1.1)
            for entry in sorted(footnotes.values(), key=lambda e: e["number"]):
                self.state.write(f"{entry['number']}. ")
                self.state.set(left_indent=20)
                for child in entry["ast_children"]:
                    self.render(child)
                self.state.reset()
            self.state.reset()

    def write_references(self):
        self.pdf.add_page()
        self.pdf.start_section(Tr("References"), level=0)
        self.write_heading(Tr("References"), 1)
        lookup = self.main.references_viewer.reference_lookup
        for refid, entries in sorted(self.referenced.items()):
            reference = lookup[refid]
            self.state.set(style="B")
            self.state.write(refid)
            self.state.reset()
            self.state.write("  ")
            self.write_reference_authors(reference)
            try:
                method = getattr(self, f"write_reference_{reference['type']}")
            except AttributeError:
                ic("unknown", reference["type"])
            else:
                method(reference)
            self.write_reference_external_links(reference)
            self.write_reference_xrefs(entries)
            self.state.ln(2)

    def write_reference_authors(self, reference):
        count = len(reference["authors"])
        for pos, author in enumerate(reference["authors"]):
            if pos > 0:
                if pos == count - 1:
                    self.state.write(" & ")
                else:
                    self.state.write(", ")
            self.state.write(utils.shortname(author))

    def write_reference_article(self, reference):
        self.state.write(f" ({reference['year']})")
        try:
            self.state.write(" " + reference["title"].strip(".") + ".")
        except KeyError:
            pass
        journal = reference.get("journal")
        if journal:
            self.state.set(style="I")
            self.state.write(" " + journal)
            self.state.reset()
        try:
            self.state.write(" " + reference['volume'])
        except KeyError:
            pass
        else:
            try:
                self.state.write(f" ({reference['number']})")
            except KeyError:
                pass
        try:
            self.state.write(f": pp. {reference['pages'].replace('--', '-')}.")
        except KeyError:
            pass

    def write_reference_book(self, reference):
        self.state.write(f" ({reference['year']}).")
        self.state.set(style="I")
        self.state.write(" " + reference["title"].strip(".") + ". ")
        self.state.reset()
        try:
            self.state.write(f" {reference['publisher']}.")
        except KeyError:
            pass

    def write_reference_link(self, reference):
        self.state.write(f" ({reference['year']}).")
        try:
            self.state.write(" " + reference["title"].strip(".") + ". ")
        except KeyError:
            pass
        try:
            self.state.set(style="U", text_color=HREF_COLOR)
            self.pdf.cell(
                h=self.state.line_height * self.state.font_size,
                text=reference["title"],
                link=reference["url"],
            )
            self.state.reset()
        except KeyError:
            pass
        try:
            self.state.write(f"Accessed {reference['accessed']}.")
        except KeyError:
            pass

    def write_reference_external_links(self, reference):
        links = []
        for key, label, template in constants.REFERENCE_LINKS:
            try:
                value = reference[key]
                text = f"{label}:{value}"
                url = template.format(value=value)
                links.append((text, url))
            except KeyError:
                pass
        if not links:
            return
        self.state.set(left_indent=20)
        self.state.ln()
        for pos, (text, link) in enumerate(links):
            if pos != 0:
                self.state.write(", ")
            self.state.set(style="U", text_color=HREF_COLOR)
            self.pdf.cell(
                h=self.state.line_height * self.state.font_size,
                text=text,
                link=url,
                new_x=fpdf.enums.XPos.WCONT,
            )
            self.state.reset()
        self.state.reset()

    def write_reference_xrefs(self, entries):
        if not entries:
            return
        if self.config["references_xref"] == NO_XREF:
            return
        if self.config["references_xref"] == PAGE_NUMBER:
            key = "page"
        elif self.config["references_xref"] == TEXT_FULL_NAME:
            key = "fullname"
        elif self.config["references_xref"] == TEXT_HEADING:
            key = "heading"
        else:
            return
        self.state.set(left_indent=20)
        self.state.ln()
        for pos, entry in enumerate(sorted(entries, key=lambda e: e["ordinal"])):
            if pos != 0:
                self.state.write(", ")
            self.state.set(style="U", text_color=HREF_COLOR)
            self.pdf.cell(
                h=self.state.line_height * self.state.font_size,
                text=str(entry[key]),  # Page number is 'int'.
                link=self.pdf.add_link(page=entry["page"]),
                new_x=fpdf.enums.XPos.WCONT,
            )
            self.state.reset()
        self.state.reset()

    def write_indexed(self):
        self.pdf.add_page()
        self.pdf.start_section(Tr("Index"), level=0)
        self.write_heading(Tr("Index"), 1)
        if self.config["indexed_xref"] == PAGE_NUMBER:
            key = "page"
        elif self.config["indexed_xref"] == TEXT_FULL_NAME:
            key = "fullname"
        elif self.config["indexed_xref"] == TEXT_HEADING:
            key = "heading"
        else:
            return
        items = sorted(self.indexed.items(), key=lambda i: i[0].lower())
        for canonical, entries in items:
            self.state.set(style="B")
            self.state.write(canonical)
            self.state.reset()
            self.state.write("  ")
            entries.sort(key=lambda e: e["ordinal"])
            for pos, entry in enumerate(entries):
                if pos != 0:
                    self.state.write(", ")
                self.state.set(style="U", text_color=HREF_COLOR)
                self.pdf.cell(
                    h=self.state.line_height * self.state.font_size,
                    text=str(entry[key]),  # Page number is 'int'.
                    link=self.pdf.add_link(page=entry["page"]),
                    new_x=fpdf.enums.XPos.WCONT,
                )
                self.state.reset()
            self.state.ln()

    def render(self, ast):
        try:
            method = getattr(self, f"render_{ast['element']}")
        except AttributeError:
            ic("Could not handle ast", ast)
        else:
            method(ast)

    def render_document(self, ast):
        for child in ast["children"]:
            self.render(child)

    def render_paragraph(self, ast):
        for child in ast["children"]:
            self.render(child)
        if self.list_stack:
            if self.list_stack[-1]["tight"]:
                self.state.ln()
            else:
                self.state.ln(2)
        else:
            self.state.ln(2)

    def render_raw_text(self, ast):
        line = ast["children"]
        self.state.write(line)

    def render_blank_line(self, ast):
        pass

    def render_quote(self, ast):
        self.state.set(
            family=constants.QUOTE_FONT,
            font_size=constants.QUOTE_FONT_SIZE,
            left_indent=constants.QUOTE_LEFT_INDENT,
            right_indent=constants.QUOTE_RIGHT_INDENT,
        )
        for child in ast["children"]:
            self.render(child)
        self.state.reset()

    def render_code_span(self, ast):
        self.state.set(family=constants.CODE_FONT)
        self.state.write(ast["children"])
        self.state.reset()

    def render_code_block(self, ast):
        self.state.set(
            family=constants.CODE_FONT,
            left_indent=constants.CODE_INDENT,
            line_height=1.2,
        )
        for child in ast["children"]:
            self.render(child)
        self.state.reset()
        self.state.ln()

    def render_fenced_code(self, ast):
        self.state.set(
            family=constants.CODE_FONT,
            left_indent=constants.CODE_INDENT,
            line_height=1.2,
        )
        for child in ast["children"]:
            self.render(child)
        self.state.reset()
        self.state.ln()

    def render_emphasis(self, ast):
        self.state.set(style="I")
        for child in ast["children"]:
            self.render(child)
        self.state.reset()

    def render_strong_emphasis(self, ast):
        self.state.set(style="B")
        for child in ast["children"]:
            self.render(child)
        self.state.reset()

    def render_thematic_break(self, ast):
        self.pdf.set_line_width(2)
        self.pdf.set_draw_color(r=128, g=128, b=128)
        width, height = self.pdf.default_page_dimensions
        self.pdf.line(
            x1=self.pdf.l_margin + THEMATIC_BREAK_INDENT,
            y1=self.pdf.y,
            x2=width - (self.pdf.r_margin + THEMATIC_BREAK_INDENT),
            y2=self.pdf.y,
        )
        self.state.ln()

    def render_link(self, ast):
        # XXX This handles only raw text within a link, nothing else.
        raw_text = []
        for child in ast["children"]:
            if child["element"] == "raw_text":
                raw_text.append(child["children"])
        self.state.set(style="U", text_color=HREF_COLOR)
        self.pdf.cell(
            h=self.state.line_height * self.state.font_size,
            text="".join(raw_text),
            link=ast["dest"],
            new_x=fpdf.enums.XPos.WCONT,
        )
        self.state.reset()

    def render_list(self, ast):
        data = dict(
            ordered=ast["ordered"],
            bullet=ast["bullet"],  # Currently useless.
            start=ast["start"],  # Currently useless.
            tight=ast["tight"],
            depth=len(self.list_stack) + 1,
            count=0,
        )
        self.list_stack.append(data)
        self.state.set(line_height=1.1)
        for child in ast["children"]:
            self.render(child)
        self.state.reset()
        if self.list_stack[-1]["tight"]:
            self.state.ln()
        self.list_stack.pop()

    def render_list_item(self, ast):
        data = self.list_stack[-1]
        data["count"] += 1
        self.state.set(style="B")
        if data["ordered"]:
            self.state.write(f'{data["count"]}. ')
        else:
            self.state.write("- ")
        self.state.reset()
        self.state.set(left_indent=data["depth"] * constants.LIST_INDENT)
        for child in ast["children"]:
            self.render(child)
        self.state.reset()

    def render_indexed(self, ast):
        entries = self.indexed.setdefault(ast["canonical"], [])
        self.indexed_count += 1
        entries.append(
            dict(
                ordinal=self.current_text.ordinal,
                fullname=self.current_text.fullname,
                heading=self.current_text.heading,
                page=self.pdf.page_no(),
            )
        )
        self.state.set(style="U")
        self.state.write(ast["term"])
        self.state.reset()

    def render_footnote_ref(self, ast):
        "The label is used only for lookup; number is used for output."
        label = ast["label"]
        if self.config["footnotes"] == EACH_TEXT:
            entries = self.footnotes.setdefault(self.current_text.fullname, {})
            number = len(entries) + 1
            key = label
        elif self.config["footnotes"] in (EACH_CHAPTER, END_OF_BOOK):
            fullname = self.current_text.chapter.fullname
            entries = self.footnotes.setdefault(fullname, {})
            number = len(entries) + 1
            key = f"{fullname}-{label}"
        entries[key] = dict(label=label, number=number, page=self.pdf.page_no())
        self.state.set(vertical="superscript", style="B")
        self.state.write(str(number))
        self.state.reset()

    def render_footnote_def(self, ast):
        label = ast["label"]
        if self.config["footnotes"] == EACH_TEXT:
            fullname = self.current_text.fullname
            key = label
        elif self.config["footnotes"] in (EACH_CHAPTER, END_OF_BOOK):
            fullname = self.current_text.chapter.fullname
            key = f"{fullname}-{label}"
        self.footnotes[fullname][key]["ast_children"] = ast["children"]

    def render_reference(self, ast):
        entries = self.referenced.setdefault(ast["reference"], [])
        self.referenced_count += 1
        entries.append(
            dict(
                ordinal=self.current_text.ordinal,
                fullname=self.current_text.fullname,
                heading=self.current_text.heading,
                page=self.pdf.page_no(),
            )
        )
        self.state.set(style="U")
        self.state.write(ast["reference"])
        self.state.reset()


class Current:
    "Field providing the current value of the style parameter."

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, obj, objtype=None):
        return obj.stack[-1][self.name]


class State:
    "Current style parameters state as a stack."

    family = Current()
    style = Current()
    font_size = Current()
    text_color = Current()
    line_height = Current()
    left_indent = Current()
    right_indent = Current()
    vertical = Current()

    def __init__(self, pdf):
        self.pdf = pdf
        self.stack = [
            dict(
                family=constants.FONT,
                style="",
                text_color=0,
                font_size=constants.FONT_NORMAL_SIZE,
                line_height=1.4,
                left_indent=0,
                right_indent=0,
                vertical=None,
            )
        ]
        self.pdf.set_font(family=self.family, style=self.style, size=self.font_size)
        self.l_margin = self.pdf.l_margin
        self.r_margin = self.pdf.r_margin

    def set(self, **kwargs):
        self.set_pdf_state(**kwargs)
        self.stack.append(self.stack[-1].copy())
        self.stack[-1].update(kwargs)

    def reset(self):
        diff = dict(
            [(k, v) for k, v in self.stack[-2].items() if self.stack[-1][k] != v]
        )
        self.stack.pop()
        self.set_pdf_state(**diff)

    def set_pdf_state(self, **kwargs):
        try:
            self.pdf.set_font(family=kwargs["family"])
        except KeyError:
            pass
        try:  # Due to apparent bug in fpdf2, set font_size before style.
            self.pdf.set_font(size=kwargs["font_size"])
        except KeyError:
            pass
        try:
            self.pdf.set_font(style=kwargs["style"])
        except KeyError:
            pass
        try:
            self.pdf.set_text_color(kwargs["text_color"])
        except KeyError:
            pass
        try:
            value = kwargs["left_indent"]
        except KeyError:
            pass
        else:
            self.pdf.set_left_margin(self.l_margin + value)
        try:
            value = kwargs["right_indent"]
        except KeyError:
            pass
        else:
            self.pdf.set_right_margin(self.l_margin + value)
        try:
            value = kwargs["vertical"]
        except KeyError:
            pass
        else:
            if value == "superscript":
                self.pdf.char_vpos = "SUP"
            elif value == "subscript":
                self.pdf.char_vpos = "SUB"
            else:
                self.pdf.char_vpos = "LINE"

    def write(self, text, link=""):
        self.pdf.write(h=self.font_size * self.line_height, text=text, link=link)

    def ln(self, factor=1):
        self.pdf.ln(factor * self.font_size * self.line_height)


class Dialog(tk.simpledialog.Dialog):
    "Dialog to confirm or modify configuration before export."

    def __init__(self, master, source, config):
        self.source = source
        self.config = copy.deepcopy(config)
        self.result = None
        super().__init__(master, title=Tr("HTML export"))

    def body(self, body):
        row = 0
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_columnconfigure(2, weight=1)

        row += 1
        label = tk.ttk.Label(body, text=Tr("Directory"), padding=4)
        label.grid(row=row, column=0, sticky=tk.NE)
        self.dirpath_entry = tk.ttk.Entry(body, width=40)
        self.dirpath_entry.insert(0, self.config.get("dirpath") or os.getcwd())
        self.dirpath_entry.grid(row=row, column=1, sticky=tk.W)
        button = tk.ttk.Button(body, text=Tr("Choose"), command=self.change_dirpath)
        button.grid(row=row, column=3)

        row += 1
        label = tk.ttk.Label(body, text=Tr("Filename"))
        label.grid(row=row, column=0, padx=4, sticky=tk.NE)
        self.filename_entry = tk.ttk.Entry(body, width=40)
        self.filename_entry.insert(0, self.config.get("filename") or "book.pdf")
        self.filename_entry.grid(row=row, column=1, sticky=tk.W)

        row += 1
        label = tk.ttk.Label(body, text=Tr("Page break level"))
        label.grid(row=row, column=0, padx=4, sticky=tk.NE)
        self.page_break_level_var = tk.IntVar(
            value=min(self.config.get("page_break_level", 1), self.source.max_level)
        )
        frame = tk.ttk.Frame(body)
        frame.grid(row=row, column=1, padx=4, sticky=tk.W)
        for level in range(1, self.source.max_level + 1):
            button = tk.ttk.Radiobutton(
                frame, text=str(level), value=level, variable=self.page_break_level_var
            )
            button.pack(anchor=tk.W)

        row += 1
        label = tk.ttk.Label(body, text=Tr("Contents level"))
        label.grid(row=row, column=0, padx=4, sticky=tk.NE)
        self.contents_level_var = tk.IntVar(
            value=min(
                self.config.get("contents_level", 1), self.source.max_level
            )
        )
        frame = tk.ttk.Frame(body)
        frame.grid(row=row, column=1, padx=4, sticky=tk.W)
        for level in range(1, self.source.max_level + 1):
            button = tk.ttk.Radiobutton(
                frame,
                text=str(level),
                value=level,
                variable=self.contents_level_var,
            )
            button.pack(anchor=tk.W)

        row += 1
        label = tk.ttk.Label(body, text=Tr("Contents pages"))
        label.grid(row=row, column=0, padx=4, sticky=tk.NE)
        self.contents_pages_var = tk.IntVar(value=self.config.get("contents_pages", True))
        frame = tk.ttk.Frame(body)
        frame.grid(row=row, column=1, padx=4, sticky=tk.W)
        button = tk.ttk.Checkbutton(frame,
                                    text=Tr("Display contents page(s)"),
                                    onvalue=True,
                                    offvalue=False,
                                    variable=self.contents_pages_var)
        button.pack(anchor=tk.W)

        row += 1
        label = tk.ttk.Label(body, text=Tr("Footnotes"))
        label.grid(row=row, column=0, padx=4, sticky=tk.NE)
        self.footnotes_var = tk.StringVar(
            value=self.config.get("footnotes", FOOTNOTES_DISPLAY[0])
        )
        frame = tk.ttk.Frame(body)
        frame.grid(row=row, column=1, padx=4, sticky=tk.W)
        for label in FOOTNOTES_DISPLAY:
            button = tk.ttk.Radiobutton(
                frame, text=Tr(label), value=label, variable=self.footnotes_var
            )
            button.pack(anchor=tk.W)

        row += 1
        label = tk.ttk.Label(body, text=Tr("Xref for indexed"))
        label.grid(row=row, column=0, padx=4, sticky=tk.NE)
        self.indexed_xref_var = tk.StringVar(
            value=self.config.get("indexed_xref", INDEXED_XREF_DISPLAY[0])
        )
        frame = tk.ttk.Frame(body)
        frame.grid(row=row, column=1, padx=4, sticky=tk.W)
        for label in INDEXED_XREF_DISPLAY:
            button = tk.ttk.Radiobutton(
                frame, text=Tr(label), value=label, variable=self.indexed_xref_var
            )
            button.pack(anchor=tk.W)

        row += 1
        label = tk.ttk.Label(body, text=Tr("Xref for references"))
        label.grid(row=row, column=0, padx=4, sticky=tk.NE)
        self.references_xref_var = tk.StringVar(
            value=self.config.get("references_xref", REFERENCES_XREF_DISPLAY[0])
        )
        frame = tk.ttk.Frame(body)
        frame.grid(row=row, column=1, padx=4, sticky=tk.W)
        for label in REFERENCES_XREF_DISPLAY:
            button = tk.ttk.Radiobutton(
                frame, text=Tr(label), value=label, variable=self.references_xref_var
            )
            button.pack(anchor=tk.W)

    def apply(self):
        self.config["dirpath"] = self.dirpath_entry.get().strip() or os.getcwd()
        filename = self.filename_entry.get().strip() or constants.BOOK
        self.config["filename"] = os.path.splitext(filename)[0] + ".pdf"
        self.config["page_break_level"] = self.page_break_level_var.get()
        self.config["contents_level"] = self.contents_level_var.get()
        self.config["contents_pages"] = bool(self.contents_pages_var.get())
        self.config["footnotes"] = self.footnotes_var.get()
        self.config["indexed_xref"] = self.indexed_xref_var.get()
        self.config["references_xref"] = self.references_xref_var.get()
        self.result = self.config

    def change_dirpath(self):
        dirpath = tk.filedialog.askdirectory(
            parent=self,
            title=Tr("Directory"),
            initialdir=self.config.get("dirpath") or os.getcwd(),
            mustexist=True,
        )
        if dirpath:
            self.dirpath_entry.delete(0, tk.END)
            self.dirpath_entry.insert(0, dirpath)
