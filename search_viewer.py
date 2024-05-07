"Viewer for the search feature and resulting list."

from icecream import ic

import functools

import tkinter as tk
from tkinter import ttk

import constants
import utils
from base_viewer import BaseViewer


class SearchViewer(BaseViewer):
    "Viewer for the search feature and resulting list."

    def __str__(self):
        return "Search"

    def view_create(self, parent):
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill=tk.BOTH, expand=True)
        self.entry_frame = ttk.Frame(self.frame, 
                                     padding=6)
        self.entry_frame.pack(fill=tk.X)
        self.entry_frame.columnconfigure(1, weight=1)

        ttk.Label(self.entry_frame, text="Term").grid(row=0, column=0, padx=4)
        self.search_entry = ttk.Entry(self.entry_frame)
        self.search_entry.grid(row=0, column=1,
                               sticky=(tk.E, tk.W), 
                               padx=4)
        self.search_entry.bind("<Return>", self.search)

        button = ttk.Button(self.entry_frame, text="Search", command=self.search)
        button.grid(row=0, column=2, padx=4, pady=4)
        button = ttk.Button(self.entry_frame, text="Clear", command=self.clear)
        button.grid(row=1, column=2, padx=4, pady=4)

        self.search_nocase_var = tk.IntVar(value=1)
        self.search_nocase = ttk.Checkbutton(self.entry_frame,
                                             text="Ignore character case",
                                             variable=self.search_nocase_var)
        self.search_nocase.grid(row=1, column=1, sticky=tk.W)

        self.search_regexp_var = tk.IntVar(value=0)
        self.search_regexp = ttk.Checkbutton(
            self.entry_frame,
            text="Allow regular expression\n. ^ [c1...] (...) * + ? e1|e2",
            variable=self.search_regexp_var)
        self.search_regexp.grid(row=2, column=1, sticky=tk.W)

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
        
    def view_configure_tags(self, view=None):
        "Configure the tags used in the 'tk.Text' instance."
        if view is None:
            view = self.view
        super().view_configure_tags(view=view)
        view.tag_configure(constants.SEARCH, lmargin1=constants.SEARCH_INDENT)

    def view_configure_tag_bindings(self, view=None):
        "Configure the tag bindings used in the 'tk.Text' instance."
        if view is None:
            view = self.view
        super().view_configure_tag_bindings(view=view)
        view.tag_bind(constants.SEARCH, "<Enter>", self.link_enter)
        view.tag_bind(constants.SEARCH, "<Leave>", self.link_leave)

    def search(self, event=None):
        """Search the viewer texts.
        Due to an apparent Tk/Tcl bug that affects searches of with
        tags for elided parts, a work-around has been implemented.
        Ugly, but it makes it work.
        """
        term = self.search_entry.get()
        if not term:
            return
        self.display()
        tag_counter = 0
        nocase = self.search_nocase_var.get()
        regexp = self.search_regexp_var.get()
        count_var = tk.IntVar()
        for text in self.main.source.all_texts:
            view = text.viewer.view
            found = []
            text.viewer.tags_inhibit_elide() # Bug workaround. See above.
            first = view.search(term, 
                                "1.0",
                                nocase=nocase,
                                regexp=regexp, 
                                stopindex=tk.END,
                                count=count_var)
            while first:
                length = count_var.get()
                item = view.get(first, view.index(first + f"+{length}c"))
                found.append((first, length))
                first = view.search(term,
                                    first + f"+{length}c",
                                    nocase=nocase,
                                    regexp=regexp,
                                    stopindex=tk.END,
                                    count=count_var)
            text.viewer.tags_restore_elide() # Bug workaround. See above.
            if not found:
                continue
            self.view.insert(tk.INSERT, text.fullname, (constants.BOLD, ))
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
                self.view.tag_bind(tag,
                                   "<Button-1>", 
                                   functools.partial(self.link_action,
                                                     text=text,
                                                     first=first,
                                                     last=last))
                self.view.insert(tk.INSERT, "\n")
            self.view.insert(tk.INSERT, "\n")

    def link_enter(self, event):
        self.view.configure(cursor="hand2")

    def link_leave(self, event):
        self.view.configure(cursor="")

    def link_action(self, event=None, text=None, first=None, last=None):
        self.main.texts_notebook.select(text.tabid)
        text.viewer.highlight(first=first, last=last)

    def display(self):
        self.view.delete("1.0", tk.END)

    def clear(self):
        self.search_entry.delete(0, tk.END)
        self.display()
