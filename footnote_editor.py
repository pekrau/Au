"Footnote editor window."

from icecream import ic

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox as tk_messagebox
from tkinter import simpledialog as tk_simpledialog

import constants
import utils
from editor_mixin import EditorMixin



class FootnoteEditor(EditorMixin):
    "Footnote editor window."

    TEXT_HEIGHT = 10

    def __init__(self, text_editor):
        self.text_editor = text_editor
        self.main = text_editor.main
        self.setup_toplevel(self.text_editor.toplevel,
                            "Edit footnote",
                            self.text_editor.toplevel.geometry())

        self.setup_text()
        self.prev_blank_line = False

    def save(self, event=None):
        ic("save")

    def close(self, event=None):
        ic("close")

    def handle_modified(self, event=None):
        ic("handle_modified")
    
