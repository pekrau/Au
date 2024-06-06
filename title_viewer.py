"Title page viewer."

from icecream import ic

import functools

import tkinter as tk
from tkinter import ttk
import tkinter.simpledialog

import constants
import utils

from viewer import Viewer
from utils import Tr


class TitleViewer(Viewer):
    "View of the title page setup."

    def __init__(self, parent, main):
        super().__init__(parent, main)
        self.status_var = tk.StringVar()
        self.chapters_var = tk.IntVar()
        self.texts_var = tk.IntVar()
        self.characters_var = tk.IntVar()
        self.indexed_var = tk.IntVar()
        self.references_var = tk.IntVar()

    def __str__(self):
        return "Title"

    def display(self):
        self.view.delete("1.0", tk.END)
        self.display_heading()
        self.display_statistics()
        self.update_statistics()

    def display_heading(self):
        self.view.insert(
            tk.INSERT, f"{self.main.title}\n", constants.H_LOOKUP[1]["tag"]
        )
        self.view.insert(
            tk.INSERT,
            f"{self.main.subtitle or '[no subtitle]'}\n",
            constants.H_LOOKUP[2]["tag"],
        )
        for author in self.main.authors:
            self.view.insert(tk.INSERT, f"{author}\n", constants.H_LOOKUP[3]["tag"])
        if not self.main.authors:
            self.view.insert(tk.INSERT, "[no authors]\n")

    def display_statistics(self):
        frame = tk.ttk.Frame(self.view, padding=4)

        row = 0
        label = tk.ttk.Label(frame, text=Tr("Status") + ":")
        label.grid(row=row, column=0, sticky=tk.E, padx=4)
        label = tk.ttk.Label(frame, textvariable=self.status_var)
        label.grid(row=row, column=1, sticky=tk.E, padx=4)

        row += 1
        label = tk.ttk.Label(frame, text=Tr("Number of chapters") + ":")
        label.grid(row=row, column=0, sticky=tk.E, padx=4)
        label = tk.ttk.Label(frame, textvariable=self.chapters_var)
        label.grid(row=row, column=1, sticky=tk.E, padx=4)

        row += 1
        label = tk.ttk.Label(frame, text=Tr("Number of texts") + ":")
        label.grid(row=row, column=0, sticky=tk.E, padx=4)
        label = tk.ttk.Label(frame, textvariable=self.texts_var)
        label.grid(row=row, column=1, sticky=tk.E, padx=4)

        row += 1
        label = tk.ttk.Label(frame, text=Tr("Number of characters") + ":")
        label.grid(row=row, column=0, sticky=tk.E, padx=4)
        label = tk.ttk.Label(frame, textvariable=self.characters_var)
        label.grid(row=row, column=1, sticky=tk.E, padx=4)

        row += 1
        label = tk.ttk.Label(frame, text=Tr("Number of indexed") + ":")
        label.grid(row=row, column=0, sticky=tk.E, padx=4)
        label = tk.ttk.Label(frame, textvariable=self.indexed_var)
        label.grid(row=row, column=1, sticky=tk.E, padx=4)

        row += 1
        label = tk.ttk.Label(frame, text=Tr("Number of references") + ":")
        label.grid(row=row, column=0, sticky=tk.E, padx=4)
        label = tk.ttk.Label(frame, textvariable=self.references_var)
        label.grid(row=row, column=1, sticky=tk.E, padx=4)

        row += 1
        label = tk.ttk.Label(frame, text=Tr("Language") + ":")
        label.grid(row=row, column=0, sticky=tk.E, padx=4)
        label = tk.ttk.Label(frame, text=self.main.language)
        label.grid(row=row, column=1, sticky=tk.E, padx=4)

        self.view.insert(tk.INSERT, "\n")
        self.view.window_create(tk.INSERT, window=frame)

    def update_statistics(self, event=None):
        statuses = [t.status for t in self.main.source.all_texts] + [
            max(constants.STATUSES)
        ]
        self.status_var.set(Tr(str(min(statuses))))
        self.chapters_var.set(len(self.main.source.items))
        self.texts_var.set(len(self.main.source.all_texts))
        self.characters_var.set(
            sum([len(t.viewer) for t in self.main.source.all_texts])
        )
