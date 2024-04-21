"Base Editor window; for text, footnote, reference."

from icecream import ic

import io
import json
import os
import string

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox as tk_messagebox
from tkinter import simpledialog as tk_simpledialog

import constants
import utils


class BaseEditor:
    "Base editor window."

    def setup_toplevel(self, root):
        self.toplevel = tk.Toplevel(self.main.root)
