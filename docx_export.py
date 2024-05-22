"DOCX export."

from icecream import ic

import copy
import os.path

import tkinter as tk
import tkinter.simpledialog
import tkinter.filedialog

import docx

# from docx.enum.style import WD_STYLE_TYPE

import constants
import utils
from utils import Tr


class Exporter:
    "DOCX exporter."

    def __init__(self, source, config):
        self.source = source
        self.config = config

    def write(self, filepath=None):
        if filepath is None:
            filepath = os.path.join(self.source.abspath, self.source.name + ".docx")
        self.document = docx.Document()

        # Set the default document-wide language.
        # See https://stackoverflow.com/questions/36967416/how-can-i-set-the-language-in-text-with-python-docx
        try:
            language = self.config["language"]
        except KeyError:
            pass
        else:
            styles_element = self.document.styles.element
            rpr_default = styles_element.xpath("./w:docDefaults/w:rPrDefault/w:rPr")[0]
            lang_default = rpr_default.xpath("w:lang")[0]
            lang_default.set(docx.oxml.shared.qn("w:val"), language)

        # Create a new style for quote.
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

        self.document.add_heading(self.config.get("title") or self.source.name, 0)
        for item in self.source.items:
            if item.is_section:
                self.write_section(item, level=1)
            else:
                self.write_text(item, level=1)
        self.document.save(filepath)

    def write_section(self, section, level):
        if level <= constants.DOCX_PAGEBREAK_LEVEL:
            self.document.add_page_break()
        self.document.add_heading(section.name, level)
        for item in section.items:
            if item.is_section:
                self.write_section(item, level=level + 1)
            else:
                self.write_text(item, level=level + 1)

    def write_text(self, text, level):
        if level < constants.DOCX_PAGEBREAK_LEVEL:
            self.document.add_page_break()
        self.document.add_heading(text.name, level)
        self.style_stack = ["Normal"]
        self.bold = False
        self.italic = False
        self.render(text.ast)

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
        label = tk.ttk.Label(body, text=Tr("Title"))
        label.grid(row=row, column=0, padx=4, sticky=tk.E)
        self.title_entry = tk.ttk.Entry(body, width=40)
        self.title_entry.insert(0, self.config.get("title") or self.source.name)
        self.title_entry.grid(row=row, column=1, sticky=tk.W)

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
        self.config["title"] = self.title_entry.get().strip()
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
