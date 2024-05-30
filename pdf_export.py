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

        self.pdf = fpdf.FPDF(format="a4", unit="pt")
        self.pdf.add_page()
        self.state = State(self.pdf)

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
        self.state.set(style="B", size=constants.FONT_TITLE_SIZE)
        self.state.ln()
        self.state.write(self.main.title)
        self.state.ln()
        self.state.reset()

        if self.main.subtitle:
            self.state.set(size=constants.FONT_LARGE_SIZE + 10)
            self.state.write(self.main.subtitle)
            self.state.ln()
            self.state.reset()

        self.state.set(size=constants.FONT_LARGE_SIZE + 5)
        self.state.ln()
        for author in self.main.authors:
            self.state.write(author)
            self.state.ln()
        self.state.reset()

        self.state.ln(3)
        status = str(min([t.status for t in self.source.all_texts] + [max(constants.STATUSES)]))
        self.state.write(f'{Tr("Status")}: {Tr(status)}')
        self.state.ln()

        now = datetime.datetime.now().strftime(constants.TIME_ISO_FORMAT)
        self.state.write(f'{Tr("Created")}: {now}')
        self.state.ln(2)

    def write_toc(self):
        self.state.set(line_height=1.5)
        for item in self.source.items:
            self.state.write(item.fullname)
            self.state.ln()
        self.state.write(Tr("References"))
        self.state.ln()
        self.state.write(Tr("Index"))
        self.state.ln()
        self.state.reset()

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
        self.render(text.ast)
        # Footnotes at end of the text.
        try:
            footnotes = self.footnotes[text.fullname]
        except KeyError:
            return
        self.state.ln()
        self.state.write(constants.EM_DASH * 10)
        self.state.ln()
        self.write_heading(Tr("Footnotes"), 6)
        for label, entry in sorted(footnotes.items()):
            self.state.set(style="B")
            self.state.write(label)
            self.state.reset()
            self.state.write("  ")
            for child in entry["ast_children"]:
                self.render(child)
            self.state.ln(2)

    def write_heading(self, title, level):
        level = min(level, constants.MAX_H_LEVEL)
        self.state.set(style="B", size=constants.H_LOOKUP[level]["font"][1])
        self.state.write(title)
        self.state.ln()
        self.state.reset()

    def write_references(self):
        self.pdf.add_page()
        self.write_heading(Tr("References"), 1)
        lookup = self.main.references_viewer.reference_lookup
        for refid, entries in sorted(self.referenced.items()):
            reference = lookup[refid]
            self.state.set(style="B")
            self.state.write(refid)
            self.state.reset()
            self.state.write("  ")
            self.write_reference_authors(reference)
            try:
                method = getattr(self, f"write_reference_{reference['type']}")
            except AttributeError:
                ic("unknown", reference["type"])
            else:
                method(reference)
            self.write_reference_external_links(reference)
            self.state.ln(2)

    def write_reference_authors(self, reference):
        count = len(reference["authors"])
        for pos, author in enumerate(reference["authors"]):
            if pos > 0:
                if pos == count - 1:
                    self.state.write(" & ")
                else:
                    self.state.write(", ")
            self.state.write(utils.shortname(author))

    def write_reference_article(self, reference):
        self.state.write(f"({reference['year']}) ")
        try:
            self.state.write(reference["title"].strip(".") + ". ")
        except KeyError:
            pass
        journal = reference.get("journal")
        if journal:
            self.state.set(style="I")
            self.statewrite(journal)
            self.state.reset()
        try:
            self.state.write(reference["volume"])
        except KeyError:
            pass
        else:
            try:
                self.state.write(reference["number"])
            except KeyError:
                pass
        try:
            self.state.write(f": pp. {reference['pages'].replace('--', '-')}.")
        except KeyError:
            pass

    def write_reference_book(self, reference):
        self.state.write(f"({reference['year']}).")
        self.state.set(style="I")
        self.state.write(reference['title'].strip('.') + '. ')
        self.state.reset()
        try:
            self.state.write(f"{reference['publisher']}.")
        except KeyError:
            pass

    def write_reference_link(self, reference):
        self.state.write(f"({reference['year']}).")
        try:
            self.state.write(reference["title"].strip(".") + ". ")
        except KeyError:
            pass
        try:
            self.state.write(f'<a href="{reference["url"]}"><{reference["title"]}</a>')
        except KeyError:
            pass
        try:
            self.state.write(f"Accessed {reference['accessed']}.")
        except KeyError:
            pass

    def write_reference_external_links(self, reference):
        any_item = False
        for key, label, template in constants.REFERENCE_LINKS:
            try:
                value = reference[key]
                if any_item:
                    self.state.write(", ")
                url = template.format(value=value)
                self.state.write(f'<a target="_blank" href="{url}">{label}:{value}</a>')
                any_item = True
            except KeyError:
                pass

    def write_indexed(self):
        self.pdf.add_page()
        self.write_heading(Tr("Index"), 1)
        items = sorted(self.indexed.items(), key=lambda i: i[0].lower())
        for canonical, entries in items:
            self.state.set(style="B")
            self.state.write(canonical)
            self.state.reset()
            self.state.write("  ")
            entries.sort(key=lambda e: e["ordinal"])
            for entry in entries:
                self.state.write(entry["fullname"])
                if entry is not entries[-1]:
                    self.state.write(", ")
            self.state.ln()

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
        self.state.ln()
        for child in ast["children"]:
            self.render(child)
        self.state.ln()

    def render_raw_text(self, ast):
        line = ast["children"]
        if not type(line) == str:
            ic("could not handle", ast)
            return
        self.state.write(line)

    def render_blank_line(self, ast):
        pass

    def render_quote(self, ast):
        self.state.ln()
        self.state.set(family="Times",
                       left_indent=constants.QUOTE_LEFT_INDENT,
                       right_indent=constants.QUOTE_RIGHT_INDENT)
        for child in ast["children"]:
            self.render(child)
        self.state.reset()
        self.state.ln()

    def render_code_span(self, ast):
        self.state.set(family="Courier")
        self.state.write(ast["children"])
        self.state.reset()
        
    def render_code_block(self, ast):
        self.state.ln()
        self.state.set(family="Courier", left_indent=constants.CODE_INDENT, line_height=1.2)
        for child in ast["children"]:
            self.render(child)
        self.state.reset()
        self.state.ln()

    def render_fenced_code(self, ast):
        self.state.ln()
        self.state.set(family="Courier", left_indent=constants.CODE_INDENT, line_height=1.2)
        for child in ast["children"]:
            self.render(child)
        self.state.reset()
        self.state.ln()

    def render_emphasis(self, ast):
        self.state.set(style="I")
        for child in ast["children"]:
            self.render(child)
        self.state.reset()

    def render_strong_emphasis(self, ast):
        self.state.set(style="B")
        for child in ast["children"]:
            self.render(child)
        self.state.reset()

    def render_thematic_break(self, ast):
        self.state.ln()
        self.state.write(constants.EM_DASH * 10)
        self.state.ln()

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
        self.state.set(style="U")
        self.state.write(ast["term"])
        self.state.reset()

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
        self.state.set(style="U")
        self.state.write(ast["reference"])
        self.state.reset()


class Current:
    "State value field."

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, obj, objtype=None):
        return obj.stack[-1][self.name]


class State:
    "Current style parameters state as a stack."

    family = Current()
    style = Current()
    size = Current()
    line_height = Current()
    left_indent = Current()
    right_indent = Current()

    def __init__(self, pdf):
        self.pdf = pdf
        self.stack = [dict(family=FONT_FAMILY,
                           style="",
                           size=constants.FONT_NORMAL_SIZE,
                           line_height=1.5,
                           left_indent=0,
                           right_indent=0,
                           )]
        self.pdf.set_font(family=self.family, style=self.style, size=self.size)
        self.l_margin=self.pdf.l_margin
        self.r_margin=self.pdf.r_margin

    def set(self, **kwargs):
        try:
            self.pdf.set_font(family=kwargs["family"])
        except KeyError:
            pass
        try:                    # Due to possible bug in fpdf2, size before style.
            self.pdf.set_font(size=kwargs["size"])
        except KeyError:
            pass
        try:
            self.pdf.set_font(style=kwargs["style"])
        except KeyError:
            pass
        try:
            value = kwargs["left_indent"]
        except KeyError:
            pass
        else:
            self.pdf.set_left_margin(self.l_margin + value)
        try:
            value = kwargs["right_indent"]
        except KeyError:
            pass
        else:
            self.pdf.set_right_margin(self.l_margin + value)
        self.stack.append(self.stack[-1].copy())
        self.stack[-1].update(kwargs)
        
    def reset(self):
        diff = dict([(k,v) for k, v in self.stack[-2].items()
                     if self.stack[-1][k] != v])
        self.stack.pop()
        for key in ("family", "style", "size"):
            try:
                value = diff[key]
            except KeyError:
                pass
            else:
                self.pdf.set_font(**{key: value})
        # No action required for 'line_height'.
        try:
            value = diff["left_indent"]
        except KeyError:
            pass
        else:
            self.pdf.set_left_margin(self.l_margin + value)
        try:
            value = diff["right_indent"]
        except KeyError:
            pass
        else:
            self.pdf.set_right_margin(self.l_margin + value)

    def write(self, text, link=""):
        self.pdf.write(h=self.size * self.line_height, text=text, link=link)

    def ln(self, factor=1):
        self.pdf.ln(factor * self.size * self.line_height)


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
