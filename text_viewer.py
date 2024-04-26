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
        super().__init__(main, filepath, title=title)
        self.setup_text(parent)
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
    "Text viewer window."

    def __init__(self, parent, main, filepath, title=None):
        super().__init__(parent, main, filepath, title=title)
        self.status = constants.Status.lookup(self.frontmatter.get("status")) or constants.STARTED

        
class HelpViewer(BaseTextViewer):

    TEXT_COLOR = "white"

    def __str__(self):
        return "Help"
