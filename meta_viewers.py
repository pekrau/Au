"Meta content text viewers."

from icecream import ic

import tkinter as tk

import constants
import utils
from base_viewer import BaseViewer


class MetaViewer(BaseViewer):
    "Base class for meta contents viewers."

    def render(self):
        self.view.delete("1.0", tk.END)
        self.render_title()


class ReferencesViewer(MetaViewer):
    "View of the references list."

    def __str__(self):
        return "References"

    def render(self):
        super().render()


class IndexedViewer(MetaViewer):
    "View of the list of indexed terms."

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
                           

    def render(self):
        super().render()
        self.links = dict()
        indexed = dict()
        for text in self.main.source.all_texts:
            for term, positions in text.viewer.indexed.items():
                indexed.setdefault(term, dict())[text.fullname] = list(sorted(positions))
        for term, fullnames in sorted(indexed.items(), key=lambda i: i[0].lower()):
            mark = term.replace(" ", "_").replace(".", "_")
            self.view.mark_set(mark, tk.INSERT)
            self.view.insert(tk.INSERT, term + "\n", (constants.INDEXED, ))
            for fullname, positions in sorted(fullnames.items()):
                positions = sorted(positions, key= lambda p: int(p[:p.index(".")]))
                tag = f"{constants.LINK_PREFIX}{len(self.links) + 1}"
                self.view.insert(tk.INSERT, fullname, (constants.LINK, tag))
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
        self.main.texts_notebook_show(self.main.source[fullname], position=position)


class TodoViewer(MetaViewer):
    "View of the to-do list."

    def __str__(self):
        return "To do"

    def render(self):
        super().render()
