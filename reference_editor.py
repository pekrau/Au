"Reference editor; also for viewing abstract and notes."

from icecream import ic

import functools

import tkinter as tk
import tkinter.ttk

import constants
import utils

from editor import Editor
from utils import Tr


class ReferenceEditor(Editor):
    "Edit a reference."

    def __init__(self, main, viewer, text):
        self.main = main
        self.viewer = viewer
        self.text = text
        self.toplevel_create(main, text)
        self.menubar_create()
        self.metadata_create(self.toplevel)
        self.metadata_display()
        self.view_create(self.toplevel)
        self.configure_tags()
        self.bind_tags()
        self.bind_events()

    def menubar_create(self):
        super().menubar_create()
        state = self.text.get("orphan") and tk.NORMAL or tk.DISABLED
        self.menu_file.insert_command(
            0, label=Tr("Delete"), state=state, command=self.delete
        )

    def metadata_create(self, parent):
        self.metadata_frame = tk.ttk.Frame(parent)
        self.metadata_frame.pack(fill=tk.BOTH, expand=True)
        self.metadata_frame.columnconfigure(1, weight=1)
        self.authors = list(self.text["authors"])

    def metadata_display(self):
        "Create entry fields for the given reference."
        for item in self.metadata_frame.grid_slaves():
            item.grid_forget()
        self.variables = {}
        row = 0
        for key in constants.REFERENCE_GENERAL_KEYS:
            row += 1
            label = tk.Label(self.metadata_frame, text=Tr(key.capitalize()), padx=4)
            label.grid(row=row, column=0, sticky=tk.E)
            self.variables[key] = tk.StringVar(value=self.text.get(key) or "")
            # Special case for language field.
            if key == "language":
                entry = tk.ttk.Combobox(
                    self.metadata_frame,
                    values=constants.DEFAULT_LANGUAGES,
                    textvariable=self.variables[key],
                )
            else:
                entry = tk.ttk.Entry(
                    self.metadata_frame, textvariable=self.variables[key]
                )
            entry.grid(row=row, column=1, sticky=(tk.W, tk.E))
            entry.bind("<Key>", self.entry_modified)
            entry.bind("<Control-q>", self.close)
            entry.bind("<Control-Q>", self.close)

        # Special case for authors field.
        row += 1
        label = tk.Label(self.metadata_frame, text=Tr("Authors"), padx=4)
        label.grid(row=row, column=0, sticky=tk.E)
        for pos, author in enumerate(self.authors):
            key = f"author {pos}"
            self.variables[key] = tk.StringVar(value=self.authors[pos])
            entry = tk.ttk.Entry(self.metadata_frame, textvariable=self.variables[key])
            entry.grid(row=row, column=1, sticky=(tk.W, tk.E))
            entry.bind("<Key>", self.entry_modified)
            entry.bind("<Control-q>", self.close)
            entry.bind("<Control-Q>", self.close)
            if pos > 0:
                button = tk.Button(
                    self.metadata_frame,
                    text=Tr("Remove"),
                    command=functools.partial(self.remove_author, pos=pos),
                )
                button.grid(row=row, column=2)
            row += 1

        key = "author"
        self.variables[key] = tk.StringVar()
        entry = tk.ttk.Entry(self.metadata_frame, textvariable=self.variables[key])
        entry.grid(row=row, column=1, sticky=(tk.W, tk.E))
        entry.bind("<Return>", self.add_author)
        entry.bind("<Key>", self.entry_modified)
        button = tk.Button(self.metadata_frame, text=Tr("Add"), command=self.add_author)
        button.grid(row=row, column=2)

        for key in constants.REFERENCE_TYPE_KEYS[self.text["type"]]:
            row += 1
            label = tk.Label(self.metadata_frame, text=Tr(key.capitalize()), padx=4)
            label.grid(row=row, column=0, sticky=tk.E)
            self.variables[key] = tk.StringVar(value=self.text.get(key) or "")
            entry = tk.ttk.Entry(self.metadata_frame, textvariable=self.variables[key])
            entry.grid(row=row, column=1, sticky=(tk.W, tk.E))
            entry.bind("<Key>", self.entry_modified)
            entry.bind("<Control-q>", self.close)
            entry.bind("<Control-Q>", self.close)

    def entry_modified(self, event):
        if not self.modified and event.char:
            self.view.edit_modified(True)
            self.view.event_generate("<<Modified>>")

    def delete(self):
        if not tk.messagebox.askokcancel(
            parent=self.frame,
            title=Tr("Delete"),
            message=Tr("Really delete reference") + "?",
        ):
            return
        self.viewer.references.remove(self.text)
        self.viewer.references_lookup.pop(self.text["id"])
        self.main.reference_editors.pop(self.text.fullname)
        self.text.delete()
        self.viewer.display()
        self.toplevel.destroy()

    def save_prepare(self):
        "Prepare for saving; before doing dump-to-Markdown."
        super().save_prepare()
        for key in constants.REFERENCE_GENERAL_KEYS:
            value = self.variables[key].get().strip()
            if value:
                self.text[key] = value
            else:
                self.text.pop(key)
        self.text["authors"] = self.authors
        for key in constants.REFERENCE_TYPE_KEYS[self.text["type"]]:
            value = self.variables[key].get().strip()
            if value:
                self.text[key] = value
            else:
                self.text.pop(key)

    def save_finalize(self):
        self.main.references_viewer.display()

    def close_finalize(self):
        "Perform action at window closing time."
        self.main.reference_editors.pop(self.text.fullname)
        self.text.read()

    def add_author(self, event=None):
        name = self.variables["author"].get().strip()
        if not name:
            return
        self.authors.append(name)
        self.view.edit_modified(True)
        self.metadata_display()

    def remove_author(self, pos):
        try:
            self.authors.pop(pos)
        except IndexError:
            return
        self.view.edit_modified(True)
        self.metadata_display()
