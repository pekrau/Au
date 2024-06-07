"EPUB export."

from icecream import ic

import copy
import datetime
import io
import os
import tarfile
import time

import tkinter as tk

from ebooklib import epub

import utils
import constants
from utils import Tr


class Exporter:
    "HTML exporter."

    def __init__(self, main, source, config):
        self.main = main
        self.source = source
        self.config = config

    def write(self):
        # Key: canonical; value: dict(id, fullname, heading, ordinal)
        self.indexed = {}
        self.indexed_count = 0
        # Key: reference id; value: dict(id, fullname, heading, ordinal)
        self.referenced = {}
        self.referenced_count = 0
        # Key: fullname; value: dict(label, ast_children)
        self.footnotes = {}

        book = epub.EpubBook()
        book.set_identifier(self.config["identifier"])
        if self.main.subtitle:
            book.add_metadata("DC", "description", self.main.subtitle)
        book.set_title(self.main.title)
        book.set_language(self.main.language)
        for author in self.main.authors:
            book.add_author(author)

        chapters = []
        for item in self.source.items:
            chapter = epub.EpubHtml(title=item.name,
                                    file_name=f"{item.name}.xhtml",
                                    lang=self.main.language)
            self.outfile = io.StringIO()
            if item.is_section:
                self.write_section(item, level=1)
            else:
                self.write_text(item, level=1)
            chapter.content = self.outfile.getvalue()
            book.add_item(chapter)
            chapters.append(chapter)

        chapter = epub.EpubHtml(title=Tr("References"),
                                     file_name="_References.xhtml",
                                     lang=self.main.language)
        self.outfile = io.StringIO()
        self.write_references()
        chapter.content = self.outfile.getvalue()
        chapters.append(chapter)
        book.add_item(chapter)

        chapter = epub.EpubHtml(title=Tr("Index"),
                                file_name="_Index.xhtml",
                                lang=self.main.language)
        self.outfile = io.StringIO()
        self.write_indexed()
        chapter.content = self.outfile.getvalue()
        chapters.append(chapter)
        book.add_item(chapter)

        book.toc = chapters

        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())

        style = "BODY {color: white;}"
        nav_css = epub.EpubItem(
            uid="style_nav",
            file_name="style/nav.css",
            media_type="text/css",
            content=style,
        )
        book.add_item(nav_css)

        book.spine = ["nav"] + chapters

        filepath = os.path.join(self.config["dirpath"], self.config["filename"])
        epub.write_epub(filepath, book, {})

    def output(self, line):
        self.outfile.write(line)

    def output_newline(self, line):
        self.outfile.write(line + "\n")

    def write_section(self, section, level):
        self.write_heading(section.heading, level)
        for item in section.items:
            if item.is_section:
                self.write_section(item, level=level + 1)
            else:
                self.write_text(item, level=level + 1)

    def write_text(self, text, level):
        self.write_heading(text.heading, level)
        self.current_text = text
        self.render(text.ast)
        self.write_text_footnotes(text)

    def write_text_footnotes(self, text):
        "Footnotes at end of the text."
        try:
            footnotes = self.footnotes[text.fullname]
        except KeyError:
            return
        self.output_newline('<hr width="50%" align="left" style="margin-top: 40pt;"/>')
        self.write_heading(Tr("Footnotes"), 5)
        # This implementation relies on labels being consecutive numbers from 1.
        self.output_newline("<ol>")
        for label, entry in sorted(footnotes.items()):
            self.output_newline(f'<li id="{entry["id"]}">')
            for child in entry["ast_children"]:
                self.render(child)
            self.output_newline("</li>")
        self.output_newline("</ol>")

    def write_heading(self, title, level):
        self.output_newline(f'<h{level}>{title}</h{min(level, constants.MAX_H_LEVEL)}>')

    def write_references(self):
        self.write_heading(Tr("References"), 1)
        lookup = self.main.references_viewer.reference_lookup
        for refid, entries in sorted(self.referenced.items()):
            reference = lookup[refid]
            self.output_newline(f'<p id="{refid}">')
            self.output(f"<strong>{refid}</strong>")
            self.write_reference_authors(reference)
            try:
                method = getattr(self, f"write_reference_{reference['type']}")
            except AttributeError:
                ic("unknown", reference["type"])
            else:
                method(reference)
            self.write_reference_external_links(reference)
            self.write_reference_xrefs(entries)
            self.output_newline("</p>")

    def write_reference_authors(self, reference):
        count = len(reference["authors"])
        for pos, author in enumerate(reference["authors"]):
            if pos > 0:
                if pos == count - 1:
                    self.output(" &amp;")
                else:
                    self.output(",")
            self.output(" " + utils.shortname(author))

    def write_reference_article(self, reference):
        self.output(f" ({reference['year']})")
        try:
            self.output(f" {reference['title'].strip('.')}.")
        except KeyError:
            pass
        try:
            self.output(f" <em>{reference['journal']}</em>")
        except KeyError:
            pass
        try:
            self.output(f' {reference["volume"]}')
        except KeyError:
            pass
        else:
            try:
                self.output(f" ({reference['number']})")
            except KeyError:
                pass
        try:
            self.output(f": pp. {reference['pages'].replace('--', '-')}.")
        except KeyError:
            pass
        self.output_newline("")

    def write_reference_book(self, reference):
        self.output(f" ({reference['year']}).")
        self.output(f" <em>{reference['title'].strip('.')}.</em>")
        try:
            self.output(f" {reference['publisher']}.")
        except KeyError:
            pass
        self.output_newline("")

    def write_reference_link(self, reference):
        self.output(f" ({reference['year']}).")
        try:
            self.output(f" {reference['title'].strip('.')}.")
        except KeyError:
            pass
        try:
            self.output(f' <a href="{reference["url"]}"><{reference["title"]}</a>')
        except KeyError:
            pass
        try:
            self.output(f" Accessed {reference['accessed']}.")
        except KeyError:
            pass
        self.output_newline("")

    def write_reference_external_links(self, reference):
        links = []
        for key, label, template in constants.REFERENCE_LINKS:
            try:
                value = reference[key]
                text = f"{label}:{value}"
                url = template.format(value=value)
                links.append((text, url))
            except KeyError:
                pass
        if not links:
            return
        self.output_newline("<br/>")
        self.output_newline(f'<span style="margin-left: {constants.REFERENCE_INDENT}pt;">')
        for pos, (text, url) in enumerate(links):
            if pos != 0:
                self.output(", ")
            self.output(f'<a href="{url}">{text}</a>')
        self.output_newline("")
        self.output_newline("</span>")

    def write_reference_xrefs(self, entries):
        if not entries:
            return
        self.output_newline("<br/>")
        self.output_newline(f'<span style="margin-left: {constants.REFERENCE_INDENT}pt;">')
        entries = sorted(entries, key=lambda e: e["ordinal"])
        for pos, entry in enumerate(entries):
            if pos != 0:
                self.output(", ")
            url = f'{entry["fullname"]}.xhtml#{entry["id"]}'
            self.output(f'<a href="{url}">{entry["heading"]}</a>')
        self.output_newline("")
        self.output_newline("</span>")

    def write_indexed(self):
        self.write_heading(Tr("Index"), 1)
        items = sorted(self.indexed.items(), key=lambda i: i[0].lower())
        for canonical, entries in items:
            self.output_newline(f'<p id="{canonical}">')
            self.output(f"<strong>{canonical}</strong> ")
            entries.sort(key=lambda e: e["ordinal"])
            for pos, entry in enumerate(entries):
                if pos != 0:
                    self.output(", ")
                url = f'{entry["chapter"]}#{entry["id"]}'
                self.output(f'<a href="{url}">{entry["heading"]}</a>')
            self.output_newline("")
            self.output_newline("</p>")

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
        self.output_newline("<p>")
        for child in ast["children"]:
            self.render(child)
        self.output_newline("</p>")

    def render_raw_text(self, ast):
        self.output(ast["children"])

    def render_blank_line(self, ast):
        pass

    def render_quote(self, ast):
        self.output_newline('<blockquote>')
        for child in ast["children"]:
            self.render(child)
        self.output_newline("</blockquote>")

    def render_code_span(self, ast):
        self.output(f"<code>{ast['children']}</code>")

    def render_code_block(self, ast):
        self.output('<pre><code>')
        for child in ast["children"]:
            self.render(child)
        self.output_newline("</code></pre>")

    def render_fenced_code(self, ast):
        self.output('<pre><code>')
        for child in ast["children"]:
            self.render(child)
        self.output_newline("</code></pre>")

    def render_emphasis(self, ast):
        self.output("<em>")
        for child in ast["children"]:
            self.render(child)
        self.output("</em>")

    def render_strong_emphasis(self, ast):
        self.output("<strong>")
        for child in ast["children"]:
            self.render(child)
        self.output("</strong>")

    def render_thematic_break(self, ast):
        self.output_newline('<hr width="75%"></hr>')

    def render_link(self, ast):
        self.output(f'<a href="{ast["dest"]}">')
        for child in ast["children"]:
            self.render(child)
        self.output("</a>")

    def render_list(self, ast):
        if ast["ordered"]:
            self.output_newline("<ol>")
        else:
            self.output_newline("<ul>")
        for child in ast["children"]:
            self.render(child)
        if ast["ordered"]:
            self.output_newline("</ol>")
        else:
            self.output_newline("</ul>")

    def render_list_item(self, ast):
        self.output_newline("<li>")
        for child in ast["children"]:
            self.render(child)
        self.output_newline("</li>")

    def render_indexed(self, ast):
        entries = self.indexed.setdefault(ast["canonical"], [])
        self.indexed_count += 1
        id = f"_Indexed-{self.indexed_count}"
        entries.append(
            dict(
                id=id,
                chapter=f"{self.current_text.chapter.name}.xhtml",
                heading=self.current_text.heading,
                ordinal=self.current_text.ordinal,
            )
        )
        self.output(
            f'<a id="{id}" href="_Index.xhtml#{ast["canonical"]}">{ast["term"]}</a>'
        )

    def render_footnote_ref(self, ast):
        entries = self.footnotes.setdefault(self.current_text.fullname, {})
        label = int(ast["label"])
        id = f"_footnote-{self.current_text.fullname}-{label}"
        entries[label] = dict(label=label, id=id)
        self.output(f'<sup><strong><a href="#{id}">{ast["label"]}</a></strong></sup>')

    def render_footnote_def(self, ast):
        label = int(ast["label"])
        self.footnotes[self.current_text.fullname][label]["ast_children"] = ast[
            "children"
        ]

    def render_reference(self, ast):
        entries = self.referenced.setdefault(ast["reference"], [])
        self.referenced_count += 1
        id = f"_Referenced-{self.referenced_count}"
        entries.append(
            dict(
                id=id,
                fullname=self.current_text.fullname,
                heading=self.current_text.heading,
                ordinal=self.current_text.ordinal,
            )
        )
        self.output(
            f'<a id="{id}" href="_References.xhtml#{ast["reference"]}">{ast["reference"]}</a>'
        )


class Dialog(tk.simpledialog.Dialog):
    "Dialog to confirm or modify configuration before export."

    def __init__(self, master, source, config):
        self.source = source
        self.config = copy.deepcopy(config)
        self.result = None
        super().__init__(master, title=Tr("EPUB export"))

    def body(self, body):
        row = 0
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_columnconfigure(2, weight=1)

        row += 1
        label = tk.ttk.Label(body, text=Tr("Identifier"))
        label.grid(row=row, column=0, padx=4, sticky=tk.NE)
        self.identifier_entry = tk.ttk.Entry(body, width=40)
        self.identifier_entry.insert(0, self.config.get("identifier") or "book1")
        self.identifier_entry.grid(row=row, column=1, sticky=tk.W)

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
        self.filename_entry.insert(0, self.config.get("filename") or "book.epub")
        self.filename_entry.grid(row=row, column=1, sticky=tk.W)

    def apply(self):
        self.config["identifier"] = self.identifier_entry.get().strip() or "book1"
        self.config["dirpath"] = self.dirpath_entry.get().strip() or os.getcwd()
        filename = self.filename_entry.get().strip() or constants.BOOK
        self.config["filename"] = os.path.splitext(filename)[0] + ".epub"
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
