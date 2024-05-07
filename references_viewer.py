"Viewer for the references list."

from icecream import ic

import os

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox as tk_messagebox
from tkinter import simpledialog as tk_simpledialog

import bibtexparser
import LaTexAccents

import constants
import utils

from source import Source
from base_viewer import BaseViewer


class ReferencesViewer(BaseViewer):
    "Viewer for the references list."

    def __init__(self, parent, main):
        super().__init__(parent, main)
        self.read()

    def view_create(self, parent):
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill=tk.BOTH, expand=True)
        self.actions_frame = ttk.Frame(self.frame, padding=6)
        self.actions_frame.pack(fill=tk.X)
        self.actions_frame.columnconfigure(0, weight=1)
        self.actions_frame.columnconfigure(1, weight=1)

        button = ttk.Button(self.actions_frame,
                            text="Import BibTeX",
                            command=self.import_bibtex,
                            padding=4)
        button.grid(row=0, column=0, padx=4, pady=4)

        button = ttk.Button(self.actions_frame,
                            text="Add manually",
                            command=self.add_manually,
                            padding=4)
        button.grid(row=0, column=1, padx=4, pady=4)

        self.result_frame = ttk.Frame(self.frame)
        self.result_frame.pack(fill=tk.BOTH, expand=True)
        self.result_frame.rowconfigure(0, weight=1)
        self.result_frame.columnconfigure(0, weight=1)

        self.view = tk.Text(self.result_frame,
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
        return "References"

    def view_configure_tags(self, view=None):
        "Configure the key bindings used in the 'tk.Text' instance."
        if view is None:
            view = self.view
        super().view_configure_tags(view=view)
        view.tag_configure(constants.REFERENCE, 
                           spacing1=constants.REFERENCE_SPACING,
                           lmargin2=constants.REFERENCE_INDENT)

    def display(self):
        self.view.delete("1.0", tk.END)
        for reference in sorted(self.references, key=lambda r: r["id"]):
            first = self.view.index(tk.INSERT)
            self.view.insert(tk.INSERT, reference["id"], (constants.BOLD, ))
            self.view.insert(tk.INSERT, "  ")
            self.view.insert(tk.INSERT, reference["authors"][0])
            for author in reference["authors"][1:constants.REFERENCE_MAX_AUTHORS-1]:
                self.view.insert(tk.INSERT, ", ")
                self.view.insert(tk.INSERT, author)
            if len(reference["authors"]) > constants.REFERENCE_MAX_AUTHORS:
                self.view.insert(tk.INSERT, " ...")
            if len(reference["authors"]) > 1:
                self.view.insert(tk.INSERT, " & ")
                self.view.insert(tk.INSERT, reference["authors"][-1])
            self.view.insert(tk.INSERT, " ")
            if reference["type"] == "book":
                self.view.insert(tk.INSERT, f"({reference['year']}). ")
                self.view.insert(tk.INSERT, reference["title"].strip(".") + ". ",
                                 (constants.ITALIC, ))
                try:
                    self.view.insert(tk.INSERT, f"{reference['publisher']}. ")
                except KeyError:
                    pass
                try:
                    self.view.insert(tk.INSERT, f"ISBN {reference['isbn']}. ")
                except KeyError:
                    pass
            elif reference["type"] == "article":
                self.view.insert(tk.INSERT, f"({reference['year']}). ")
                self.view.insert(tk.INSERT, reference["title"].strip(".") + ". ")
                self.view.insert(tk.INSERT, reference["journal"], (constants.ITALIC, ))
                try:
                    self.view.insert(tk.INSERT, f" {reference['volume']}")
                except KeyError:
                    pass
                else:
                    try:
                        self.view.insert(tk.INSERT, f"({reference['number']})")
                    except KeyError:
                        pass
                    self.view.insert(tk.INSERT, ": ")
                try:
                    self.view.insert(tk.INSERT,
                                     f"pp. {reference['pages'].replace('--', '-')}. ")
                except KeyError:
                    pass
                try:
                    self.view.insert(tk.INSERT, f"doi {reference['doi']} ")
                except KeyError:
                    pass
            self.view.tag_add(constants.REFERENCE, first, tk.INSERT)
            self.view.mark_set(reference["id"].replace(" ", "_"), first)
            self.view.insert(tk.INSERT, "\n")

    def read(self):
        self.source = Source(os.path.join(self.main.absdirpath,
                                          constants.REFERENCES_DIRNAME))
        self.references = [t for t in self.source.all_texts if "id" in t]
        self.references_lookup = dict([(r["id"], r) for r in self.references])

    def add_manually(self):
        raise NotImplementedError

    def import_bibtex(self):
        bibtex = BibtexImport(self.view)
        if not bibtex.result:
            return
        library = bibtexparser.parse_string(bibtex.result["bibtex"])
        entries = list(library.entries)
        if len(entries) > 1:
            tk_messagebox.showerror(
                parent=self.view,
                title="Error",
                message="More than one BibTeX entry in data.")
            return
        elif len(entries) == 0:
            tk_messagebox.showerror(
                parent=self.view,
                title="Error",
                message="No BibTeX entry in data.")
            return
        entry = entries[0]
        authors = entry.fields_dict["author"].value
        authors = " ".join([s.strip() for s in authors.split("\n")])
        authors = LaTexAccents.AccentConverter().decode_Tex_Accents(authors)
        authors = [a.strip() for a in authors.split(" and ")]
        name = authors[0].split(",")[0].strip() + " " + entry.fields_dict["year"].value
        try:
            text = self.source.create_text(name)
        except ValueError as error:
            tk_messagebox.showerror(
                parent=self.view,
                title="Error",
                message=str(error))
            return
        text["id"] = name
        text["type"] = entry.entry_type
        text["authors"] = authors
        abstract = ""
        for key, field in entry.fields_dict.items():
            if key == "abstract":
                abstract = " ".join(field.value.split())
            elif key == "author":
                pass
            else:
                text[key] = field.value
        text.write(abstract)
        self.references.append(text)
        self.references_lookup[text["id"]] = text
        self.display()


class BibtexImport(tk_simpledialog.Dialog):
    "Simple dialog window for importing a BibTeX entry."

    def __init__(self, toplevel):
        self.result = None
        super().__init__(toplevel, title="Import BibTeX")

    def body(self, body):
        label = ttk.Label(body, text="Id")
        label.grid(row=0, column=0, padx=4, sticky=tk.E)
        self.id_entry = tk.Entry(body, width=50)
        self.id_entry.grid(row=0, column=1)

        label = ttk.Label(body, text="BibTeX")
        label.grid(row=1, column=0, padx=4, sticky=(tk.E, tk.N))
        self.bibtex_text = tk.Text(body, width=50)
        self.bibtex_text.grid(row=1, column=1)
        return self.bibtex_text

    def apply(self):
        self.result = dict(id=self.id_entry.get(),
                           bibtex=self.bibtex_text.get("1.0", tk.END))
