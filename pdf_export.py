"PDF export."

from icecream import ic

import copy
import datetime
import io
import os

import tkinter as tk

import fpdf

import utils
import constants
from utils import Tr

FONT_FAMILY = "Helvetica"

def mm(points):
    return points / 2.83465

class Exporter:
    "HTML exporter."

    def __init__(self, main, source, config):
        self.main = main
        self.source = source
        self.config = config

    def write(self):
        self.indexed = {}  # Key: canonical; value: dict(id, fullname)
        self.indexed_count = 0
        self.referenced = {}  # Key: reference id; value: dict(id, fullname)
        self.referenced_count = 0
        self.footnotes = {}  # Key: fullname; value: dict(label, ast_children)
        self.outputs = []

        self.pdf = fpdf.FPDF()
        self.pdf.add_page()

        self.write_title_page()
        self.write_toc()
        self.current_text = None
        for item in self.source.items:
            if item.is_section:
                self.write_section(item, level=1)
            else:
                self.write_text(item, level=1)
        self.write_references()
        self.write_indexed()

        self.pdf.output(os.path.join(self.config["dirpath"], self.config["filename"]))

    def write_title_page(self):
        self.pdf.set_font(FONT_FAMILY, "B", constants.FONT_TITLE_SIZE)
        self.pdf.write(text=self.main.title)
        if self.main.subtitle:
            self.pdf.ln(1.5 *mm(constants.FONT_TITLE_SIZE))
            self.pdf.set_font(FONT_FAMILY, "B", constants.FONT_LARGE_SIZE + 10)
            self.pdf.write(text=self.main.subtitle)
        self.pdf.ln(2 * mm(constants.FONT_LARGE_SIZE + 10))
        for author in self.main.authors:
            self.pdf.set_font(FONT_FAMILY, "B", constants.FONT_LARGE_SIZE + 5)
            self.pdf.write(text=author)
            self.pdf.ln(mm(constants.FONT_LARGE_SIZE + 5))
        self.pdf.ln(2 * mm(constants.FONT_LARGE_SIZE + 10))
        self.pdf.set_font(FONT_FAMILY, "", constants.FONT_NORMAL_SIZE)
        status = str(min([t.status for t in self.source.all_texts] + [max(constants.STATUSES)]))
        self.pdf.write(text=f'{Tr("Status")}: {Tr(status)}')
        self.pdf.ln()
        self.pdf.ln()

        now = datetime.datetime.now().strftime(constants.TIME_ISO_FORMAT)
        self.pdf.write(text=f'{Tr("Created")}: {now}')
        self.pdf.ln()
        self.pdf.ln()

    def write_toc(self):
        self.pdf.set_font(FONT_FAMILY, "", constants.FONT_NORMAL_SIZE)
        for item in self.source.items:
            self.pdf.write(text=item.fullname)
            self.pdf.ln()
        self.pdf.write(text=Tr("References"))
        self.pdf.ln()
        self.pdf.write(text=Tr("Index"))
        self.pdf.ln()

    def write_section(self, section, level):
        if level <= self.config["page_break_level"]:
            self.pdf.add_page()
        self.write_heading(section.name, level)
        for item in section.items:
            if item.is_section:
                self.write_section(item, level=level + 1)
            else:
                self.write_text(item, level=level + 1)

    def write_text(self, text, level):
        if level <= self.config["page_break_level"]:
            self.pdf.add_page()
        if text.get("display_heading", True):
            self.write_heading(text.name, level)
        self.current_text = text
        self.pdf.set_font(FONT_FAMILY, "", constants.FONT_NORMAL_SIZE)
        self.render(text.ast)
        # Footnotes at end of the text.
        try:
            footnotes = self.footnotes[text.fullname]
        except KeyError:
            return
        self.pdf.ln()
        self.pdf.write(text=constants.EM_DASH * 10)
        self.pdf.ln()
        self.write_heading(Tr("Footnotes"), 6)
        for label, entry in sorted(footnotes.items()):
            self.pdf.set_font(FONT_FAMILY, "B", constants.FONT_NORMAL_SIZE)
            self.pdf.write(text=label)
            self.pdf.set_font(FONT_FAMILY, "", constants.FONT_NORMAL_SIZE)
            self.pdf.write(text="  ")
            for child in entry["ast_children"]:
                self.render(child)
            self.pdf.ln(1.5 * mm(constants.FONT_NORMAL_SIZE))

    def write_heading(self, title, level):
        level = min(level, constants.MAX_H_LEVEL)
        self.pdf.set_font(FONT_FAMILY, "B", constants.H_LOOKUP[level]["font"][1])
        self.pdf.write(text=title)
        self.pdf.set_font(FONT_FAMILY, "", constants.FONT_NORMAL_SIZE)

    def write_references(self):
        self.pdf.add_page()
        self.write_heading(Tr("References"), 1)
        lookup = self.main.references_viewer.reference_lookup
        for refid, entries in sorted(self.referenced.items()):
            reference = lookup[refid]
            self.pdf.set_font(FONT_FAMILY, "B", constants.FONT_NORMAL_SIZE)
            self.pdf.write(text=refid)
            self.pdf.set_font(FONT_FAMILY, "", constants.FONT_NORMAL_SIZE)
            self.pdf.write(text="  ")
            self.write_reference_authors(reference)
            try:
                method = getattr(self, f"write_reference_{reference['type']}")
            except AttributeError:
                ic("unknown", reference["type"])
            else:
                method(reference)
            self.write_reference_external_links(reference)
            self.pdf.ln(1.5 * mm(constants.FONT_NORMAL_SIZE))

    def write_reference_authors(self, reference):
        self.pdf.set_font(FONT_FAMILY, "", constants.FONT_NORMAL_SIZE)
        count = len(reference["authors"])
        for pos, author in enumerate(reference["authors"]):
            if pos > 0:
                if pos == count - 1:
                    self.pdf.write(text=" & ")
                else:
                    self.pdf.write(text=", ")
            self.pdf.write(text=utils.shortname(author))

    def write_reference_article(self, reference):
        self.pdf.set_font(FONT_FAMILY, "", constants.FONT_NORMAL_SIZE)
        self.pdf.write(text=f"({reference['year']}) ")
        try:
            self.pdf.write(text=reference["title"].strip(".") + ". ")
        except KeyError:
            pass
        self.pdf.set_font(FONT_FAMILY, "I", constants.FONT_NORMAL_SIZE)
        try:
            self.pdf.write(text=reference["journal"])
        except KeyError:
            pass
        self.pdf.set_font(FONT_FAMILY, "", constants.FONT_NORMAL_SIZE)
        try:
            self.pdf.write(text=reference["volume"])
        except KeyError:
            pass
        else:
            self.pdf.set_font(FONT_FAMILY, "", constants.FONT_NORMAL_SIZE)
            try:
                self.pdf.write(text=reference["number"])
            except KeyError:
                pass
        self.pdf.set_font(FONT_FAMILY, "", constants.FONT_NORMAL_SIZE)
        try:
            self.pdf.write(text=f": pp. {reference['pages'].replace('--', '-')}.")
        except KeyError:
            pass

    def write_reference_book(self, reference):
        self.pdf.set_font(FONT_FAMILY, "", constants.FONT_NORMAL_SIZE)
        self.pdf.write(text=f"({reference['year']}).")
        self.pdf.set_font(FONT_FAMILY, "I", constants.FONT_NORMAL_SIZE)
        self.pdf.write(text=reference['title'].strip('.') + '. ')
        self.pdf.set_font(FONT_FAMILY, "", constants.FONT_NORMAL_SIZE)
        try:
            self.pdf.write(text=f"{reference['publisher']}.")
        except KeyError:
            pass

    def write_reference_link(self, reference):
        self.pdf.set_font(FONT_FAMILY, "", constants.FONT_NORMAL_SIZE)
        self.pdf.write(text=f"({reference['year']}).")
        try:
            self.pdf.write(text=reference["title"].strip(".") + ". ")
        except KeyError:
            pass
        try:
            self.pdf.write(text=f'<a href="{reference["url"]}"><{reference["title"]}</a>')
        except KeyError:
            pass
        try:
            self.pwd.write(text=f"Accessed {reference['accessed']}.")
        except KeyError:
            pass

    def write_reference_external_links(self, reference):
        self.pdf.set_font(FONT_FAMILY, "", constants.FONT_NORMAL_SIZE)
        any_item = False
        for key, label, template in constants.REFERENCE_LINKS:
            try:
                value = reference[key]
                if any_item:
                    self.pdf.write(", ")
                url = template.format(value=value)
                self.pdf.write(text=f'<a target="_blank" href="{url}">{label}:{value}</a>')
                any_item = True
            except KeyError:
                pass

    def write_indexed(self):
        self.pdf.add_page()
        self.write_heading(Tr("Index"), 1)
        items = sorted(self.indexed.items(), key=lambda i: i[0].lower())
        for canonical, entries in items:
            self.pdf.set_font(FONT_FAMILY, "B", constants.FONT_NORMAL_SIZE)
            self.pdf.write(text=canonical)
            self.pdf.set_font(FONT_FAMILY, "", constants.FONT_NORMAL_SIZE)
            entries.sort(key=lambda e: e["ordinal"])
            for entry in entries:
                self.pdf.write(text=entry["fullname"])
                if entry is not entries[-1]:
                    self.pdf.write(text=", ")
            self.pdf.ln()
            self.pdf.ln()

    def render(self, ast):
        try:
            method = getattr(self, f"render_{ast['element']}")
        except AttributeError:
            ic("Could not handle ast", ast)
        else:
            method(ast)

    def render_document(self, ast):
        for child in ast["children"]:
            self.render(child)

    def render_paragraph(self, ast):
        self.pdf.ln()
        for child in ast["children"]:
            self.render(child)
        self.pdf.ln()

    def render_raw_text(self, ast):
        line = ast["children"]
        if not type(line) == str:
            ic("could not handle", ast)
            return
        self.pdf.write(text=line)

    def render_blank_line(self, ast):
        pass

    def render_quote(self, ast):
        self.pdf.ln()
        self.pdf.set_font("Times", "", constants.FONT_NORMAL_SIZE)
        for child in ast["children"]:
            self.render(child)
        self.pdf.set_font(FONT_FAMILY, "", constants.FONT_NORMAL_SIZE)
        self.pdf.ln()

    def render_code_span(self, ast):
        self.pdf.set_font("Courier", "", constants.FONT_NORMAL_SIZE)
        self.pdf.write(text=ast["children"])
        self.pdf.set_font(FONT_FAMILY, "", constants.FONT_NORMAL_SIZE)
        
    def render_code_block(self, ast):
        self.pdf.ln()
        self.pdf.set_font("Courier", "", constants.FONT_NORMAL_SIZE)
        for child in ast["children"]:
            self.render(child)
        self.pdf.set_font(FONT_FAMILY, "", constants.FONT_NORMAL_SIZE)
        self.pdf.ln()

    def render_fenced_code(self, ast):
        self.pdf.ln()
        self.pdf.set_font("Courier", "", constants.FONT_NORMAL_SIZE)
        for child in ast["children"]:
            self.render(child)
        self.pdf.set_font(FONT_FAMILY, "", constants.FONT_NORMAL_SIZE)
        self.pdf.ln()

    def render_emphasis(self, ast):
        self.pdf.set_font(FONT_FAMILY, "I", constants.FONT_NORMAL_SIZE)
        for child in ast["children"]:
            self.render(child)
        self.pdf.set_font(FONT_FAMILY, "", constants.FONT_NORMAL_SIZE)

    def render_strong_emphasis(self, ast):
        self.pdf.set_font(FONT_FAMILY, "B", constants.FONT_NORMAL_SIZE)
        for child in ast["children"]:
            self.render(child)
        self.pdf.set_font(FONT_FAMILY, "", constants.FONT_NORMAL_SIZE)

    def render_thematic_break(self, ast):
        self.pdf.ln()
        self.pdf.write(text=constants.EM_DASH * 10)
        self.pdf.ln()

    def render_link(self, ast):
        for child in ast["children"]:
            self.render(child)

    def render_list(self, ast):
        pass
        # if ast["ordered"]:
        #     self.output("<ol>")
        # else:
        #     self.output("<ul>")
        # for child in ast["children"]:
        #     self.render(child)
        # if ast["ordered"]:
        #     self.output("</ol>")
        # else:
        #     self.output("</ul>")

    def render_list_item(self, ast):
        pass
        # self.output("<li>")
        # for child in ast["children"]:
        #     self.render(child)
        # self.output("</li>")

    def render_indexed(self, ast):
        entries = self.indexed.setdefault(ast["canonical"], [])
        self.indexed_count += 1
        id = f"_Indexed-{self.indexed_count}"
        entries.append(dict(id=id,
                            fullname=self.current_text.fullname,
                            ordinal=self.current_text.ordinal,
                            )
                       )
        self.pdf.set_font(FONT_FAMILY, "U", constants.FONT_NORMAL_SIZE)
        self.pdf.write(text=ast["term"])
        self.pdf.set_font(FONT_FAMILY, "", constants.FONT_NORMAL_SIZE)

    def render_footnote_ref(self, ast):
        pass
        # entries = self.footnotes.setdefault(self.current_text.fullname, {})
        # label = int(ast["label"])
        # id = f"_footnote-{self.current_text.fullname}-{label}"
        # entries[label] = dict(label=label, id=id)
        # self.output(f'<sup><strong><a href="#{id}">{ast["label"]}</a></strong></sup>')

    def render_footnote_def(self, ast):
        pass
        # label = int(ast["label"])
        # self.footnotes[self.current_text.fullname][label]["ast_children"] = ast[
        #     "children"
        # ]

    def render_reference(self, ast):
        entries = self.referenced.setdefault(ast["reference"], [])
        self.referenced_count += 1
        id = f"_Referenced-{self.referenced_count}"
        entries.append(dict(id=id,
                            fullname=self.current_text.fullname,
                            ordinal=self.current_text.ordinal)
                       )
        self.pdf.set_font(FONT_FAMILY, "U", constants.FONT_NORMAL_SIZE)
        self.pdf.write(text=ast["reference"])
        self.pdf.set_font(FONT_FAMILY, "", constants.FONT_NORMAL_SIZE)


class Dialog(tk.simpledialog.Dialog):
    "Dialog to confirm or modify configuration before export."

    def __init__(self, master, source, config):
        self.source = source
        self.config = copy.deepcopy(config)
        self.result = None
        super().__init__(master, title=Tr("HTML export"))

    def body(self, body):
        row = 0
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_columnconfigure(2, weight=1)

        row += 1
        label = tk.ttk.Label(body, text=Tr("Directory"), padding=4)
        label.grid(row=row, column=0, sticky=tk.NE)
        self.dirpath_entry = tk.ttk.Entry(body, width=40)
        self.dirpath_entry.insert(0, self.config.get("dirpath") or os.getcwd())
        self.dirpath_entry.grid(row=row, column=1, sticky=tk.W)
        button = tk.ttk.Button(body, text=Tr("Choose"), command=self.change_dirpath)
        button.grid(row=row, column=3)

        row += 1
        label = tk.ttk.Label(body, text=Tr("Filename"))
        label.grid(row=row, column=0, padx=4, sticky=tk.NE)
        self.filename_entry = tk.ttk.Entry(body, width=40)
        self.filename_entry.insert(0, self.config.get("filename") or "book.pdf")
        self.filename_entry.grid(row=row, column=1, sticky=tk.W)

        row += 1
        label = tk.ttk.Label(body, text=Tr("Page break level"))
        label.grid(row=row, column=0, padx=4, sticky=tk.NE)
        self.page_break_level_var = tk.IntVar(value=min(self.config.get("page_break_level", 1), self.source.max_level))
        frame = tk.ttk.Frame(body)
        frame.grid(row=row, column=1, padx=4, sticky=tk.W)
        for level in range(1, self.source.max_level+1):
            button = tk.ttk.Radiobutton(frame,
                                        text=str(level),
                                        variable=self.page_break_level_var,
                                        value=level)
            button.pack(anchor=tk.W)


    def apply(self):
        self.config["dirpath"] = self.dirpath_entry.get().strip() or "."
        filename = self.filename_entry.get().strip() or constants.BOOK
        self.config["filename"] = os.path.splitext(filename)[0] + ".pdf"
        self.config["page_break_level"] = self.page_break_level_var.get()
        self.result = self.config

    def change_dirpath(self):
        dirpath = tk.filedialog.askdirectory(
            parent=self,
            title=Tr("Directory"),
            initialdir=self.config.get("dirpath") or os.getcwd(),
            mustexist=True,
        )
        if dirpath:
            self.dirpath_entry.delete(0, tk.END)
            self.dirpath_entry.insert(0, dirpath)
