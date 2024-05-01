"Meta content text viewers."

from icecream import ic

import tkinter as tk

import constants
import utils
from source import Source
from base_viewer import BaseViewer


class MetaViewer(BaseViewer):
    "Base class for meta contents viewers."

    def __init__(self, parent, main):
        self.main = main
        self.text_create(parent)
        self.text_configure_tags()


class ReferencesViewer(MetaViewer):
    "View of the references list."

    def __str__(self):
        return "References"

    def render(self):
        self.text.delete("1.0", tk.END)
        self.render_title()


# class IndexedViewer(MetaViewer):
#     "View of the list of indexed terms."

#     def __init__(self, parent, main):
#         super().__init__(parent, main)

#     def __str__(self):
#         return "Indexed"

#     def render(self):
#         self.text.delete("1.0", tk.END)
#         self.set_title()
#         indexed = dict()
#         for filepath, text in self.main.texts.items():
#             try:
#                 viewer = text["viewer"]
#             except KeyError:
#                 pass
#             else:
#                 for term, positions in viewer.indexed.items():
#                     indexed.setdefault(term, dict())[filepath] = positions
#         for term, textrefs in sorted(indexed.items()):
#             self.text.insert(tk.INSERT, term + "\n", (constants.BOLD, ))
#             for filepath, positions in sorted(textrefs.items()):
#                 self.text.insert(tk.INSERT, f"  {filepath}  ")
#                 self.text.insert(tk.INSERT, ", ".join([str(p) for p in positions]))
#                 self.text.insert(tk.INSERT, "\n")


# class TodoViewer(MetaViewer):
#     "View of the to-do list."

#     def __str__(self):
#         return "To do"

#     def render(self):
#         self.text.delete("1.0", tk.END)
#         self.set_title()


class HelpViewer(BaseViewer):
    "View of the help file Markdown contents."

    def __init__(self, parent, main):
        super().__init__(parent, main, main.help["hotkeys"])

    def __str__(self):
        return "Help"

    def render_title(self):
        title = "Au " + ".".join([str(n) for n in constants.VERSION])
        self.view.insert(tk.INSERT, title, constants.TITLE)
        self.view.insert(tk.INSERT, "\n\n")
