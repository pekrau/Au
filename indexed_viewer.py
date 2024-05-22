"Viewer for the list of indexed terms."

import tkinter as tk

from icecream import ic

import constants
import utils

from viewer import Viewer


class IndexedViewer(Viewer):
    "Viewer for the list of indexed terms."

    def __str__(self):
        return "Indexed"

    def configure_tags(self):
        "Reconfigure some tags."
        super().configure_tags()
        self.view.tag_configure(
            constants.INDEXED,
            spacing1=constants.INDEXED_SPACING,
            font=constants.INDEXED_FONT,
            underline=False,
        )
        self.view.tag_configure(
            constants.XREF,
            lmargin1=constants.INDEXED_INDENT,
            font=constants.INDEXED_XREF_FONT,
        )

    def display_initialize(self):
        super().display_initialize()
        self.indexed = {}  # Key: term; value: position in this view.
        # Gather positions of indexed terms in source texts.
        pos = {}
        for text in self.main.source.all_texts:
            for term, positions in text.viewer.indexed.items():
                pos.setdefault(term, {})[text.fullname] = list(sorted(positions))
        self.terms = sorted(pos.items(), key=lambda i: i[0].lower())

    def display_title(self):
        pass

    def display_view(self):
        for term, fullnames in self.terms:
            self.indexed[term] = self.view.index(tk.INSERT)
            self.view.insert(tk.INSERT, term, (constants.INDEXED,))
            for fullname, positions in sorted(fullnames.items()):
                self.view.insert(tk.INSERT, "\n")
                positions = sorted(positions, key=lambda p: int(p[: p.index(".")]))
                self.xref_create(fullname, positions[0], constants.INDEXED)
                for i, position in enumerate(positions[1:], start=2):
                    self.view.insert(tk.INSERT, ", ")
                    self.xref_create(
                        fullname, position, constants.INDEXED, label=str(i)
                    )
                self.view.insert(tk.INSERT, "\n")

    def display_finalize(self):
        super().display_finalize()
        # This is already displayed in the statistics table; needs to be updated.
        self.main.title_viewer.indexed_var.set(len(self.indexed))

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
