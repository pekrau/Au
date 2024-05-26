"Title page viewer."

import functools

import tkinter as tk
from tkinter import ttk
import tkinter.simpledialog

import constants
import utils

from viewer import Viewer
from utils import Tr

from icecream import ic


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
        self.display_title()
        self.display_statistics()
        self.update_statistics()

    def display_title(self):
        first = self.view.index(tk.INSERT)
        self.view.insert(tk.INSERT, self.main.title)
        button = tk.ttk.Button(self.view, text=Tr("Edit"), command=self.edit_title)
        self.view.window_create(tk.INSERT, window=button)
        self.view.insert(tk.INSERT, "\n")
        self.view.tag_add(constants.H_LOOKUP[1]["tag"], first, tk.INSERT)

        first = self.view.index(tk.INSERT)
        self.view.insert(tk.INSERT, self.main.subtitle or "[no subtitle]")
        button = tk.ttk.Button(self.view, text=Tr("Edit"), command=self.edit_subtitle)
        self.view.window_create(tk.INSERT, window=button)
        self.view.insert(tk.INSERT, "\n")
        self.view.tag_add(constants.H_LOOKUP[2]["tag"], first, tk.INSERT)

        first = self.view.index(tk.INSERT)
        for author in self.main.authors:
            self.view.insert(tk.INSERT, author)
            button = tk.ttk.Button(
                self.view,
                text=Tr("Delete"),
                command=functools.partial(self.delete_author, author=author),
            )
            self.view.window_create(tk.INSERT, window=button)
            self.view.insert(tk.INSERT, "\n")
        if not self.main.authors:
            self.view.insert(tk.INSERT, "[no authors]\n")
        button = tk.ttk.Button(self.view, text=Tr("Add"), command=self.add_author)
        self.view.window_create(tk.INSERT, window=button)
        self.view.insert(tk.INSERT, "\n")
        self.view.tag_add(constants.H_LOOKUP[3]["tag"], first, tk.INSERT)

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

        self.view.insert(tk.INSERT, "\n")
        self.view.window_create(tk.INSERT, window=frame)

    def update_statistics(self, event=None):
        statuses = [t.status for t in self.main.source.all_texts] + [max(constants.STATUSES)]
        self.status_var.set(Tr(str(min(statuses))))
        self.chapters_var.set(len(self.main.source.items))
        self.texts_var.set(len(self.main.source.all_texts))
        self.characters_var.set(
            sum([len(t.viewer) for t in self.main.source.all_texts])
        )

    def edit_title(self):
        result = tk.simpledialog.askstring(
            parent=self.view,
            title=Tr("Title?"),
            prompt=Tr("Give new title") + ":",
            initialvalue=self.main.title,
        )
        if result is None:
            return
        self.main.title = result
        self.display()

    def edit_subtitle(self):
        result = tk.simpledialog.askstring(
            parent=self.view,
            title=Tr("Subtitle?"),
            prompt=Tr("Give new subtitle") + ":",
            initialvalue=self.main.subtitle,
        )
        if result is None:
            return
        self.main.subtitle = result
        self.display()

    def delete_author(self, author):
        if not tk.messagebox.askokcancel(
            parent=self.view,
            title=Tr("Delete"),
            message=Tr(f"Really delete author '{author}'?"),
        ):
            return
        try:
            self.main.authors.remove(author)
        except ValueError:
            pass
        else:
            self.display()

    def add_author(self):
        result = tk.simpledialog.askstring(
            parent=self.view, title=Tr("Author"), prompt=Tr("Give new author") + ":"
        )
        if result is None:
            return
        result = result.strip()
        if not result:
            return
        self.main.authors.append(result)
        self.display()
