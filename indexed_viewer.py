"Viewer for the list of indexed terms."

from icecream import ic

import tkinter as tk

import constants
import utils

from viewer import Viewer


class IndexedViewer(Viewer):
    "Viewer for the list of indexed terms."

    # self.main.indexed_viewer.display() XXX listen to event instead

    def __str__(self):
        return "Indexed"

    def display(self):
        self.display_clear()

        # Gather positions of indexed terms in source texts.
        pos = {}
        for text in self.main.source.all_texts:
            for term, positions in text.viewer.indexed.items():
                pos.setdefault(term, {})[text.fullname] = list(sorted(positions))

        for term, fullnames in sorted(pos.items(), key=lambda i: i[0].lower()):
            self.indexed[term] = self.view.index(tk.INSERT)
            self.view.insert(tk.INSERT, term, (constants.INDEXED,))
            for fullname, positions in sorted(fullnames.items()):
                self.view.insert(tk.INSERT, "\n")
                positions = sorted(positions, key=lambda p: int(p[: p.index(".")]))
                self.xref_create(fullname, positions[0], constants.INDEXED)
                for i, position in enumerate(positions[1:], start=2):
                    self.view.insert(tk.INSERT, ", ")
                    self.xref_create(str(i), position, constants.INDEXED)
                self.view.insert(tk.INSERT, "\n")

        # This is already displayed in the statistics table; needs to be updated.
        self.main.title_viewer.indexed_var.set(len(self.indexed))

    def display_clear(self):
        super().display_clear()
        self.indexed = {}  # Key: term; value: position in this view.

    def highlight(self, term):
        "Highlight and show the indexed term; show this pane."
        try:
            first = self.indexed[term]
        except KeyError:
            pass
        else:
            if self.highlighted:
                self.view.tag_remove(constants.HIGHLIGHT, *self.highlighted)
            last = self.view.index(first + " lineend")
            self.view.tag_add(constants.HIGHLIGHT, first, last)
            self.highlighted = (first, last)
            self.view.see(first)
            self.main.meta_notebook.select(self.tabid)
