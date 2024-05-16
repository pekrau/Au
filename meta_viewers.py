"Meta content text viewers."

from icecream import ic

import functools

import tkinter as tk
from tkinter import ttk

import constants
import utils
from base_viewer import BaseViewer


class MetaViewer(BaseViewer):
    "Base class for meta contents viewers."

    def display(self):
        self.display_wipe()
        self.display_title()


class TitleViewer(MetaViewer):
    "View of the title page setup."

    def __str__(self):
        return str(self.main.source)

    def display_title(self):
        pass


class TodoViewer(MetaViewer):
    "View of the to-do list."

    def __str__(self):
        return "To do"

    def display_title(self):
        pass
