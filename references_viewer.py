"Viewer for the references."

from icecream import ic

import functools
import os
import string

import tkinter as tk
import tkinter.messagebox
import tkinter.ttk

import bibtexparser

import constants
import utils
from utils import Tr

from source import Source
from viewer import Viewer


class ReferencesViewer(Viewer):
    "Viewer for the references."

    def __init__(self, parent, main):
        super().__init__(parent, main)
        self.read_references()

    def __str__(self):
        return "References"

    def view_create(self, parent):
        """Create an outer super-frame to contain the action buttons
        and the view frame.
        """
        self.super_frame = tk.ttk.Frame(parent)
        self.super_frame.pack(fill=tk.BOTH, expand=True)

        self.actions_frame = tk.ttk.Frame(self.super_frame, padding=6)
        self.actions_frame.pack(fill=tk.X)

        label = tk.ttk.Label(self.actions_frame, text=Tr("Add"))
        label.grid(row=0, column=0)
        self.actions_frame.columnconfigure(0, weight=1)

        button = tk.ttk.Button(
            self.actions_frame,
            text=Tr("BibTeX"),
            padding=4,
            command=self.import_bibtex,
        )
        button.grid(row=0, column=1)
        self.actions_frame.columnconfigure(1, weight=1)

        button = tk.ttk.Button(
            self.actions_frame,
            text=Tr("RIS"),
            padding=4,
            command=self.import_ris,
        )
        button.grid(row=0, column=2)
        self.actions_frame.columnconfigure(2, weight=1)

        button = tk.ttk.Button(
            self.actions_frame,
            text=Tr("Manually"),
            padding=4,
            command=self.add_manually,
        )
        button.grid(row=0, column=3)
        self.actions_frame.columnconfigure(3, weight=1)

        super().view_create(self.super_frame)

    def configure_tags(self):
        "Reconfigure and add tags."
        super().configure_tags()
        self.view.tag_configure(
            constants.LINK,
            lmargin1=2 * constants.REFERENCE_INDENT,
            lmargin2=2 * constants.REFERENCE_INDENT,
        )
        self.view.tag_configure(
            constants.REFERENCE,
            spacing1=constants.REFERENCE_SPACING,
            lmargin2=constants.REFERENCE_INDENT,
            foreground="black",
            underline=False,
        )
        self.view.tag_configure(
            constants.XREF,
            foreground=constants.XREF_COLOR,
            lmargin1=2 * constants.REFERENCE_INDENT,
            lmargin2=2 * constants.REFERENCE_INDENT,
            underline=True,
        )

    def bind_tags(self):
        "Remove tag binding that is irrelevant in this context."
        super().bind_tags()
        self.view.tag_unbind(constants.REFERENCE, "<Button-1>")
        self.view.tag_unbind(constants.REFERENCE, "<Enter>")
        self.view.tag_unbind(constants.REFERENCE, "<Leave>")

    def read_references(self):
        self.source = Source(
            os.path.join(self.main.absdirpath, constants.REFERENCES_DIRNAME)
        )
        self.reference_texts = [t for t in self.source.all_texts if "id" in t]
        self.reference_texts.sort(key=lambda r: r["id"].lower())
        self.reference_lookup = dict([(r["id"], r) for r in self.reference_texts])
        # This variable is already displayed, so needs to be updated.
        self.main.title_viewer.references_var.set(len(self.reference_texts))

    def display_heading(self):
        pass

    def display_initialize(self):
        super().display_initialize()
        self.reference_pos = {}  # Key: reference id; value: position here.
        self.texts_pos = {}  # Position in the source text.
        for text in self.main.source.all_texts:
            for id, positions in text.viewer.references.items():
                self.texts_pos.setdefault(id, {})[text.fullname] = list(
                    sorted(positions)
                )

    def display_view(self):
        for reference in self.reference_texts:
            first = self.view.index(tk.INSERT)
            self.reference_pos[reference["id"]] = first

            tag = f"{constants.REFERENCE_PREFIX}{reference['id']}".replace(" ", "_")
            self.view.tag_configure(
                tag, font=constants.FONT_BOLD, foreground=constants.REFERENCE_COLOR
            )
            self.view.insert(tk.INSERT, reference["id"], tag)
            self.view.insert(tk.INSERT, "  ")
            self.display_view_authors(reference)
            try:
                method = getattr(self, f"display_view_{reference['type']}")
            except AttributeError:
                ic("unknown", reference["type"])
            else:
                method(reference)
            # Done at this stage to avoid mark from being moved by insert.
            self.view.mark_set(reference["id"].replace(" ", "_"), first)
            self.view.tag_add(constants.REFERENCE, first, tk.INSERT)
            button = tk.ttk.Button(
                self.view_frame,
                text=Tr("Notes"),
                command=functools.partial(self.main.open_reference_editor, self, reference))
            self.view.window_create(tk.INSERT, window=button)
            self.display_view_external_links(reference)
            self.display_view_xrefs(reference)
            self.view.insert(tk.INSERT, "\n")

    def display_view_authors(self, reference):
        self.view.insert(tk.INSERT, utils.shortname(reference["authors"][0]))
        number = min(len(reference["authors"]), constants.REFERENCE_MAX_AUTHORS)
        for author in reference["authors"][1 : number - 1]:
            self.view.insert(tk.INSERT, ", ")
            self.view.insert(tk.INSERT, utils.shortname(author))
        if len(reference["authors"]) > constants.REFERENCE_MAX_AUTHORS:
            self.view.insert(tk.INSERT, " ...")
        if len(reference["authors"]) > 1:
            self.view.insert(tk.INSERT, " & ")
            self.view.insert(tk.INSERT, utils.shortname(reference["authors"][-1]))
        self.view.insert(tk.INSERT, " ")

    def display_view_article(self, reference):
        self.view.insert(tk.INSERT, f"({reference['year']}). ")
        try:
            self.view.insert(tk.INSERT, reference["title"].strip(".") + ". ")
        except KeyError:
            pass
        try:
            self.view.insert(tk.INSERT, reference["journal"], constants.ITALIC)
        except KeyError:
            pass
        try:
            self.view.insert(tk.INSERT, f" {reference['volume']}")
        except KeyError:
            pass
        else:
            try:
                self.view.insert(tk.INSERT, f" ({reference['number']})")
            except KeyError:
                pass
            self.view.insert(tk.INSERT, ": ")
        try:
            self.view.insert(
                tk.INSERT, f"pp. {reference['pages'].replace('--', '-')}. "
            )
        except KeyError:
            pass

    def display_view_book(self, reference):
        self.view.insert(tk.INSERT, f"({reference['year']}). ")
        self.view.insert(
            tk.INSERT, reference["title"].strip(".") + ". ", constants.ITALIC
        )
        try:
            self.view.insert(tk.INSERT, f"{reference['publisher']}. ")
        except KeyError:
            pass

    def display_view_link(self, reference):
        self.view.insert(tk.INSERT, f"({reference['year']}). ")
        try:
            self.view.insert(tk.INSERT, reference["title"].strip(".") + ". ")
        except KeyError:
            pass
        try:
            start = self.view.index(tk.INSERT)
            self.view.insert(tk.INSERT, reference["url"])
            self.link_create(
                url=reference["url"],
                title=reference["title"],
                first=start,
                last=self.view.index(tk.INSERT),
            )
        except KeyError:
            pass
        try:
            self.view.insert(tk.INSERT, f" Accessed {reference['accessed']}.")
        except KeyError:
            pass

    def display_view_external_links(self, reference):
        links = []
        for key, label, template in constants.REFERENCE_LINKS:
            try:
                value = reference[key]
                text = f"{label}:{value}"
                url = template.format(value=value)
                links.append((value, text, url))
            except KeyError:
                pass
        if not links:
            return
        first = self.view.index(tk.INSERT)
        self.view.insert(tk.INSERT, "\n")
        after_first = False
        for value, text, url in links:
            if after_first:
                self.view.insert(tk.INSERT, ", ")
            else:
                after_first = True
            start = self.view.index(tk.INSERT)
            self.view.insert(tk.INSERT, text)
            self.link_create(
                url=url,
                title=value,
                first=start,
                last=self.view.index(tk.INSERT),
            )

    def display_view_xrefs(self, reference):
        fullnames = self.texts_pos.get(reference["id"]) or {}
        reference["orphan"] = not fullnames
        if not fullnames:
            return
        self.view.insert(tk.INSERT, "\n")
        after_first = False
        for fullname, positions in sorted(fullnames.items()):
            positions = sorted(positions, key=lambda p: int(p[: p.index(".")]))
            for position in positions:
                if after_first:
                    self.view.insert(tk.INSERT, ", ")
                else:
                    after_first = True
                self.xref_create(fullname, position, constants.REFERENCE)

    def highlight(self, refid):
        "Highlight and ensure that the reference and this pane is visible."
        try:
            first = self.reference_pos[refid]
        except KeyError:
            return
        if self.highlighted:
            self.view.tag_remove(constants.HIGHLIGHT, *self.highlighted)
        last = self.view.index(first + " lineend")
        self.view.tag_add(constants.HIGHLIGHT, first, last)
        self.highlighted = (first, last)
        self.view.see(first)
        self.main.meta_notebook.select(self.tabid)

    def import_bibtex(self):
        bibtex = BibtexImport(self)
        if bibtex.result is None:
            return
        reference = bibtex.result
        reference.read()
        self.reference_add(reference)
        self.display()

    def import_ris(self):
        ris = RisImport(self)
        if ris.result is None:
            return
        reference = ris.result
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
        self.main.open_reference_editor(self, reference)

    def get_unique_id(self, author, year):
        if not year:
            return None
        name = author.split(",")[0].strip()
        for char in [""] + list("abcdefghijklmnopqrstuvxyz"):
            id = f"{name} {year}{char}"
            if self.source.get(id) is None:
                return id
        return None

    def reference_add(self, reference):
        self.reference_texts.append(reference)
        self.reference_texts.sort(key=lambda r: r["id"])
        self.reference_lookup[reference["id"]] = reference
        # This is already displayed, so needs to be updated.
        self.main.title_viewer.references_var.set(len(self.reference_texts))


class BibtexImport(tk.simpledialog.Dialog):
    "Dialog window for importing a BibTeX entry."

    def __init__(self, viewer):
        self.viewer = viewer
        self.result = None
        super().__init__(viewer.view_frame, title=Tr("Add BibTeX"))

    def body(self, body):
        label = tk.ttk.Label(body, text=Tr("BibTeX"))
        label.grid(row=1, column=0, padx=4, sticky=(tk.E, tk.N))
        self.bibtex_text = tk.Text(body, width=80)
        self.bibtex_text.grid(row=1, column=1)
        return self.bibtex_text

    def validate(self):
        library = bibtexparser.parse_string(self.bibtex_text.get("1.0", tk.END))
        entries = list(library.entries)
        if len(entries) > 1:
            tk.messagebox.showerror(
                parent=self.viewer.view_frame,
                title="Error",
                message="More than one BibTeX entry in data.",
            )
            return False
        elif len(entries) == 0:
            tk.messagebox.showerror(
                parent=self.viewer.view_frame,
                title="Error",
                message="No BibTeX entry in data.",
            )
            return False
        entry = entries[0]
        authors = utils.cleanup(entry.fields_dict["author"].value)
        authors = [a.strip() for a in authors.split(" and ")]
        year = entry.fields_dict["year"].value.strip()
        id = self.viewer.get_unique_id(authors[0], year)
        if id is None:
            tk.messagebox.showerror(
                parent=self,
                title="Error",
                message="Could not create unique id for reference.",
            )
            return False
        self.result = dict(id=id, type=entry.entry_type, authors=authors, year=year)
        for key, field in entry.fields_dict.items():
            if key == "author":
                continue
            value = utils.cleanup(field.value).strip()
            if value:
                self.result[key] = value
        # Split keywords into a list.
        try:
            self.result["keywords"] = [k.strip() for k in self.result["keywords"].split(";")]
        except KeyError:
            pass
        # Change month into date; sometimes has day number.
        try:
            month = self.result.pop("month")
            parts = month.split("#")
            if len(parts) == 2:
                month = constants.MONTHS[parts[1].strip().lower()]
                day = int("".join([c for c in parts[0] if c in string.digits]))
            else:
                month = constants.MONTHS[parts[0].strip().lower()]
                day = 0
            self.result["date"] = f"{year}-{month:02d}-{day:02d}"
        except (KeyError, ValueError):
            pass
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


class RisImport(tk.simpledialog.Dialog):
    "Dialog window for importing a RIS entry."

    def __init__(self, viewer):
        self.viewer = viewer
        self.result = None
        super().__init__(viewer.view_frame, title=Tr("Add RIS"))

    def body(self, body):
        label = tk.ttk.Label(body, text=Tr("RIS"))
        label.grid(row=1, column=0, padx=4, sticky=(tk.E, tk.N))
        self.ris_text = tk.Text(body, width=80)
        self.ris_text.grid(row=1, column=1)
        return self.ris_text

    def validate(self):
        text = self.ris_text.get("1.0", tk.END).strip()
        if not text:
            tk.messagebox.showerror(
                parent=self.viewer.view_frame,
                title="Error",
                message="No RIS entry in data.",
            )
            return False
        self.result = dict()
        for line in text.split("\n"):
            prefix = line[0:2]
            if prefix != "  ":
                code = prefix
            value = line[6:].rstrip()
            if code == "TY":
                if value == "BOOK":
                    self.result["type"] = "book"
                elif value == "JOUR":
                    self.result["type"] = "article"
                else:
                    ic(line)
            elif code == "TI":
                self.result.setdefault("title", []).append(value)
            elif code == "AU":
                self.result.setdefault("authors", []).append(value)
            elif code == "PY":
                self.result["year"] = value
            elif code == "AB":
                self.result.setdefault("abstract", []).append(value)
            elif code == "T2":
                self.result["journal"] = value
            elif code == "KW":
                self.result.setdefault("keywords", []).append(value)
            elif code == "DA":
                try:
                    parts = value.split("/")
                    self.result["date"] = f"{parts[0]}-{parts[1]:02d}-{parts[1]:02d}"
                except (IndexError, ValueError):
                    pass
            elif code == "SN":
                if self.result.get("type") == "book":
                    self.result["isbn"] = value
                elif self.result.get("type") == "article":
                    self.result["issn"] = value
            elif code == "SP":
                self.result["pages"] = value
            elif code == "PB":
                self.result["publisher"] = value
            elif code == "DO":
                self.result["doi"] = value
            elif code == "UR":
                self.result.setdefault("links", []).append(value)
        try:
            self.result["title"] = " ".join(self.result["title"])
        except KeyError:
            self.result["title"] = "[no title]"
        try:
            self.result["abstract"] = " ".join(self.result["abstract"])
        except KeyError:
            pass
        id = self.viewer.get_unique_id(self.result["authors"][0], self.result.get("year"))
        if id is None:
            tk.messagebox.showerror(
                parent=self,
                title="Error",
                message="Could not create unique id for reference.",
            )
            return False
        self.result["id"] = id
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
        super().__init__(viewer.view_frame, title=Tr("Add manually"))

    def body(self, body):
        label = tk.ttk.Label(body, text=Tr("Author"))
        label.grid(row=0, column=0, padx=4, sticky=tk.E)
        self.author_entry = tk.Entry(body, width=40)
        self.author_entry.grid(row=0, column=1, sticky=tk.W)

        label = tk.ttk.Label(body, text=Tr("Year"))
        label.grid(row=1, column=0, padx=4, sticky=tk.E)
        self.year_entry = tk.Entry(body)
        self.year_entry.grid(row=1, column=1, sticky=tk.W)
        self.year_entry.bind("<Return>", self.ok)

        frame = tk.Frame(body)
        frame.grid(row=2, column=1, sticky=(tk.W, tk.E))
        self.type_var = tk.StringVar(value=constants.ARTICLE)
        for type in constants.REFERENCE_TYPES:
            tk.ttk.Radiobutton(
                frame, text=Tr(type.capitalize()), value=type, variable=self.type_var
            ).pack(anchor=tk.NW, padx=4)

        return self.author_entry

    def validate(self):
        author = self.author_entry.get().strip()
        year = self.year_entry.get().strip()
        id = self.viewer.get_unique_id(author, year)
        if id is None:
            tk.messagebox.showerror(
                parent=self,
                title="Error",
                message="Could not create unique id for reference.",
            )
            return False
        self.result = dict(id=id, type=self.type_var.get(), authors=[author], year=year)
        return True

    def apply(self):
        text = self.viewer.source.create_text(self.result["id"])
        for key, value in self.result.items():
            text[key] = value
        text.write()
        self.result = text
