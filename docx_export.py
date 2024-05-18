"DOCX export."

from icecream import ic

import copy
import os.path

import docx
import tkinter as tk
import tkinter.simpledialog
import tkinter.filedialog

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
        self.document.add_heading(self.config.get("title") or self.source.name, 0)
        for item in self.source.items:
            if item.is_section:
                self.write_section(item, level=0)
            else:
                self.write_text(item, level=0)
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
        for child in ast["children"]:
            self.render(child)

    def render_raw_text(self, ast):
        line = ast["children"]
        if line[-1] == "\n":
            line[-1] = " "
        self.paragraph.add_run(line)

    def render_blank_line(self, ast):
        pass


class Dialog(tk.simpledialog.Dialog):
    "Dialog to confirm or modify configuration before export."

    def __init__(self, master, config):
        self.config = copy.deepcopy(config)
        self.result = None
        super().__init__(master, title="DOCX export")

    def body(self, body):
        label = tk.ttk.Label(body, text="Filename")
        label.grid(row=0, column=0, padx=4, sticky=tk.E)
        self.filename_entry = tk.ttk.Entry(body, width=40)
        self.filename_entry.insert(0, self.config.get("filename") or "")
        self.filename_entry.grid(row=0, column=1, sticky=tk.W)

        label = tk.ttk.Label(body, text="Directory")
        label.grid(row=1, column=0, padx=4, sticky=tk.E)
        self.dirpath_entry = tk.ttk.Entry(body, width=40)
        self.dirpath_entry.insert(0, self.config.get("dirpath") or "")
        self.dirpath_entry.grid(row=1, column=1, sticky=tk.W)
        button = tk.ttk.Button(body, text=Tr("Choose"), command=self.change_dirpath)
        button.grid(row=1, column=3)

    def apply(self):
        self.config["dirpath"] = self.dirpath_entry.get().strip() or "."
        filename = self.filename_entry.get().strip() or constants.BOOK
        self.config["filename"] = os.path.splitext(filename)[0] + ".docx"
        self.result = self.config

    def change_dirpath(self):
        dirpath = tk.filedialog.askdirectory(
            parent=self,
            title="Directory",
            initialdir=self.config.get("dirpath") or ".",
            mustexist=True,
        )
        if dirpath:
            self.dirpath_entry.delete(0, tk.END)
            self.dirpath_entry.insert(0, dirpath)
