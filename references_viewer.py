"Viewer for the references list."

import os

from icecream import ic

import tkinter as tk

import constants
import utils
from base_viewer import BaseViewer


class ReferencesViewer(BaseViewer):
    "Viewer for the references list."

    def __init__(self, parent, main):
        super().__init__(parent, main)
        self.read()

    def __str__(self):
        return "References"

    def view_configure_tags(self, view=None):
        "Configure the key bindings used in the 'tk.Text' instance."
        if view is None:
            view = self.view
        super().view_configure_tags(view=view)
        view.tag_configure(constants.TITLE, font=constants.FONT_BOLD)

    def display(self):
        self.view.delete("1.0", tk.END)

    def read(self):
        dirpath = os.path.join(self.main.absdirpath, constants.REFERENCES_DIRNAME)
        if not os.path.exists(dirpath):
            os.mkdir(dirpath)
        for filename in os.listdir(dirpath):
            if not filename.endswith(constants.MARKDOWN_EXT):
                continue
            self.read_reference(filepath)

    def read_reference(self, filepath):
        raise NotImplementedError
