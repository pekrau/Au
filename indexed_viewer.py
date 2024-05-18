"Viewer for the list of indexed terms."

from icecream import ic

import tkinter as tk

import constants
import utils
from base_viewer import BaseViewer


class IndexedViewer(BaseViewer):
    "Viewer for the list of indexed terms."

    def __str__(self):
        return "Indexed"

    def view_configure_tags(self, view=None):
        "Configure the key bindings used in the 'tk.Text' instance."
        view = view or self.view
        super().view_configure_tags(view=view)
        view.tag_configure(
            constants.INDEXED,
            font=constants.FONT_NORMAL,
            spacing1=constants.INDEXED_SPACING,
        )
        view.tag_configure(
            constants.XREF,
            font=constants.FONT_SMALL,
            foreground=constants.XREF_COLOR,
            lmargin1=constants.INDEXED_INDENT,
            lmargin2=constants.INDEXED_INDENT,
            underline=True,
        )

    def display(self):
        self.display_wipe()
        self.indexed = {}  # Key: term; value: position in this view.
        pos = {}  # Position in source text.
        for text in self.main.source.all_texts:
            for term, positions in text.viewer.indexed.items():
                pos.setdefault(term, {})[text.fullname] = list(sorted(positions))
        texts_pos = sorted(pos.items(), key=lambda i: i[0].lower())
        for term, fullnames in texts_pos:
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

        # This is already displayed, so needs to be updated.
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
