"View of the help file Markdown contents."

from icecream import ic

import tkinter as tk

import constants
from base_viewer import TextViewer


class HelpViewer(TextViewer):
    "View of the help file Markdown contents."

    def __init__(self, parent, main):
        super().__init__(parent, main, main.help_source["hotkeys"])

    def __str__(self):
        return "Help"

    def display_title(self):
        title = "Au " + ".".join([str(n) for n in constants.VERSION])
        self.view.insert(tk.INSERT, title, constants.TITLE)
        self.view.insert(tk.INSERT, "\n\n")
