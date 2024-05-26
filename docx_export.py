"DOCX export."

from icecream import ic

import copy
import datetime
import os.path

import tkinter as tk
import tkinter.simpledialog
import tkinter.filedialog

import docx

import constants
import utils
from utils import Tr


class Exporter:
    "DOCX exporter."

    def __init__(self, main, source, config):
        self.main = main
        self.source = source
        self.config = config

    def write(self, filepath=None):
        if filepath is None:
            filepath = os.path.join(self.source.abspath, self.source.name + ".docx")
        self.document = docx.Document()

        # Set the default document-wide language.
        # From https://stackoverflow.com/questions/36967416/how-can-i-set-the-language-in-text-with-python-docx
        try:
            language = self.config["language"]
        except KeyError:
            pass
        else:
            styles_element = self.document.styles.element
            rpr_default = styles_element.xpath("./w:docDefaults/w:rPrDefault/w:rPr")[0]
            lang_default = rpr_default.xpath("w:lang")[0]
            lang_default.set(docx.oxml.shared.qn("w:val"), language)

        # Set to A4 page size.
        section = self.document.sections[0]
        section.page_height = docx.shared.Mm(297)
        section.page_width = docx.shared.Mm(210)
        section.left_margin = docx.shared.Mm(25.4)
        section.right_margin = docx.shared.Mm(25.4)
        section.top_margin = docx.shared.Mm(25.4)
        section.bottom_margin = docx.shared.Mm(25.4)
        section.header_distance = docx.shared.Mm(12.7)
        section.footer_distance = docx.shared.Mm(12.7)

        # Create style for quote.
        style = self.document.styles.add_style(
            constants.DOCX_QUOTE_STYLE, docx.enum.style.WD_STYLE_TYPE.PARAGRAPH
        )
        style.paragraph_format.left_indent = docx.shared.Pt(
            constants.DOCX_QUOTE_LEFT_INDENT
        )
        style.paragraph_format.right_indent = docx.shared.Pt(
            constants.DOCX_QUOTE_RIGHT_INDENT
        )
        style.font.name = constants.DOCX_QUOTE_FONT

        # Set Dublin core metadata.
        self.document.core_properties.language = language
        self.document.core_properties.modified = datetime.datetime.now()

        self.indexed = {}  # Key: canonical; value: dict(id, fullname)
        self.indexed_count = 0
        self.footnotes = {}  # Key: fullname; value: dict(label, ast_children)

        self.write_title()
        self.current_text = None
        for item in self.source.items:
            if item.is_section:
                self.write_section(item, level=1)
            else:
                self.write_text(item, level=1)
        self.write_references(references=self.main.references_viewer.references)
        self.write_indexed(self.main.indexed_viewer.terms)
        self.document.save(filepath)

    def write_title(self):
        paragraph = self.document.add_paragraph(style="Title")
        paragraph.paragraph_format.space_after = docx.shared.Pt(40)
        run = paragraph.add_run(self.main.title)
        run.font.size = docx.shared.Pt(28)
        run.font.bold = True

        if self.main.subtitle:
            paragraph = self.document.add_paragraph(style=f"Heading 1")
            paragraph.paragraph_format.space_after = docx.shared.Pt(30)
            paragraph.add_run(self.main.subtitle)

        for author in self.main.authors:
            paragraph = self.document.add_paragraph(style=f"Heading 2")
            paragraph.add_run(author)

        statuses = [t.status for t in self.source.all_texts] + [max(constants.STATUSES)]
        paragraph = self.document.add_paragraph()
        paragraph.paragraph_format.space_before = docx.shared.Pt(100)
        paragraph.add_run(Tr("Status"))
        paragraph.add_run(": ")
        statuses = [t.status for t in self.source.all_texts] + [max(constants.STATUSES)]
        paragraph.add_run(Tr(str(min(statuses))))

        paragraph = self.document.add_paragraph()
        paragraph.add_run(Tr("Created"))
        paragraph.add_run(": ")
        paragraph.add_run(datetime.datetime.now().strftime(constants.TIME_ISO_FORMAT))

    def write_section(self, section, level):
        if level <= constants.DOCX_PAGEBREAK_LEVEL:
            self.document.add_page_break()
        self.write_heading(section.name, level)
        for item in section.items:
            if item.is_section:
                self.write_section(item, level=level + 1)
            else:
                self.write_text(item, level=level + 1)

    def write_text(self, text, level):
        if level < constants.DOCX_PAGEBREAK_LEVEL:
            self.document.add_page_break()
        self.write_heading(text.name, level)
        self.style_stack = ["Normal"]
        self.bold = False
        self.italic = False
        self.current_text = text
        self.render(text.ast)
        # Footnotes at end of the text.
        try:
            footnotes = self.footnotes[text.fullname]
        except KeyError:
            return
        self.document.add_heading(Tr("Footnotes"), 6)
        for label in sorted(footnotes.keys()):
            self.document.add_heading(str(label), 7)
            for child in footnotes[label]["ast_children"]:
                self.render(child)

    def write_heading(self, title, level):
        level = min(level, constants.MAX_H_LEVEL)
        h = constants.H_LOOKUP[level]
        paragraph = self.document.add_paragraph(style=f"Heading {level}")
        paragraph.paragraph_format.left_indent = docx.shared.Pt(h["left_margin"])
        paragraph.paragraph_format.space_after = docx.shared.Pt(h["spacing"])
        run = paragraph.add_run(title)
        run.font.size = docx.shared.Pt(h["font"][1])

    def write_references(self, references):
        self.document.add_page_break()
        self.write_heading(Tr("References"), 1)
        for reference in self.main.references_viewer.reference_texts:
            paragraph = self.document.add_paragraph()
            run = paragraph.add_run(reference["id"])
            run.bold = True
            paragraph.add_run("  ")
            self.write_reference_authors(paragraph, reference)
            try:
                method = getattr(self, f"write_reference_{reference['type']}")
            except AttributeError:
                ic("unknown", reference["type"])
            else:
                method(paragraph, reference)
            self.write_reference_external_links(paragraph, reference)

    def write_reference_authors(self, paragraph, reference):
        count = len(reference["authors"])
        for pos, author in enumerate(reference["authors"]):
            if pos > 0:
                if pos == count - 1:
                    paragraph.add_run(" & ")
                else:
                    paragraph.add_run(", ")
            paragraph.add_run(utils.shortname(author))

    def write_reference_article(self, paragraph, reference):
        paragraph.add_run(f"({reference['year']}) ")
        try:
            paragraph.add_run(reference["title"].strip(".") + ". ")
        except KeyError:
            pass
        try:
            run = paragraph.add_run(f"{reference['journal']} ")
            run.font.italic = True
        except KeyError:
            pass
        try:
            paragraph.add_run(f"{reference['volume']} ")
        except KeyError:
            pass
        else:
            try:
                paragraph.add_run(f"({reference['number']})")
            except KeyError:
                pass
        try:
            paragraph.add_run(f": pp. {reference['pages'].replace('--', '-')}.")
        except KeyError:
            pass

    def write_reference_book(self, paragraph, reference):
        paragraph.add_run(f"({reference['year']}). ")
        run = paragraph.add_run(reference["title"].strip(".") + ". ")
        run.font.italic = True
        try:
            paragraph.add_run(f"{reference['publisher']}. ")
        except KeyError:
            pass

    def write_reference_link(self, paragraph, reference):
        paragraph.add_run(f"({reference['year']}). ")
        try:
            paragraph.add_run(reference["title"].strip(".") + ". ")
        except KeyError:
            pass
        try:
            add_hyperlink(paragraph, reference["url"], reference["title"])
        except KeyError:
            pass
        try:
            paragraph.add_run(f" Accessed {reference['accessed']}.")
        except KeyError:
            pass

    def write_reference_external_links(self, paragraph, reference):
        any_item = False
        for key, label, template in constants.REFERENCE_LINKS:
            try:
                value = reference[key]
                if any_item:
                    paragraph.add_run(", ")
                else:
                    paragraph.add_run("  ")
                add_hyperlink(
                    paragraph, template.format(value=value), f"{label}:{value}"
                )
                any_item = True
            except KeyError:
                pass

    def write_indexed(self, terms):
        self.document.add_page_break()
        self.write_heading(Tr("Index"), 1)
        for term, fullnames in terms:
            paragraph = self.document.add_paragraph()
            run = paragraph.add_run(term)
            run.bold = True
            for fullname, positions in sorted(fullnames.items()):
                paragraph.add_run(f" {fullname}")

    def render(self, ast):
        try:
            method = getattr(self, f"render_{ast['element']}")
        except AttributeError:
            ic("Could not handle ast", ast)
        else:
            method(ast)

    def render_document(self, ast):
        self.prev_blank_line = False
        for child in ast["children"]:
            self.render(child)

    def render_paragraph(self, ast):
        self.paragraph = self.document.add_paragraph()
        self.paragraph.style = self.style_stack[-1]
        for child in ast["children"]:
            self.render(child)

    def render_raw_text(self, ast):
        line = ast["children"]
        if line[-1] == "\n":
            line[-1] = " "
        run = self.paragraph.add_run(line)
        if self.bold:
            run.bold = True
        if self.italic:
            run.italic = True

    def render_blank_line(self, ast):
        pass

    def render_quote(self, ast):
        self.style_stack.append(constants.DOCX_QUOTE_STYLE)
        for child in ast["children"]:
            self.render(child)
        self.style_stack.pop()

    def render_emphasis(self, ast):
        self.italic = True
        for child in ast["children"]:
            self.render(child)
        self.italic = False

    def render_strong_emphasis(self, ast):
        self.bold = True
        for child in ast["children"]:
            self.render(child)
        self.bold = False

    def render_thematic_break(self, ast):
        paragraph = self.document.add_paragraph(constants.EM_DASH * 20)
        paragraph.alignment = docx.enum.text.WD_ALIGN_PARAGRAPH.CENTER

    def render_link(self, ast):
        raw_text = []
        for child in ast["children"]:
            if child["element"] == "raw_text" and type(child["children"]) == str:
                raw_text.append(child["children"])
        raw_text = "".join(raw_text)
        add_hyperlink(self.paragraph, ast["dest"], raw_text)

    def render_indexed(self, ast):
        entries = self.indexed.setdefault(ast["canonical"], [])
        self.indexed_count += 1
        entries.append(
            dict(id=f"i{self.indexed_count}", fullname=self.current_text.fullname)
        )
        self.paragraph.add_run(ast["term"])

    def render_footnote_ref(self, ast):
        entries = self.footnotes.setdefault(self.current_text.fullname, {})
        label = int(ast["label"])
        entries[label] = dict(label=label)
        run = self.paragraph.add_run(str(label))
        run.font.superscript = True
        run.font.bold = True

    def render_footnote_def(self, ast):
        label = int(ast["label"])
        self.footnotes[self.current_text.fullname][label]["ast_children"] = ast[
            "children"
        ]

    def render_reference(self, ast):
        run = self.paragraph.add_run(ast["reference"])
        run.font.italic = True
        run.font.underline = True


class Dialog(tk.simpledialog.Dialog):
    "Dialog to confirm or modify configuration before export."

    def __init__(self, master, config):
        self.config = copy.deepcopy(config)
        self.result = None
        super().__init__(master, title=Tr("DOCX export"))

    def body(self, body):
        row = 0
        label = tk.ttk.Label(body, text=Tr("Filename"))
        label.grid(row=row, column=0, padx=4, sticky=tk.E)
        self.filename_entry = tk.ttk.Entry(body, width=40)
        self.filename_entry.insert(0, self.config.get("filename") or "")
        self.filename_entry.grid(row=row, column=1, sticky=tk.W)

        row += 1
        label = tk.ttk.Label(body, text=Tr("Directory"))
        label.grid(row=row, column=0, padx=4, sticky=tk.E)
        self.dirpath_entry = tk.ttk.Entry(body, width=40)
        self.dirpath_entry.insert(0, self.config.get("dirpath") or ".")
        self.dirpath_entry.grid(row=row, column=1, sticky=tk.W)
        button = tk.ttk.Button(body, text=Tr("Choose"), command=self.change_dirpath)
        button.grid(row=row, column=3)

        row += 1
        label = tk.ttk.Label(body, text=Tr("Language"))
        label.grid(row=row, column=0, padx=4, sticky=tk.E)
        self.language_var = tk.StringVar(value=self.config.get("language") or "")
        combobox = tk.ttk.Combobox(
            body,
            values=constants.DOCX_LANGUAGES,
            textvariable=self.language_var,
        )
        combobox.grid(row=row, column=1, sticky=tk.W)

    def apply(self):
        self.config["dirpath"] = self.dirpath_entry.get().strip() or "."
        filename = self.filename_entry.get().strip() or constants.BOOK
        self.config["filename"] = os.path.splitext(filename)[0] + ".docx"
        self.config["language"] = self.language_var.get().strip()
        self.result = self.config

    def change_dirpath(self):
        dirpath = tk.filedialog.askdirectory(
            parent=self,
            title=Tr("Directory"),
            initialdir=self.config.get("dirpath") or ".",
            mustexist=True,
        )
        if dirpath:
            self.dirpath_entry.delete(0, tk.END)
            self.dirpath_entry.insert(0, dirpath)


# From https://github.com/python-openxml/python-docx/issues/74#issuecomment-261169410
def add_hyperlink(paragraph, url, text, color="2222FF", underline=True):
    """
    A function that places a hyperlink within a paragraph object.

    :param paragraph: The paragraph we are adding the hyperlink to.
    :param url: A string containing the required url
    :param text: The text displayed for the url
    :return: The hyperlink object
    """

    # This gets access to the document.xml.rels file and gets a new relation id value.
    part = paragraph.part
    r_id = part.relate_to(
        url, docx.opc.constants.RELATIONSHIP_TYPE.HYPERLINK, is_external=True
    )

    # Create the w:hyperlink tag and add needed values.
    hyperlink = docx.oxml.shared.OxmlElement("w:hyperlink")
    hyperlink.set(
        docx.oxml.shared.qn("r:id"),
        r_id,
    )

    # Create a w:r element.
    new_run = docx.oxml.shared.OxmlElement("w:r")

    # Create a new w:rPr element.
    rPr = docx.oxml.shared.OxmlElement("w:rPr")

    # Add color if it is given.
    if not color is None:
        c = docx.oxml.shared.OxmlElement("w:color")
        c.set(docx.oxml.shared.qn("w:val"), color)
        rPr.append(c)

    # Remove underlining if it is requested.
    # XXX Does not seem to work? /Per Kraulis
    if not underline:
        u = docx.oxml.shared.OxmlElement("w:u")
        u.set(docx.oxml.shared.qn("w:val"), "none")
        rPr.append(u)

    # Join all the xml elements together add add the required text to the w:r element.
    new_run.append(rPr)
    new_run.text = text
    hyperlink.append(new_run)

    paragraph._p.append(hyperlink)

    return hyperlink
