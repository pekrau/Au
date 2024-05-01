"Viewer window for Markdown text file."

from icecream import ic

import webbrowser

import tkinter as tk
from tkinter import ttk

import constants
import utils
from render_mixins import FootnoteRenderMixin
from base_viewer import ViewMixin, BaseViewContainer


class BaseViewer(ViewMixin, BaseViewContainer):
    "Base viewer window."

    def __init__(self, parent, main, text, title=None):
        super().__init__(main, text, title=title)
        self.view_create(parent)
        self.view_configure_tags()
        self.view_configure_tag_bindings()
        self.view_bind_keys()
        self.render_title()
        self.render(self.text.ast)

    def key_press(self, event):
        "Stop modifying actions."
        if event.char in constants.AFFECTS_CHARACTER_COUNT:
            return "break"

    def link_action(self, event):
        link = self.get_link()
        if link:
            webbrowser.open_new_tab(link["url"])


class Viewer(FootnoteRenderMixin, BaseViewer):
    "Viewer window for Markdown text file."

    TEXT_COLOR = constants.TEXT_COLOR

    def __init__(self, parent, main, text, title=None):
        self.footnotes = dict()     # Lookup local for the instance.
        super().__init__(parent, main, text, title=title)
        self.status = constants.Status.lookup(self.text.frontmatter.get("status")) or constants.STARTED

    def view_configure_tags(self, view=None):
        if view is None:
            view = self.view
        super().view_configure_tags(view=view)
        view.tag_configure(constants.FOOTNOTE_REF,
                           foreground=constants.FOOTNOTE_REF_COLOR,
                           underline=True)
        view.tag_configure(constants.FOOTNOTE_DEF,
                           background=constants.FOOTNOTE_DEF_COLOR,
                           borderwidth=1,
                           relief=tk.SOLID,
                           lmargin1=constants.FOOTNOTE_MARGIN,
                           lmargin2=constants.FOOTNOTE_MARGIN,
                           rmargin=constants.FOOTNOTE_MARGIN)

    def view_configure_tag_bindings(self, view=None):
        if view is None:
            view = self.view
        super().view_configure_tag_bindings(view=view)
        view.tag_bind(constants.FOOTNOTE_REF, "<Enter>", self.footnote_enter)
        view.tag_bind(constants.FOOTNOTE_REF, "<Leave>", self.footnote_leave)

    def rerender(self):
        self.footnotes = dict()
        super().rerender()

    def footnote_enter(self, event=None):
        self.view.configure(cursor="hand2")

    def footnote_leave(self, event=None):
        self.view.configure(cursor="")

    def footnote_toggle(self, event=None):
        for tag in self.view.tag_names(tk.CURRENT):
            if tag.startswith(constants.FOOTNOTE_REF_PREFIX):
                label = tag[len(constants.FOOTNOTE_REF_PREFIX):]
                break
        else:
            return
        tag = constants.FOOTNOTE_DEF_PREFIX + label
        elided = bool(int(self.view.tag_cget(tag, "elide")))
        self.view.tag_configure(tag, elide=not elided)
