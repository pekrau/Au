"Help text window."

import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox
import webbrowser

import constants
import utils


class HelpText:
    "Help text window."

    def __init__(self, main):
        self.main = main
        self.main.help_window = self
        self.toplevel = tk.Toplevel(self.main.root)
        self.toplevel.title("Au help")
        self.toplevel.protocol("WM_DELETE_WINDOW", self.close)
        try:
            self.toplevel.geometry(self.main.configuration["geometry"])
        except KeyError:
            pass

    def close(self, event=None):
        self.main.help_text = None
        self.toplevel.destroy()

    def get_configuration(self):
        return dict(geometry=self.toplevel.geometry())
