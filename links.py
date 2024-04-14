"Handle links in a text editor window."

from icecream import ic

import webbrowser

import tkinter as tk
from tkinter import ttk
from tkinter import simpledialog as tk_simpledialog

import constants


class Links:
    "Manage links in a text editor window."

    def __init__(self, editor):
        self.editor = editor
        self.lookup = dict()
        self.editor.text.tag_configure(constants.LINK,
                                       foreground=constants.LINK_COLOR,
                                       underline=True)
        self.editor.text.tag_bind(constants.LINK, "<Enter>", self.enter)
        self.editor.text.tag_bind(constants.LINK, "<Leave>", self.leave)
        self.editor.text.tag_bind(constants.LINK, "<Button-1>", self.edit)
        self.editor.text.tag_bind(constants.LINK, "<Control-Button-1>", self.browse)

    def add(self, ast, first, last):
        self.new(ast["dest"], ast["title"], first, last)

    def new(self, url, title, first, last):
        tag = f"{constants.LINK_PREFIX}{len(self.lookup)}"
        self.lookup[tag] = dict(tag=tag, url=url, title=title)
        self.editor.text.tag_add(constants.LINK, first, last)
        self.editor.text.tag_add(tag, first, last)

    def enter(self, event):
        self.editor.text.configure(cursor="hand1")
        data = self.get()
        self.editor.url_var.set(data["url"])
        self.editor.title_var.set(data["title"] or "-")

    def leave(self, event):
        self.editor.text.configure(cursor="")
        self.editor.url_var.set("")
        self.editor.title_var.set("")

    def get(self, tag=None):
        "Get the link for the given tag, or for the current cursor position."
        if tag is None:
            for tag in self.editor.text.tag_names(tk.CURRENT):
                if tag.startswith(constants.LINK_PREFIX):
                    break
            else:
                return None
        return self.lookup[tag]

    def edit(self, event):
        link = self.get()
        if not link:
            return
        edit = Link(self.editor.toplevel, link["url"], link["title"])
        if edit.result:
            if edit.result["url"]:
                link["url"] = edit.result["url"]
                link["title"] = edit.result["title"]
            else:
                region = self.editor.text.tag_nextrange(link["tag"], "1.0")
                self.editor.text.tag_remove(constants.LINK, *region)
                self.editor.text.tag_remove(link["tag"], *region)
                # Do not remove entry from main.links: the count must be preserved.
            self.editor.ignore_modified_event = True
            self.editor.text.edit_modified(True)

    def browse(self, event):
        webbrowser.open_new_tab(self.get()["url"])


class Link(tk_simpledialog.Dialog):
    "Dialog window for editing URL and title for a link."

    def __init__(self, parent, url, title):
        self.initial = dict(url=url, title=title)
        self.result = None
        super().__init__(parent, title="Edit link")

    def body(self, body):
        label = ttk.Label(body, text="URL")
        label.grid(row=0, column=0)
        self.url_entry = tk.Entry(body)
        if self.initial["url"]:
            self.url_entry.insert(0, self.initial["url"])
        self.url_entry.grid(row=0, column=1)
        label = ttk.Label(body, text="Title")
        label.grid(row=1, column=0)
        self.title_entry = tk.Entry(body)
        if self.initial["title"]:
            self.title_entry.insert(0, self.initial["title"])
        self.title_entry.grid(row=1, column=1)
        return self.url_entry

    def validate(self):
        self.result = dict(url=self.url_entry.get(),
                           title=self.title_entry.get())
        return True
