"Text viewer window classes."

from icecream import ic

import webbrowser

import tkinter as tk
from tkinter import ttk

import constants
import utils
from base_text import BaseTextContainer, TextMixin


class BaseTextViewer(TextMixin, BaseTextContainer):
    "Base text viewer window."

    def __init__(self, parent, main, filepath, title=None):
        super().__init__(main, filepath, title=title)
        self.text_setup(parent)
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


class TextViewer(BaseTextViewer):
    "Text viewer of Markdown contents."

    TEXT_COLOR = constants.TEXT_COLOR

    def __init__(self, parent, main, filepath, title=None):
        super().__init__(parent, main, filepath, title=title)
        self.status = constants.Status.lookup(self.frontmatter.get("status")) or constants.STARTED

        
class MetaViewer(TextMixin):
    "Base class for meta contents viewers."

    def __init__(self, parent, main):
        self.main = main
        self.text_setup(parent)
        self.text_configure_tags()


class ReferencesViewer(MetaViewer):
    "Viewer of the references list."

    def __str__(self):
        return "References"


class IndexedViewer(MetaViewer):
    "Viewer of the list of indexed terms."

    def __str__(self):
        return "Indexed"


class TodoViewer(MetaViewer):
    "Viewer of the to-do list."

    def __str__(self):
        return "To do"


class HelpViewer(BaseTextViewer):
    "Viewer of Markdown contents of the help file."

    def __init__(self, parent, main, filepath):
        super().__init__(parent, main, filepath,
                         title="Au " + ".".join([str(n) for n in constants.VERSION]))

    def __str__(self):
        return "Help"
