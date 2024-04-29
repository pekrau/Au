"Text viewer window."

from icecream import ic

import webbrowser

import tkinter as tk
from tkinter import ttk

import constants
import utils
from render_mixins import FootnoteRenderMixin
from base_text import BaseTextContainer, TextMixin


class BaseTextViewer(TextMixin, BaseTextContainer):
    "Base text viewer window."

    def __init__(self, parent, main, filepath, title=None):
        super().__init__(main, filepath, title=title)
        self.text_create(parent)
        self.text_configure_tags()
        self.text_configure_tag_bindings()
        self.text_bind_keys()
        self.render_title()
        self.render(self.ast)

    def key_press(self, event):
        "Stop modifying actions."
        if event.char in constants.AFFECTS_CHARACTER_COUNT:
            return "break"

    def link_action(self, event):
        link = self.get_link()
        if link:
            webbrowser.open_new_tab(link["url"])


class TextViewer(FootnoteRenderMixin, BaseTextViewer):
    "Text viewer of Markdown contents."

    TEXT_COLOR = constants.TEXT_COLOR

    def __init__(self, parent, main, filepath, title=None):
        self.footnotes = dict()     # Lookup local for the instance.
        super().__init__(parent, main, filepath, title=title)
        self.status = constants.Status.lookup(self.frontmatter.get("status")) or constants.STARTED

    def text_configure_tags(self, text=None):
        if text is None:
            text = self.text
        super().text_configure_tags(text=text)
        text.tag_configure(constants.FOOTNOTE_REF,
                           foreground=constants.FOOTNOTE_REF_COLOR,
                           underline=True)
        text.tag_configure(constants.FOOTNOTE_DEF,
                           background=constants.FOOTNOTE_DEF_COLOR,
                           borderwidth=1,
                           relief=tk.SOLID,
                           lmargin1=constants.FOOTNOTE_MARGIN,
                           lmargin2=constants.FOOTNOTE_MARGIN,
                           rmargin=constants.FOOTNOTE_MARGIN)

    def text_configure_tag_bindings(self, text=None):
        if text is None:
            text = self.text
        super().text_configure_tag_bindings(text=text)
        text.tag_bind(constants.FOOTNOTE_REF, "<Enter>", self.footnote_enter)
        text.tag_bind(constants.FOOTNOTE_REF, "<Leave>", self.footnote_leave)

    def rerender(self):
        self.footnotes = dict()
        super().rerender()

    def footnote_enter(self, event=None):
        self.text.configure(cursor="hand2")

    def footnote_leave(self, event=None):
        self.text.configure(cursor="")

    def footnote_toggle(self, event=None):
        for tag in self.text.tag_names(tk.CURRENT):
            if tag.startswith(constants.FOOTNOTE_REF_PREFIX):
                label = tag[len(constants.FOOTNOTE_REF_PREFIX):]
                break
        else:
            return
        tag = constants.FOOTNOTE_DEF_PREFIX + label
        elided = bool(int(self.text.tag_cget(tag, "elide")))
        self.text.tag_configure(tag, elide=not elided)
