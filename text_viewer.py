"Text viewer window classes."

from icecream import ic

import webbrowser

import tkinter as tk
from tkinter import ttk

import constants
import utils
from base_text import BaseText


class BaseTextViewer(BaseText):
    "Base text viewer window."

    def __init__(self, parent, main, filepath, title=None):
        super().__init__(main, filepath)
        self.setup_text(parent)
        if title:
            self.render_title(title)
        self.render(self.ast)

    def render_title(self, title):
        self.text.insert(tk.INSERT, title, constants.TITLE)
        self.text.insert(tk.INSERT, "\n\n")

    def key_press(self, event):
        "Stop modifying actions."
        if event.char in constants.AFFECTS_CHARACTER_COUNT:
            return "break"

    def link_action(self, event):
        link = self.get_link()
        if link:
            webbrowser.open_new_tab(link["url"])


class TextViewer(BaseTextViewer):
    "Text viewer window."

    def __init__(self, parent, main, filepath, title=None):
        super().__init__(parent, main, filepath, title=title)
        self.move_cursor(self.frontmatter.get("cursor"))
        self.status = constants.Status.lookup(self.frontmatter.get("status")) or constants.STARTED

    def configure_text_tags(self, text):
        super().configure_text_tags(text)
        text.tag_configure(constants.INDEXED, underline=True)
        text.tag_configure(constants.REFERENCE,
                           foreground=constants.REFERENCE_COLOR,
                           underline=True)
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

    def configure_text_tag_bindings(self, text):
        super().configure_text_tag_bindings(text)
        text.tag_bind(constants.INDEXED, "<Enter>", self.indexed_enter)
        text.tag_bind(constants.INDEXED, "<Leave>", self.indexed_leave)
        text.tag_bind(constants.INDEXED, "<Button-1>", self.indexed_view)
        text.tag_bind(constants.REFERENCE, "<Enter>", self.reference_enter)
        text.tag_bind(constants.REFERENCE, "<Leave>", self.reference_leave)
        text.tag_bind(constants.REFERENCE, "<Button-1>", self.reference_view)
        text.tag_bind(constants.FOOTNOTE_REF, "<Enter>", self.footnote_enter)
        text.tag_bind(constants.FOOTNOTE_REF, "<Leave>", self.footnote_leave)

class HelpViewer(BaseTextViewer):

    TEXT_COLOR = "white"
