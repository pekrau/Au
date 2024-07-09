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
        self.viewer = viewer
        super().__init__(main, text)

    def menubar_create(self):
        super().menubar_create()
        state = self.text.get("orphan") and tk.NORMAL or tk.DISABLED
        self.menu_file.insert_command(
            0, label=Tr("Delete"), state=state, command=self.delete
        )

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

    def close_finalize(self):
        "Perform action at window closing time."
        self.main.reference_editors.pop(self.text.fullname)
        self.text.read()
