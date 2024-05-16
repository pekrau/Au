"To-do viewer."

from icecream import ic

import tkinter as tk
from tkinter import ttk

import constants
import utils
from base_viewer import BaseViewer


class TodoViewer(BaseViewer):
    "View of the to-do list."

    def __str__(self):
        return "To do"

    def display(self):
        self.display_wipe()
        self.display_title()

    def display_title(self):
        pass
