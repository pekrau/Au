"Meta content text viewers."

from icecream import ic

import tkinter as tk

import constants
import utils
from base_viewer import BaseViewer


class MetaViewer(BaseViewer):
    "Base class for meta contents viewers."

    def display(self):
        self.view.delete("1.0", tk.END)
        self.display_title()


class ReferencesViewer(MetaViewer):
    "View of the references list."

    def __str__(self):
        return "References"


class TodoViewer(MetaViewer):
    "View of the to-do list."

    def __str__(self):
        return "To do"
