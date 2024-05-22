"View of the help file Markdown contents."

import tkinter as tk

from icecream import ic

import constants

from text_viewer import Viewer


class HelpViewer(Viewer):
    "View of the help file Markdown contents."

    def __str__(self):
        return "Help"

    def display_title(self):
        title = "Au " + ".".join([str(n) for n in constants.VERSION])
        self.view.insert(tk.INSERT, title + "\n", (constants.H1["tag"],))

    def display_view(self):
        for text in self.main.help_source.all_texts:
            tag = constants.H_LOOKUP[text.depth + 1]["tag"]
            self.view.insert(tk.INSERT, text.name + "\n", (tag,))
            self.render(text.ast)
