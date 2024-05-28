"Viewer for the search feature and resulting list."

from icecream import ic

import functools

import tkinter as tk
import tkinter.ttk

import constants
import utils

from viewer import Viewer
from utils import Tr


class SearchViewer(Viewer):
    "Viewer for the search feature and resulting list."

    def __init__(self, parent, main):
        super().__init__(parent, main)
        self.result = []

    def __str__(self):
        return "Search"

    def view_create(self, parent):
        """Create an outer super-frame to contain the search entry box
        and the view frame.
        """
        self.super_frame = tk.ttk.Frame(parent)
        self.super_frame.pack(fill=tk.BOTH, expand=True)

        self.entry_frame = tk.ttk.Frame(self.super_frame, padding=6)
        self.entry_frame.pack(fill=tk.X)
        self.entry_frame.columnconfigure(1, weight=1)

        label = tk.ttk.Label(self.entry_frame, text=Tr("Term"))
        label.grid(row=0, column=0, padx=4)
        self.search_entry = tk.ttk.Entry(self.entry_frame)
        self.search_entry.grid(row=0, column=1, sticky=(tk.E, tk.W), padx=4)
        self.search_entry.bind("<Return>", self.search)

        button = tk.ttk.Button(self.entry_frame, text=Tr("Search"), command=self.search)
        button.grid(row=0, column=2, padx=4, pady=4)
        button = tk.ttk.Button(self.entry_frame, text=Tr("Clear"), command=self.clear)
        button.grid(row=1, column=2, padx=4, pady=4)

        self.search_case_var = tk.IntVar(value=1)
        self.search_case = tk.ttk.Checkbutton(
            self.entry_frame,
            text=Tr("Character case is significant"),
            variable=self.search_case_var,
        )
        self.search_case.grid(row=1, column=1, sticky=tk.W)

        self.search_regexp_var = tk.IntVar(value=0)
        self.search_regexp = tk.ttk.Checkbutton(
            self.entry_frame,
            text=Tr("Allow regular expression") + "\n. ^ [c1...] (...) * + ? e1|e2",
            variable=self.search_regexp_var,
        )
        self.search_regexp.grid(row=2, column=1, sticky=tk.W)

        super().view_create(self.super_frame)

    def configure_tags(self):
        "Add a tag configuration."
        super().configure_tags()
        self.view.tag_configure(constants.SEARCH, lmargin1=constants.SEARCH_INDENT)

    def bind_tags(self):
        "Add tag bindings."
        super().bind_tags()
        self.view.tag_bind(constants.SEARCH, "<Enter>", self.xref_enter)
        self.view.tag_bind(constants.SEARCH, "<Leave>", self.xref_leave)

    def search(self, event=None):
        """Search the viewer texts and display the result.
        Due to an apparent Tk/Tcl bug that affects searches of with
        tags for elided parts, a work-around has been implemented.
        Temporarily, all tags with elide set are unset, then restored
        after the search. Ugly, but it works.
        """
        term = self.search_entry.get()
        if not term:
            return
        self.display()
        case = self.search_case_var.get()
        regexp = self.search_regexp_var.get()
        count_var = tk.IntVar()
        self.result = []
        for text in self.main.source.all_texts:
            text_view = text.viewer.view
            found = []
            elided_tags = set()
            for tag in text_view.tag_names():  # Elide bug workaround. See above.
                if text_view.tag_cget(tag, "elide"):
                    elided_tags.add(tag)
                    text_view.tag_configure(tag, elide=False)
            first = text_view.search(
                term,
                "1.0",
                nocase=not case,
                regexp=regexp,
                stopindex=tk.END,
                count=count_var,
            )
            while first:
                length = count_var.get()
                item = text_view.get(first, text_view.index(first + f"+{length}c"))
                found.append((first, length))
                first = text_view.search(
                    term,
                    first + f"+{length}c",
                    nocase=not case,
                    regexp=regexp,
                    stopindex=tk.END,
                    count=count_var,
                )
            for tag in elided_tags:  # Elide bug workaround. See above.
                text_view.tag_configure(tag, elide=True)
            if found:
                self.result.append((text, found))
        self.display()

    def display_heading(self):
        pass

    def display_view(self):
        tag_counter = 0
        for text, found in self.result:
            view = text.viewer.view
            self.view.insert(tk.INSERT, text.fullname, (constants.BOLD,))
            self.view.insert(tk.INSERT, "\n")
            for first, length in found:
                begin = self.view.index(tk.INSERT)
                start = view.index(first + f"-{constants.SEARCH_FRAGMENT}c")
                if start != "1.0":
                    self.view.insert(tk.INSERT, "...")
                fragment = view.get(start, first).replace("\n", " ")
                self.view.insert(tk.INSERT, fragment)
                last = view.index(first + f"+{length}c")
                self.view.insert(tk.INSERT, view.get(first, last), constants.HIGHLIGHT)
                finish = view.index(last + f"+{constants.SEARCH_FRAGMENT}c")
                fragment = view.get(last, finish).replace("\n", " ")
                self.view.insert(tk.INSERT, fragment)
                if finish != view.index(tk.END):
                    self.view.insert(tk.INSERT, "...")
                self.view.tag_add(constants.SEARCH, begin, tk.INSERT)
                tag = f"{constants.SEARCH_PREFIX}{tag_counter}"
                tag_counter += 1
                self.view.tag_add(tag, begin, tk.INSERT)
                self.view.tag_bind(
                    tag,
                    "<Button-1>",
                    functools.partial(
                        self.xref_action, text=text, first=first, last=last
                    ),
                )
                self.view.insert(tk.INSERT, "\n")
            self.view.insert(tk.INSERT, "\n")

    def xref_enter(self, event):
        self.view.configure(cursor=contants.XREF_CURSOR)

    def xref_leave(self, event):
        self.view.configure(cursor="")

    def xref_action(self, event=None, text=None, first=None, last=None):
        self.main.texts_notebook.select(text.tabid)
        text.viewer.highlight(first=first, last=last)

    def clear(self):
        self.result = []
        self.search_entry.delete(0, tk.END)
        self.display()
