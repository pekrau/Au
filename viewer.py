"Base viewer class."

from icecream import ic

import os.path
import string
import webbrowser

import tkinter as tk
import tkinter.messagebox
import tkinter.ttk

import constants
import utils


class Viewer:
    "Base viewer class containing a 'tk.Text' instance."

    TEXT_COLOR = "white"

    def __init__(self, parent, main):
        self.main = main
        self.view_create(parent)

    def view_create(self, parent):
        "Create the view tk.Text widget and its associates."
        self.view_frame = tk.ttk.Frame(parent)
        self.view_frame.pack(fill=tk.BOTH, expand=True)
        self.view_frame.rowconfigure(0, weight=1)
        self.view_frame.columnconfigure(0, weight=1)
        self.view = tk.Text(
            self.view_frame,
            background=self.TEXT_COLOR,
            padx=constants.TEXT_PADX,
            font=constants.FONT,
            wrap=tk.WORD,
            spacing1=constants.TEXT_SPACING1,
            spacing2=constants.TEXT_SPACING2,
            spacing3=constants.TEXT_SPACING3,
        )
        self.view.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.scroll_y = tk.ttk.Scrollbar(
            self.view_frame, orient=tk.VERTICAL, command=self.view.yview
        )
        self.scroll_y.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.view.configure(yscrollcommand=self.scroll_y.set)

    def notification(self, eventname, func):
        "Set a function to be called on event."
        self.main.root.bind(eventname, func)
