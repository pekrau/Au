"Meta content text viewers."

from icecream import ic

import tkinter as tk
from tkinter import ttk

import constants
import utils
from base_viewer import BaseViewer


class MetaViewer(BaseViewer):
    "Base class for meta contents viewers."

    def display(self):
        self.view.delete("1.0", tk.END)
        self.display_title()


class BookViewer(MetaViewer):
    "View of the book title page setup."

    def __str__(self):
        return "Book"


class ReferencesViewer(MetaViewer):
    "View of the references list."

    def __str__(self):
        return "References"


class SearchViewer(MetaViewer):
    "View of the search feature and resulting list."

    def view_create(self, parent):
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill=tk.BOTH, expand=True)
        self.entry_frame = ttk.Frame(self.frame, 
                                     relief=tk.RAISED,
                                     borderwidth=3,
                                     padding=4)
        self.entry_frame.pack(fill=tk.X)
        label = ttk.Label(self.entry_frame, text="Search term")
        label.grid(row=0, column=0, padx=4)
        self.search_entry = ttk.Entry(self.entry_frame)

        self.search_entry.grid(row=0, column=1,
                               sticky=(tk.E, tk.W), 
                               padx=4)
        self.search_entry.bind("<Return>", self.search)
        button = ttk.Button(self.entry_frame, text="Go", command=self.search, padding=4)
        button.grid(row=0, column=2, padx=4)
        self.entry_frame.columnconfigure(1, weight=1)

        self.result_frame = ttk.Frame(self.frame)
        self.result_frame.pack(fill=tk.BOTH, expand=True)
        self.result_frame.rowconfigure(0, weight=1)
        self.result_frame.columnconfigure(0, weight=1)

        self.view = tk.Text(self.result_frame,
                            background=self.TEXT_COLOR,
                            padx=constants.TEXT_PADX,
                            font=constants.FONT_NORMAL_FAMILY,
                            wrap=tk.WORD,
                            spacing1=constants.TEXT_SPACING1,
                            spacing2=constants.TEXT_SPACING2,
                            spacing3=constants.TEXT_SPACING3)
        self.view.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.scroll_y = ttk.Scrollbar(self.result_frame,
                                      orient=tk.VERTICAL,
                                      command=self.view.yview)
        self.scroll_y.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.view.configure(yscrollcommand=self.scroll_y.set)
        
    def __str__(self):
        return "Search"

    def display_title(self):
        self.view.insert(tk.INSERT, "Results", constants.TITLE)
        self.view.insert(tk.INSERT, "\n\n")

    def search(self, event=None):
        term = self.search_entry.get()
        if not term:
            return
        self.clear()
        ic("search", event, term)
        count = tk.IntVar()
        for text in self.main.source.all_texts:
            pos = text.viewer.view.search(term, "1.0", stopindex=tk.END, count=count)
            ic(pos, count.get())
            while pos:
                self.view.insert(tk.INSERT, text.fullname)
                self.view.insert(tk.INSERT, "\n\n")
                pos = text.viewer.view.search(term, pos + f"+{count.get()}c", stopindex=tk.END)

    def clear(self):
        self.display()          # XXX Should reset search term box and results list.
        

class TodoViewer(MetaViewer):
    "View of the to-do list."

    def __str__(self):
        return "To do"
