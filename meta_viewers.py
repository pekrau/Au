"Meta content text viewers."

from icecream import ic

import tkinter as tk

import constants
import utils
from base_text import TextMixin
from text_viewer import BaseTextViewer


class MetaViewer(TextMixin):
    "Base class for meta contents viewers."

    def __init__(self, parent, main):
        self.main = main
        self.text_setup(parent)
        self.text_configure_tags()
        self.text.insert(tk.INSERT, str(self), constants.TITLE)
        self.text.insert(tk.INSERT, "\n\n")


class ReferencesViewer(MetaViewer):
    "View of the references list."

    def __str__(self):
        return "References"


class IndexedViewer(MetaViewer):
    "View of the list of indexed terms."

    def __init__(self, parent, main):
        super().__init__(parent, main)

    def __str__(self):
        return "Indexed"

    def render(self):
        self.text.delete("1.0", tk.END)
        indexed = dict()
        for filepath, text in self.main.texts.items():
            try:
                viewer = text["viewer"]
            except KeyError:
                pass
            else:
                for term, positions in viewer.indexed.items():
                    indexed.setdefault(term, dict())[filepath] = positions
        for term, textrefs in sorted(indexed.items()):
            self.text.insert(tk.INSERT, term + "\n", (constants.BOLD, ))
            for filepath, positions in sorted(textrefs.items()):
                self.text.insert(tk.INSERT, f"  {filepath}  ")
                self.text.insert(tk.INSERT, ", ".join([str(p) for p in positions]))
                self.text.insert(tk.INSERT, "\n")


class TodoViewer(MetaViewer):
    "View of the to-do list."

    def __str__(self):
        return "To do"


class HelpViewer(BaseTextViewer):
    "View of the help file Markdown contents."

    def __init__(self, parent, main, filepath):
        super().__init__(parent, main, filepath,
                         title="Au " + ".".join([str(n) for n in constants.VERSION]))

    def __str__(self):
        return "Help"
