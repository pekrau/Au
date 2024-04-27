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

    TEXT_COLOR = constants.TEXT_COLOR

    def __init__(self, parent, main, filepath, title=None):
        super().__init__(parent, main, filepath, title=title)
        self.status = constants.Status.lookup(self.frontmatter.get("status")) or constants.STARTED

        
class ReferencesViewer:

    def __init__(self, parent, main):
        self.main = main
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill=tk.BOTH, expand=True)
        self.frame.rowconfigure(0, weight=1)
        self.frame.columnconfigure(0, weight=1)

        self.references_frame = ttk.Frame(self.frame)
        # self.scroll_y = ttk.Scrollbar(self.frame,
        #                               orient=tk.VERTICAL,
        #                               command=self.references_frame.yview)
        # self.scroll_y.grid(row=0, column=1, sticky=(tk.N, tk.S))
        # self.references_frame.configure(yscrollcommand=self.scroll_y.set)

    def __str__(self):
        return "References"


class IndexedViewer:

    def __init__(self, parent, main):
        self.main = main
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill=tk.BOTH, expand=True)
        self.frame.rowconfigure(0, weight=1)
        self.frame.columnconfigure(0, weight=1)

        self.indexed_frame = ttk.Frame(self.frame)
        # self.scroll_y = ttk.Scrollbar(self.frame,
        #                               orient=tk.VERTICAL,
        #                               command=self.indexed_frame.yview)
        # self.scroll_y.grid(row=0, column=1, sticky=(tk.N, tk.S))
        # self.indexed_frame.configure(yscrollcommand=self.scroll_y.set)

    def __str__(self):
        return "Indexed"


class TodoViewer:

    def __init__(self, parent, main):
        self.main = main
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill=tk.BOTH, expand=True)
        self.frame.rowconfigure(0, weight=1)
        self.frame.columnconfigure(0, weight=1)

        self.indexed_frame = ttk.Frame(self.frame)
        # self.scroll_y = ttk.Scrollbar(self.frame,
        #                               orient=tk.VERTICAL,
        #                               command=self.indexed_frame.yview)
        # self.scroll_y.grid(row=0, column=1, sticky=(tk.N, tk.S))
        # self.indexed_frame.configure(yscrollcommand=self.scroll_y.set)

    def __str__(self):
        return "To do"


class HelpViewer(BaseTextViewer):

    def __str__(self):
        return "Help"
