"Viewer for the references list."

from icecream import ic

import functools
import os

import tkinter as tk
import tkinter.messagebox
import tkinter.ttk

import bibtexparser

import constants
import utils
from utils import Tr

from source import Source
from base_viewer import BaseViewer


class ReferencesViewer(BaseViewer):
    "Viewer for the references list."

    def __init__(self, parent, main):
        super().__init__(parent, main)
        self.read()

    def view_create(self, parent):
        self.frame = tk.ttk.Frame(parent)
        self.frame.pack(fill=tk.BOTH, expand=True)
        self.actions_frame = tk.ttk.Frame(self.frame, padding=6)
        self.actions_frame.pack(fill=tk.X)
        self.actions_frame.columnconfigure(0, weight=1)
        self.actions_frame.columnconfigure(1, weight=1)

        button = tk.ttk.Button(self.actions_frame,
                               text=Tr("Import BibTeX"),
                               padding=4,
                               command=self.import_bibtex)
        button.grid(row=0, column=0)

        button = tk.ttk.Button(self.actions_frame,
                               text=Tr("Add manually"),
                               padding=4,
                               command=self.add_manually)
        button.grid(row=0, column=1)

        self.result_frame = tk.ttk.Frame(self.frame)
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
        self.scroll_y = tk.ttk.Scrollbar(self.result_frame,
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
        view.tag_configure(constants.LINK,
                           font=constants.FONT_SMALL,
                           foreground=constants.LINK_COLOR,
                           underline=True)
        view.tag_configure(constants.REFERENCE, 
                           spacing1=constants.REFERENCE_SPACING,
                           lmargin2=constants.REFERENCE_INDENT)
        view.tag_configure(constants.XREF,
                           font=constants.FONT_SMALL,
                           foreground=constants.XREF_COLOR,
                           lmargin1=2 * constants.REFERENCE_INDENT,
                           lmargin2=2 * constants.REFERENCE_INDENT,
                           underline=True)

    def display(self):
        self.display_wipe()
        self.references_pos = dict() # Key: reference id; value: position here.
        self.highlighted = None  # Currently highlighted range.
        texts_pos = dict()  # Position in the source text.
        for text in self.main.source.all_texts:
            for id, positions in text.viewer.references.items():
                texts_pos.setdefault(id,dict())[text.fullname] = list(sorted(positions))

        for reference in self.references:
            first = self.view.index(tk.INSERT)
            self.references_pos[reference["id"]] = first
            self.view.insert(tk.INSERT, reference["id"], (constants.BOLD, ))

            # Get the texts that use this reference.
            fullnames = texts_pos.get(reference["id"])

            # Button for reference edit.
            command = functools.partial(self.main.open_reference_editor,
                                        reference=reference)
            button = tk.ttk.Button(self.view, text=Tr("Edit"), command=command)
            self.view.window_create(tk.INSERT, window=button, padx=6)

            # Button for reference delete; only if not referred to from texts.
            if not fullnames:
                command = functools.partial(self.reference_delete, reference=reference)
                button = tk.ttk.Button(self.view, text=Tr("Delete"), command=command)
                self.view.window_create(tk.INSERT, window=button, padx=6)

            self.view.insert(tk.INSERT, utils.shortname(reference["authors"][0]))
            number = min(len(reference["authors"]), constants.REFERENCE_MAX_AUTHORS)
            for author in reference["authors"][1:number-1]:
                self.view.insert(tk.INSERT, ", ")
                self.view.insert(tk.INSERT, utils.shortname(author))
            if len(reference["authors"]) > constants.REFERENCE_MAX_AUTHORS:
                self.view.insert(tk.INSERT, " ...")
            if len(reference["authors"]) > 1:
                self.view.insert(tk.INSERT, " & ")
                self.view.insert(tk.INSERT, utils.shortname(reference["authors"][-1]))
            self.view.insert(tk.INSERT, " ")

            if reference["type"] == "article":
                self.view.insert(tk.INSERT, f"({reference['year']}). ")
                try:
                    self.view.insert(tk.INSERT, reference["title"].strip(".") + ". ")
                except KeyError:
                    pass
                try:
                    self.view.insert(tk.INSERT,
                                     reference["journal"],
                                     (constants.ITALIC, ))
                except KeyError:
                    pass
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

            elif reference["type"] == "book":
                self.view.insert(tk.INSERT, f"({reference['year']}). ")
                self.view.insert(tk.INSERT, reference["title"].strip(".") + ". ",
                                 (constants.ITALIC, ))
                try:
                    self.view.insert(tk.INSERT, f"{reference['publisher']}. ")
                except KeyError:
                    pass

            elif reference["type"] == "link":
                raise NotImplementedError

            # Links for all types of references.
            any_item = False
            for key, label, template in constants.REFERENCE_LINKS:
                try:
                    value = reference[key]
                    if any_item:
                        self.view.insert(tk.INSERT, ", ")
                    start = self.view.index(tk.INSERT)
                    self.view.insert(tk.INSERT, f"{label} {value}")
                    self.link_create(template.format(value=value),
                                     title=value,
                                     first=start,
                                     last=self.view.index(tk.INSERT))
                    any_item = True
                except KeyError:
                    pass

            # This is done at this stage to avoid mark from being moved by insert.
            self.view.mark_set(reference["id"].replace(" ", "_"), first)
            self.view.tag_add(constants.REFERENCE, first, tk.INSERT)

            if fullnames:
                for fullname, positions in sorted(fullnames.items()):
                    self.view.insert(tk.INSERT, "\n")
                    positions = sorted(positions, key= lambda p: int(p[:p.index(".")]))
                    self.xref_create(fullname, positions[0], constants.REFERENCE)
                    for i, position in enumerate(positions[1:], start=2):
                        self.view.insert(tk.INSERT, ", ")
                        self.xref_create(str(i), position, constants.REFERENCE)
            self.view.insert(tk.INSERT, "\n")

    def highlight(self, refid):
        "Highlight and show the reference; show this pane."
        try:
            first = self.references_pos[refid]
        except KeyError:
            return
        if self.highlighted:
            self.view.tag_remove(constants.HIGHLIGHT, *self.highlighted)
        last = self.view.index(first + " lineend")
        self.view.tag_add(constants.HIGHLIGHT, first, last)
        self.highlighted = (first, last)
        self.view.see(first)
        self.main.meta_notebook.select(self.tabid)

    def read(self):
        self.source = Source(os.path.join(self.main.absdirpath,
                                          constants.REFERENCES_DIRNAME))
        self.references = [t for t in self.source.all_texts if "id" in t]
        self.references.sort(key=lambda r: r["id"])
        self.references_lookup = dict([(r["id"], r) for r in self.references])

    def import_bibtex(self):
        bibtex = BibtexImport(self)
        if bibtex.result is None:
            return
        reference = bibtex.result
        reference.read()
        self.reference_add(reference)
        self.display()

    def add_manually(self):
        add_manually = AddManually(self)
        if add_manually.result is None:
            return
        reference = add_manually.result
        reference.read()
        self.reference_add(reference)
        self.display()
        self.main.open_reference_editor(reference)

    def get_unique_id(self, author, year):
        name = author.split(",")[0].strip()
        for char in [""] + list("abcdefghijklmnopqrstuvxyz"):
            id = f"{name} {year}{char}"
            if self.source.get(id) is None:
                return id
        return None

    def reference_add(self, reference):
        self.references.append(reference)
        self.references.sort(key=lambda r: r["id"])
        self.references_lookup[reference["id"]] = reference

    def reference_delete(self, reference):
        if not tk.messagebox.askokcancel(
                parent=self.frame,
                title=Tr("Delete?"),
                message=Tr("Really delete reference?")):
            return
        self.references.remove(reference)
        self.references_lookup.pop(reference["id"])
        reference.delete()
        self.display()


class BibtexImport(tk.simpledialog.Dialog):
    "Dialog window for importing a BibTeX entry."

    def __init__(self, viewer):
        self.viewer = viewer
        self.result = None
        super().__init__(viewer.frame, title=Tr("Import BibTeX"))

    def body(self, body):
        label = tk.ttk.Label(body, text=Tr("BibTeX"))
        label.grid(row=1, column=0, padx=4, sticky=(tk.E, tk.N))
        self.bibtex_text = tk.Text(body, width=50)
        self.bibtex_text.grid(row=1, column=1)
        return self.bibtex_text

    def validate(self):
        library = bibtexparser.parse_string(self.bibtex_text.get("1.0", tk.END))
        entries = list(library.entries)
        if len(entries) > 1:
            tk.messagebox.showerror(
                parent=self.view,
                title=Tr("Error"),
                message=Tr("More than one BibTeX entry in data."))
            return False
        elif len(entries) == 0:
            tk.messagebox.showerror(
                parent=self.view,
                title=Tr("Error"),
                message=Tr("No BibTeX entry in data."))
            return False
        entry = entries[0]
        authors = utils.cleanup(entry.fields_dict["author"].value)
        authors = [a.strip() for a in authors.split(" and ")]
        year = entry.fields_dict["year"].value.strip()
        id = self.viewer.get_unique_id(authors[0], year)
        if id is None:
            tk.messagebox.showerror(parent=self,
                                    title=Tr("Error"),
                                    message=Tr("Could not create unique id for reference."))
            return False
        self.result = dict(id=id, type=entry.entry_type, authors=authors, year=year)
        for key, field in entry.fields_dict.items():
            if key == "author":
                continue
            value = utils.cleanup(field.value).strip()
            if value:
                self.result[key] = value
        return True

    def apply(self):
        text = self.viewer.source.create_text(self.result["id"])
        abstract = self.result.pop("abstract", None)
        for key, value in self.result.items():
            text[key] = value
        if abstract:
            text.write("**Abstract**\n\n" + abstract)
        else:
            text.write()
        self.result = text


class AddManually(tk.simpledialog.Dialog):
    "Dialog window for creating a reference entry manually."

    def __init__(self, viewer):
        self.viewer = viewer
        self.result = None
        super().__init__(viewer.frame, title=Tr("Add manually"))

    def body(self, body):
        label = tk.ttk.Label(body, text=Tr("Author"))
        label.grid(row=0, column=0, padx=4, sticky=tk.E)
        self.author_entry = tk.Entry(body, width=40)
        self.author_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))

        label = tk.ttk.Label(body, text=Tr("Year"))
        label.grid(row=1, column=0, padx=4, sticky=tk.E)
        self.year_entry = tk.Entry(body, width=8)
        self.year_entry.grid(row=1, column=1, sticky=(tk.W, tk.E))
        self.year_entry.bind("<Return>", self.ok)

        frame = tk.Frame(body)
        frame.grid(row=2, column=1, sticky=(tk.W, tk.E))
        self.type_var = tk.StringVar(value="article")
        tk.ttk.Radiobutton(frame,
                           text=Tr("Article"),
                           value="article",
                           variable=self.type_var).pack(anchor=tk.NW, padx=4)
        tk.ttk.Radiobutton(frame,
                           text=Tr("Book"), 
                           value="book",
                           variable=self.type_var).pack(anchor=tk.NW, padx=4)
        tk.ttk.Radiobutton(frame,
                           text=Tr("Link"),
                           value="link",
                           variable=self.type_var).pack(anchor=tk.NW, padx=4)

        return self.author_entry
    
    def validate(self):
        author = self.author_entry.get().strip()
        year = self.year_entry.get().strip()
        id = self.viewer.get_unique_id(author, year)
        if id is None:
            tk.messagebox.showerror(parent=self,
                                    title=Tr("Error"),
                                    message=Tr("Could not create unique id for reference."))
            return False
        self.result = dict(id=id, type=self.type_var.get(), authors=[author], year=year)
        return True

    def apply(self):
        text = self.viewer.source.create_text(self.result["id"])
        for key, value in self.result.items():
            text[key] = value
        text.write()
        self.result = text
