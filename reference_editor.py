"Reference editor; also to view abstract and notes."

from icecream import ic

import tkinter as tk
import tkinter.ttk

from text_editor import BaseEditor
from utils import Tr


class ReferenceEditor(BaseEditor):
    "Edit a reference."

    GENERAL_KEYS = ["title", "language", "year"]
    TYPE_KEYS = dict(book=["publisher", "pages", "isbn"],
                     article=["journal", "month", "volume", "number", "pages",
                              "issn", "doi", "pmid"])

    def __init__(self, main, text):
        self.main = main
        self.text = text
        self.toplevel_setup()
        self.menubar_setup()
        self.metadata_setup(self.toplevel)
        self.view_create(self.toplevel)
        self.view_configure_tags()
        self.view_configure_tag_bindings()
        self.view_bind_keys()
        self.render(self.text.ast)
        self.view.edit_modified(False)
        self.cursor_home()

    def close_finalize(self):
        "Perform action at window closing time."
        self.main.reference_editors.pop(self.text.fullname)
        self.text.read()

    def metadata_setup(self, parent):
        self.metadata_frame = tk.ttk.Frame(parent)
        self.metadata_frame.pack(fill=tk.BOTH, expand=True)
        self.metadata_frame.columnconfigure(1, weight=1)

        self.variables = dict()
        row = 0
        for key in self.GENERAL_KEYS:
            row += 1
            label = tk.Label(self.metadata_frame, text=Tr(key.capitalize()), padx=5)
            label.grid(row=row, column=0, sticky=tk.E)
            self.variables[key] = tk.StringVar(value=self.text.get(key, ""))
            entry = tk.Entry(self.metadata_frame, textvariable=self.variables[key])
            entry.grid(row=row, column=1, sticky=(tk.W, tk.E))

        row += 1
        label = tk.Label(self.metadata_frame, text=Tr("Authors"), padx=5)
        label.grid(row=row, column=0, sticky=tk.E)
        for pos, author in enumerate(self.text["authors"]):
            key = f"author {pos}"
            self.variables[key] = tk.StringVar(value=self.text["authors"][pos])
            entry = tk.Entry(self.metadata_frame, textvariable=self.variables[key])
            entry.grid(row=row, column=1, sticky=(tk.W, tk.E))
            row += 1

        label = tk.Label(self.metadata_frame, text=Tr("Add author"), padx=5)
        label.grid(row=row, column=0, sticky=tk.E)
        key = "author x"
        self.variables[key] = tk.StringVar()
        entry = tk.Entry(self.metadata_frame, textvariable=self.variables[key])
        entry.grid(row=row, column=1, sticky=(tk.W, tk.E))

        for key in self.TYPE_KEYS.get(self.text["type"], []):
            row += 1
            label = tk.Label(self.metadata_frame, text=Tr(key.capitalize()), padx=5)
            label.grid(row=row, column=0, sticky=tk.E)
            self.variables[key] = tk.StringVar(value=self.text.get(key, ""))
            entry = tk.Entry(self.metadata_frame, textvariable=self.variables[key])
            entry.grid(row=row, column=1, sticky=(tk.W, tk.E))

    def save_prepare(self):
        "Prepare for saving; before doing dump-to-Markdown."
        super().save_prepare()
        for key in self.GENERAL_KEYS:
            self.text[key] = self.variables[key].get()
        for key in self.TYPE_KEYS.get(self.text["type"], []):
            self.text[key] = self.variables[key].get()
