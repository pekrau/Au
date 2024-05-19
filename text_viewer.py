"Viewer window for Markdown text file."

from icecream import ic

import tkinter as tk

import constants
import utils
from render_mixin import RenderMixin
from base_viewer import BaseTextViewer


class TextViewer(BaseTextViewer):
    "Viewer window for Markdown text file."

    TEXT_COLOR = constants.TEXT_COLOR

    def __init__(self, parent, main, text):
        self.footnotes = {}  # Lookup local for the instance.
        super().__init__(parent, main, text)
        self.status = (
            constants.Status.lookup(self.text.frontmatter.get("status"))
            or constants.STARTED
        )

    def view_configure_tags(self, view=None):
        view = view or self.view
        super().view_configure_tags(view=view)
        view.tag_configure(
            constants.FOOTNOTE_REF,
            foreground=constants.FOOTNOTE_REF_COLOR,
            underline=True,
        )
        view.tag_configure(
            constants.FOOTNOTE_DEF,
            background=constants.FOOTNOTE_DEF_COLOR,
            borderwidth=1,
            relief=tk.SOLID,
            lmargin1=constants.FOOTNOTE_MARGIN,
            lmargin2=constants.FOOTNOTE_MARGIN,
            rmargin=constants.FOOTNOTE_MARGIN,
        )

    def view_bind_tags(self, view=None):
        view = view or self.view
        super().view_bind_tags(view=view)
        view.tag_bind(constants.FOOTNOTE_REF, "<Enter>", self.footnote_enter)
        view.tag_bind(constants.FOOTNOTE_REF, "<Leave>", self.footnote_leave)

    def display_wipe(self):
        super().display_wipe()
        self.footnotes = {}

    def footnote_enter(self, event=None):
        self.view.configure(cursor="hand2")

    def footnote_leave(self, event=None):
        self.view.configure(cursor="")

    def footnote_toggle(self, event=None):
        for tag in self.view.tag_names(tk.CURRENT):
            if tag.startswith(constants.FOOTNOTE_REF_PREFIX):
                label = tag[len(constants.FOOTNOTE_REF_PREFIX) :]
                break
        else:
            return
        self.tag_toggle_elide(constants.FOOTNOTE_DEF_PREFIX + label)
