"View of the help file Markdown contents."

from icecream import ic

import tkinter as tk

import constants
from base_viewer import BaseTextViewer


class HelpViewer(BaseTextViewer):
    "View of the help file Markdown contents."

    def __init__(self, parent, main):
        super().__init__(parent, main, main.help_source["hotkeys"])

    def __str__(self):
        return "Help"

    def display_title(self):
        title = "Au " + ".".join([str(n) for n in constants.VERSION])
        self.view.insert(tk.INSERT, title + "\n", (constants.H1["tag"], ))
