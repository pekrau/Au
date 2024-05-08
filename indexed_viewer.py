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
        if view is None:
            view = self.view
        super().view_configure_tags(view=view)
        view.tag_configure(constants.INDEXED,
                           font=constants.FONT_NORMAL,
                           spacing1=constants.INDEXED_SPACING)
        view.tag_configure(constants.LINK,
                           font=constants.FONT_SMALL,
                           foreground=constants.LINK_COLOR,
                           lmargin1=constants.INDEXED_INDENT,
                           underline=True)

    def display(self):
        self.view.delete("1.0", tk.END)
        self.links = dict()
        self.indexed = dict()   # Key: term; value: position in this view.
        self.highlighted = None # Currently highlighted range.
        texts_pos = dict()      # Position in source text; dict first, then sorted list.
        for text in self.main.source.all_texts:
            for term, positions in text.viewer.indexed.items():
                texts_pos.setdefault(term, dict())[text.fullname] = list(sorted(positions))
        texts_pos = sorted(texts_pos.items(), key=lambda i: i[0].lower())
        for term, fullnames in texts_pos:
            self.indexed[term] = self.view.index(tk.INSERT)
            self.view.insert(tk.INSERT, term + "\n", (constants.INDEXED, ))
            for fullname, positions in sorted(fullnames.items()):
                tag = f"{constants.LINK_PREFIX}{len(self.links) + 1}"
                self.view.insert(tk.INSERT, fullname, (constants.LINK, tag))
                positions = sorted(positions, key= lambda p: int(p[:p.index(".")]))
                self.links[tag] = (fullname, positions[0])
                for i, position in enumerate(positions[1:], start=2):
                    tag = f"{constants.LINK_PREFIX}{len(self.links) + 1}"
                    self.view.insert(tk.INSERT, ", ")
                    self.view.insert(tk.INSERT, str(i), (constants.LINK, tag))
                    self.links[tag] = (fullname, position)
                self.view.insert(tk.INSERT, "\n")

    def link_action(self, event):
        link = self.get_link()
        if not link:
            return
        fullname, position = link
        text = self.main.source[fullname]
        assert text.is_text
        self.main.texts_notebook.select(text.tabid)
        text.viewer.highlight(position, tag=constants.INDEXED)

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