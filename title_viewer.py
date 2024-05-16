"Title page viewer."

from icecream import ic

import functools

import tkinter as tk
from tkinter import ttk
import tkinter.simpledialog

import constants
import utils

from base_viewer import BaseViewer
from utils import Tr


class TitleViewer(BaseViewer):
    "View of the title page setup."

    def __init__(self, parent, main):
        self.chapters_var = tk.IntVar()
        self.texts_var = tk.IntVar()
        self.characters_var = tk.IntVar()
        self.indexed_var = tk.IntVar()
        self.references_var = tk.IntVar()
        super().__init__(parent, main)

    def __str__(self):
        return "Title"

    def display(self):
        self.display_wipe()
        self.display_title()
        self.display_statistics()

    def display_title(self):
        first = self.view.index(tk.INSERT)
        self.view.insert(tk.INSERT, self.main.title)
        button = tk.ttk.Button(self.view, text=Tr("Edit"), command=self.edit_title)
        self.view.window_create(tk.INSERT, window=button)
        self.view.insert(tk.INSERT, "\n")
        self.view.tag_add( constants.H_LOOKUP[1]["tag"], first, tk.INSERT)

        first = self.view.index(tk.INSERT)
        self.view.insert(tk.INSERT, self.main.subtitle or "[no subtitle]")
        button = tk.ttk.Button(self.view, text=Tr("Edit"), command=self.edit_subtitle)
        self.view.window_create(tk.INSERT, window=button)
        self.view.insert(tk.INSERT, "\n")
        self.view.tag_add( constants.H_LOOKUP[2]["tag"], first, tk.INSERT)

        first = self.view.index(tk.INSERT)
        for author in self.main.authors:
            self.view.insert(tk.INSERT, author)
            button = tk.ttk.Button(self.view,
                                   text=Tr("Delete"), 
                                   command=functools.partial(self.delete_author,
                                                             author=author))
            self.view.window_create(tk.INSERT, window=button)
            self.view.insert(tk.INSERT, "\n")
        if not self.main.authors:
            self.view.insert(tk.INSERT, "[no authors]\n")
        button = tk.ttk.Button(self.view, text=Tr("Add"), command=self.add_author)
        self.view.window_create(tk.INSERT, window=button)
        self.view.insert(tk.INSERT, "\n")
        self.view.tag_add( constants.H_LOOKUP[3]["tag"], first, tk.INSERT)

    def display_statistics(self):
        frame = tk.ttk.Frame(self.view)

        label = tk.ttk.Label(frame, text=Tr("Number of chapters") + ":")
        label.grid(row=0, column=0, sticky=tk.E, padx=4)
        label = tk.ttk.Label(frame, textvariable=self.chapters_var)
        label.grid(row=0, column=1, sticky=tk.E, padx=4)

        label = tk.ttk.Label(frame, text=Tr("Number of texts") + ":")
        label.grid(row=1, column=0, sticky=tk.E, padx=4)
        label = tk.ttk.Label(frame, textvariable=self.texts_var)
        label.grid(row=1, column=1, sticky=tk.E, padx=4)

        label = tk.ttk.Label(frame, text=Tr("Number of characters") + ":")
        label.grid(row=2, column=0, sticky=tk.E, padx=4)
        label = tk.ttk.Label(frame, textvariable=self.characters_var)
        label.grid(row=2, column=1, sticky=tk.E, padx=4)

        label = tk.ttk.Label(frame, text=Tr("Number of indexed") + ":")
        label.grid(row=3, column=0, sticky=tk.E, padx=4)
        label = tk.ttk.Label(frame, textvariable=self.indexed_var)
        label.grid(row=3, column=1, sticky=tk.E, padx=4)

        label = tk.ttk.Label(frame, text=Tr("Number of references") + ":")
        label.grid(row=4, column=0, sticky=tk.E, padx=4)
        label = tk.ttk.Label(frame, textvariable=self.references_var)
        label.grid(row=4, column=1, sticky=tk.E, padx=4)

        self.view.window_create(tk.INSERT, window=frame)

    def edit_title(self):
        result = tk.simpledialog.askstring(parent=self.view,
                                           title=Tr("Title?"), 
                                           prompt=Tr("Give new title") + ":",
                                           initialvalue=self.main.title)
        if result is None:
            return
        self.main.title = result
        self.display()

    def edit_subtitle(self):
        result = tk.simpledialog.askstring(parent=self.view,
                                           title=Tr("Subtitle?"), 
                                           prompt=Tr("Give new subtitle") + ":",
                                           initialvalue=self.main.subtitle)
        if result is None:
            return
        self.main.subtitle = result
        self.display()

    def delete_author(self, author):
        if not tk.messagebox.askokcancel(parent=self.view, 
                                         title=Tr("Delete"),
                                         message=Tr(f"Really delete author '{author}'?")):
            return
        try:
            self.main.authors.remove(author)
        except ValueError:
            pass
        else:
            self.display()

    def add_author(self):
        result = tk.simpledialog.askstring(parent=self.view,
                                           title=Tr("Author"), 
                                           prompt=Tr("Give new author") + ":")
        if result is None:
            return
        result = result.strip()
        if not result:
            return
        self.main.authors.append(result)
        self.display()
