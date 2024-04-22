"Simple dialog window for editing the URL and title for a link."

from icecream import ic

import webbrowser

import tkinter as tk
from tkinter import ttk
from tkinter import simpledialog as tk_simpledialog


class LinkEdit(tk_simpledialog.Dialog):
    "Simple dialog window for editing the URL and title for a link."

    def __init__(self, toplevel, link):
        self.link = link
        self.result = None
        super().__init__(toplevel, title="Edit link")

    def body(self, body):
        label = ttk.Label(body, text="URL")
        label.grid(row=0, column=0, padx=4, sticky=tk.E)
        self.url_entry = tk.Entry(body, width=50)
        if self.link["url"]:
            self.url_entry.insert(0, self.link["url"])
        self.url_entry.grid(row=0, column=1)
        label = ttk.Label(body, text="Title")
        label.grid(row=1, column=0, padx=4, sticky=tk.E)
        self.title_entry = tk.Entry(body, width=50)
        if self.link["title"]:
            self.title_entry.insert(0, self.link["title"])
        self.title_entry.grid(row=1, column=1)
        return self.url_entry

    def validate(self):
        self.result = dict(url=self.url_entry.get(),
                           title=self.title_entry.get())
        return True

    def buttonbox(self):
        box = tk.Frame(self)
        w = ttk.Button(box, text="OK", width=10, command=self.ok, default=tk.ACTIVE)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        w = ttk.Button(box, text="Visit", width=10, command=self.visit)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        w = ttk.Button(box, text="Cancel", width=10, command=self.cancel)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)
        box.pack()

    def visit(self):
        webbrowser.open_new_tab(self.url_entry.get())
