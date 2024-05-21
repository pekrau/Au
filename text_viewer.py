"Viewer window for Markdown text file."

from icecream import ic

import tkinter as tk

import constants
import utils

from viewer import Viewer
from renderer import Renderer


class TextRenderer(Renderer):
    "Display text title according to text position in hierarchy."

    def __len__(self):
        "Number of characters. XXX Not quite sure why '+ 2' is needed..."
        return len(self.view.get("1.0", tk.END)) - (len(self.viewer.name) + 2)

    def get_cursor(self):
        "Get the position of cursor in absolute number of characters."
        return super().get_cursor() - (len(self.viewer.name) + 1)

    def set_cursor(self, position):
        "Set the position of the cursor by the absolute number of characters."
        super().set_cursor(position + (len(self.viewer.name) + 1))

    cursor = property(get_cursor, set_cursor)

    def display_title(self):
        try:
            tag = constants.H_LOOKUP[self.viewer.text.depth]["tag"]
        except KeyError:
            tag = constants.H_LOOKUP[0]["tag"]
        self.view.insert(tk.INSERT, self.viewer.text.name + "\n", (tag,))


class TextViewer(Viewer):
    "Viewer window for Markdown text file."

    TEXT_COLOR = constants.TEXT_COLOR

    def __init__(self, parent, main, text):
        super().__init__(parent, main)
        self.text = text
        self.renderer = TextRenderer(main, self, self.view)
        self.display()

    def __str__(self):
        "The full name of the text; filepath excluding extension."
        return self.text.fullname

    @property
    def section(self):
        "The section of the text; empty string if at top level."
        return self.text.parentpath

    @property
    def name(self):
        "The short name of the text."
        return self.text.name

    def display(self):
        self.renderer.display(self.text.ast)
