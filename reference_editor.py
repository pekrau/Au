"Reference editor; also to view abstract and notes."

from icecream import ic

import functools

import tkinter as tk
import tkinter.ttk

from text_editor import BaseEditor
from utils import Tr


class ReferenceEditor(BaseEditor):
    "Edit a reference."

    GENERAL_KEYS = ["title", "language", "year"]
    TYPE_KEYS = dict(book=["publisher", "pages", "isbn"],
                     article=["journal", "month", "volume", "number", "pages",
                              "issn", "doi", "pmid"],
                     link=["url", "title", "accessed"])

    def __init__(self, main, text):
        self.main = main
        self.text = text
        self.toplevel_setup()
        self.menubar_setup()
        self.metadata_create(self.toplevel)
        if self.text is None:
            self.metadata_new()
        else:
            self.metadata_populate()
        self.view_create(self.toplevel)
        self.view_configure_tags()
        self.view_configure_tag_bindings()
        self.view_bind_keys()
        if self.text is not None:
            self.render(self.text.ast)
        self.view.edit_modified(False)
        self.cursor_home()

    def metadata_create(self, parent):
        self.metadata_frame = tk.ttk.Frame(parent)
        self.metadata_frame.pack(fill=tk.BOTH, expand=True)
        self.metadata_frame.columnconfigure(1, weight=1)
        if self.text is None:
            self.authors = list()
        else:
            self.authors = list(self.text["authors"])

    def metadata_populate(self):
        "Output entry fields for the given reference."
        for item in self.metadata_frame.grid_slaves():
            item.grid_forget()
        self.variables = dict()
        row = 0
        for key in self.GENERAL_KEYS:
            row += 1
            label = tk.Label(self.metadata_frame, text=Tr(key.capitalize()), padx=4)
            label.grid(row=row, column=0, sticky=tk.E)
            self.variables[key] = tk.StringVar(value=self.text.get(key, ""))
            entry = tk.Entry(self.metadata_frame, textvariable=self.variables[key])
            entry.grid(row=row, column=1, sticky=(tk.W, tk.E))

        row += 1
        label = tk.Label(self.metadata_frame, text=Tr("Authors"), padx=4)
        label.grid(row=row, column=0, sticky=tk.E)
        for pos, author in enumerate(self.authors):
            key = f"author {pos}"
            self.variables[key] = tk.StringVar(value=self.authors[pos])
            entry = tk.Entry(self.metadata_frame, textvariable=self.variables[key])
            entry.grid(row=row, column=1, sticky=(tk.W, tk.E))
            button = tk.Button(self.metadata_frame, text=Tr("Remove"),
                               command=functools.partial(self.remove_author, pos=pos))
            button.grid(row=row, column=2)
            row += 1

        key = "author"
        self.variables[key] = tk.StringVar()
        entry = tk.Entry(self.metadata_frame, textvariable=self.variables[key])
        entry.grid(row=row, column=1, sticky=(tk.W, tk.E))
        entry.bind("<Return>", self.add_author)
        button = tk.Button(self.metadata_frame, text=Tr("Add"), command=self.add_author)
        button.grid(row=row, column=2)

        for key in self.TYPE_KEYS.get(self.text["type"], []):
            row += 1
            label = tk.Label(self.metadata_frame, text=Tr(key.capitalize()), padx=4)
            label.grid(row=row, column=0, sticky=tk.E)
            self.variables[key] = tk.StringVar(value=self.text.get(key, ""))
            entry = tk.ttk.Entry(self.metadata_frame, 
                                 textvariable=self.variables[key])
            entry.grid(row=row, column=1, sticky=(tk.W, tk.E))

    def metadata_new(self):
        "Output fields for a new reference."
        self.variables = dict()
        row = 0
        label = tk.Label(self.metadata_frame, text=Tr("First author"), padx=4)
        label.grid(row=row, column=0, sticky=tk.E)
        key = "author"
        self.variables[key] = tk.StringVar()
        entry = tk.Entry(self.metadata_frame, textvariable=self.variables[key])
        entry.grid(row=row, column=1, sticky=(tk.W, tk.E))

        label = tk.Label(self.metadata_frame, text=Tr("Year"), padx=4)
        label.grid(row=row, column=0, sticky=tk.E)
        self.variables["year"] = tk.StringVar()
        entry = tk.Entry(self.metadata_frame, textvariable=self.variables["year"])
        entry.grid(row=row, column=1, sticky=(tk.W, tk.E))

        row += 1
        label = tk.Label(self.metadata_frame, text=Tr("Type"), padx=4)
        label.grid(row=row, column=0, sticky=tk.E)
        frame = tk.Frame(self.metadata_frame)
        frame.grid(row=row, column=1, sticky=(tk.W, tk.E))
        self.variables["type"] = var = tk.StringVar(value="Article")
        tk.ttk.Radiobutton(frame, text=Tr("Article"), variable=var).pack()
        tk.ttk.Radiobutton(frame, text=Tr("Book"), variable=var).pack()
        tk.ttk.Radiobutton(frame, text=Tr("Link"), variable=var).pack()

    def save_prepare(self):
        "Prepare for saving; before doing dump-to-Markdown."
        super().save_prepare()
        if self.text is None:
            author = self.variables["author"].get()
            year = self.variables["year"].get()
            type = self.variables["type"].get()
            # XXX
        else:
            for key in self.GENERAL_KEYS:
                self.text[key] = self.variables[key].get()
            self.text["authors"] = self.authors
            for key in self.TYPE_KEYS.get(self.text["type"], []):
                self.text[key] = self.variables[key].get()

    def save_finalize(self):
        self.main.references_viewer.display()

    def add_author(self, event=None):
        name = self.variables["author"].get().strip()
        if not name:
            return
        self.authors.append(name)
        self.view.edit_modified(True)
        self.metadata_populate()

    def remove_author(self, pos):
        try:
            self.authors.pop(pos)
        except IndexError:
            return
        self.view.edit_modified(True)
        self.metadata_populate()

    def close_finalize(self):
        "Perform action at window closing time."
        self.main.reference_editors.pop(self.text.fullname)
        self.text.read()
