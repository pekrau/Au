"Meta content text viewers."

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
    "Viewer of the references list."

    def __str__(self):
        return "References"


class IndexedViewer(MetaViewer):
    "Viewer of the list of indexed terms."

    def __init__(self, parent, main):
        super().__init__(parent, main)
        self.indexed = {}       # Key: term; value: dict(textfilepath, position)

    def __str__(self):
        return "Indexed"

    def add(self, term, text, position):
        textrefs = self.indexed.setdefault(term, dict())
        textrefs.setdefault(text.filepath, set()).add(position)

    def clear(self, text):
        "Remove all indexed terms that refer to the given text."
        for textref in self.indexed.values():
            textref.pop(text.filepath, None)

    def render(self):
        self.text.delete("1.0", tk.END)
        for term, textrefs in sorted(self.indexed.items()):
            self.text.insert(tk.INSERT, term + "\n")


class TodoViewer(MetaViewer):
    "Viewer of the to-do list."

    def __str__(self):
        return "To do"


class HelpViewer(BaseTextViewer):
    "Viewer of Markdown contents of the help file."

    def __init__(self, parent, main, filepath):
        super().__init__(parent, main, filepath,
                         title="Au " + ".".join([str(n) for n in constants.VERSION]))

    def __str__(self):
        return "Help"
