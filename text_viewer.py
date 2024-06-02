"Viewer window for Markdown text file."

from icecream import ic

import tkinter as tk

import constants
import utils

from viewer import Viewer


class TextViewer(Viewer):
    "Viewer window for Markdown text file."

    TEXT_COLOR = constants.TEXT_COLOR

    def __init__(self, parent, main, text):
        super().__init__(parent, main)
        self.text = text

    def __str__(self):
        "The full name of the text; filepath excluding extension."
        return self.text.fullname

    def __len__(self):
        "Number of characters. XXX Not quite sure why '+ 1' is needed..."
        return len(self.view.get("1.0", tk.END)) - (self.heading_offset + 1)

    @property
    def section(self):
        "The section of the text; empty string if at top level."
        return self.text.parentpath

    def get_cursor(self):
        "Get the position of cursor in absolute number of characters."
        return super().get_cursor() - self.heading_offset

    def set_cursor(self, position):
        "Set the position of the cursor by the absolute number of characters."
        super().set_cursor(position + self.heading_offset)

    cursor = property(get_cursor, set_cursor)

    @property
    def heading(self):
        if self.main.config["main"].get("display_heading_ordinal", False):
            return self.text.heading
        else:
            return self.text.name

    @property
    def heading_offset(self):
        if self.text.get("display_heading", True):
            return len(self.heading) + 1
        else:
            return 0

    def display_heading(self):
        if not self.text.get("display_heading", True):
            return
        try:
            tag = constants.H_LOOKUP[self.text.level]["tag"]
        except KeyError:
            tag = constants.H_LOOKUP[0]["tag"]
        self.view.insert(tk.INSERT, self.heading + "\n", tag)

    def display_view(self):
        self.render(self.text.ast)
