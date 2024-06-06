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
        book.set_title(self.main.title)
        book.set_language(self.main.language)
        for author in self.main.authors:
            book.add_author(author)

        chapters = []
        for number, item in enumerate(self.source.items, start=1):
            title = item.name
            file_name = f"chapter_{number}.xhtml"
            self.chapter = epub.EpubHtml(title=title,
                                                  file_name=file_name,
                                                  lang=self.main.language)
            chapters.append({"number": number,
                             "title": title,
                             "file_name": file_name,
                             "chapter": self.chapter})
            self.outfile = io.StringIO()
            if item.is_section:
                self.write_section(item, level=1)
            else:
                self.write_text(item, level=1)
            self.chapter.content = self.outfile.getvalue()
            book.add_item(self.chapter)

        # number += 1
        # title = Tr("References")
        # file_name = "_References.xhtml"
        # self.chapter = epub.EpubHtml(title=title,
        #                                       file_name=file_name,
        #                                       lang=self.main.language)
        # chapters.append({"number": number,
        #                  "title": title,
        #                  "file_name": file_name,
        #                  "chapter": self.chapter})
        # self.outfile = io.StringIO()
        # self.write_references()
        # self.chapter.content = self.outfile.getvalue()
        # book.add_item(self.chapter)

        # number += 1
        # title = Tr("Index")
        # file_name = "_Index.xhtml"
        # self.chapter = epub.EpubHtml(title=title,
        #                                       file_name=file_name,
        #                                       lang=self.main.language)
        # chapters.append({"number": number,
        #                  "title": title,
        #                  "file_name": file_name,
        #                  "chapter": self.chapter})
        # self.outfile = io.StringIO()
        # self.write_indexed()
        # self.chapter.content = self.outfile.getvalue()
        # book.add_item(self.chapter)

        book.toc =(
            epub.Link("chapter1.xhtml", "Introduction", "intro"),
            (epub.Section("Book"), (chapters[0]["chapter"],))
        )

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

        book.spine = ["nav", chapters[0]["chapter"]]

        filepath = os.path.join(self.config["dirpath"], self.config["filename"])
        epub.write_epub(filepath, book, {})

    def output(self, line, newline=True):
        line = line.rstrip()
        if newline:
            line += "\n"
        self.outfile.write(line)

    def get_url(self, name, id=None):
        if id:
            return f"{name}.html#{id}"
        else:
            return f"{name}.html"

    def get_id(self, name, id):
        return id

    def write_section(self, section, level):
        self.write_heading(section.heading, level)
        # self.output(f'<section id="{section.fullname}">')
        # for item in section.items:
        #     if item.is_section:
        #         self.write_section(item, level=level + 1)
        #     else:
        #         self.write_text(item, level=level + 1)
        # self.output("</section>")

    def write_text(self, text, level):
        self.write_heading(text.heading, level)
        # self.output(f'<article id="{text.fullname}">')
        # self.current_text = text
        # self.render(text.ast)
        # self.write_text_footnotes(text)
        # self.output("</article>")

    def write_text_footnotes(self, text):
        "Footnotes at end of the text."
        pass
        # try:
        #     footnotes = self.footnotes[text.fullname]
        # except KeyError:
        #     return
        # self.output('<hr class="mt-5 mx-5" width="50%">')
        # self.write_heading(Tr("Footnotes"), 6)
        # # This implementation relies on labels being consecutive numbers from 1.
        # self.output("<ol>")
        # for label, entry in sorted(footnotes.items()):
        #     self.output(f'<li id="{entry["id"]}">')
        #     for child in entry["ast_children"]:
        #         self.render(child)
        #     self.output("</li>")
        # self.output("</ul>")

    def write_heading(self, title, level):
        level = min(level, constants.MAX_H_LEVEL)
        self.output(f'<h{level}>{title}</h{level}>')

    def write_references(self):
        pass
        # self.output(f'<section id="_References">')
        # self.write_heading(Tr("References"), 1)
        # lookup = self.main.references_viewer.reference_lookup
        # for refid, entries in sorted(self.referenced.items()):
        #     reference = lookup[refid]
        #     self.output(f'<p id="{self.get_id("_References", refid)}">')
        #     self.output(f"<strong>{refid}</strong>")
        #     self.write_reference_authors(reference)
        #     try:
        #         method = getattr(self, f"write_reference_{reference['type']}")
        #     except AttributeError:
        #         ic("unknown", reference["type"])
        #     else:
        #         method(reference)
        #     self.write_reference_external_links(reference)
        #     self.write_reference_xrefs(entries)
        #     self.output("</p>")
        # self.output(f"</section>")

    def write_reference_authors(self, reference):
        pass
        # count = len(reference["authors"])
        # for pos, author in enumerate(reference["authors"]):
        #     if pos > 0:
        #         if pos == count - 1:
        #             self.output("&amp;")
        #         else:
        #             self.output(",")
        #     self.output(utils.shortname(author))

    def write_reference_article(self, reference):
        pass
        # self.output(f"({reference['year']}) ")
        # try:
        #     self.output(reference["title"].strip(".") + ". ")
        # except KeyError:
        #     pass
        # try:
        #     self.output(f"<em>{reference['journal']}</em>")
        # except KeyError:
        #     pass
        # try:
        #     self.output(reference["volume"])
        # except KeyError:
        #     pass
        # else:
        #     try:
        #         self.output(f"({reference['number']})")
        #     except KeyError:
        #         pass
        # try:
        #     self.output(f": pp. {reference['pages'].replace('--', '-')}.")
        # except KeyError:
        #     pass

    def write_reference_book(self, reference):
        pass
        # self.output(f"({reference['year']}).")
        # self.output(f"<em>{reference['title'].strip('.') + '. '}</em>")
        # try:
        #     self.output(f"{reference['publisher']}.")
        # except KeyError:
        #     pass

    def write_reference_link(self, reference):
        pass
        # self.output(f"({reference['year']}).")
        # try:
        #     self.output(reference["title"].strip(".") + ". ")
        # except KeyError:
        #     pass
        # try:
        #     self.output(f'<a href="{reference["url"]}"><{reference["title"]}</a>')
        # except KeyError:
        #     pass
        # try:
        #     self.output(f"Accessed {reference['accessed']}.")
        # except KeyError:
        #     pass

    def write_reference_external_links(self, reference):
        pass
        # links = []
        # for key, label, template in constants.REFERENCE_LINKS:
        #     try:
        #         value = reference[key]
        #         text = f"{label}:{value}"
        #         url = template.format(value=value)
        #         links.append((text, url))
        #     except KeyError:
        #         pass
        # if not links:
        #     return
        # self.output("<br>")
        # after_first = False
        # for pos, (text, url) in enumerate(links):
        #     if after_first:
        #         self.output(",")
        #     else:
        #         after_first = True
        #     if pos == 0:
        #         self.output(f'<a class="ms-4" target="_blank" href="{url}">{text}</a>')
        #     else:
        #         self.output(f'<a target="_blank" href="{url}">{text}</a>')

    def write_reference_xrefs(self, entries):
        pass
        # if not entries:
        #     return
        # self.output("<br>")
        # for pos, entry in enumerate(sorted(entries, key=lambda e: e["ordinal"])):
        #     url = f'{entry["fullname"]}.html#{entry["id"]}'
        #     if pos == 0:
        #         self.output(f'<a class="ms-4" href="{url}">{entry["heading"]}</a>')
        #     else:
        #         self.output(f'<a href="{url}">{entry["heading"]}</a>')
        #     if entry is not entries[-1]:
        #         self.output(",")

    def write_indexed(self):
        pass
        # self.output(f'<section id="_Index">')
        # self.write_heading(Tr("Index"), 1)
        # items = sorted(self.indexed.items(), key=lambda i: i[0].lower())
        # for canonical, entries in items:
        #     self.output(f'<p id="{self.get_id("_Index", canonical)}">')
        #     self.output(f"<strong>{canonical}</strong>")
        #     entries.sort(key=lambda e: e["ordinal"])
        #     for entry in entries:
        #         url = f'{entry["fullname"]}.html#{entry["id"]}'
        #         self.output(f'<a href="{url}">{entry["heading"]}</a>')
        #         if entry is not entries[-1]:
        #             self.output(",")
        #     self.output("</p>")
        # self.output(f"</section>")

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
        self.output("<p>")
        for child in ast["children"]:
            self.render(child)
        self.output("</p>")

    def render_raw_text(self, ast):
        self.output(ast["children"])

    def render_blank_line(self, ast):
        pass

    def render_quote(self, ast):
        self.output('<blockquote>')
        for child in ast["children"]:
            self.render(child)
        self.output("</blockquote>")

    def render_code_span(self, ast):
        self.output(f"<code>{ast['children']}</code>")

    def render_code_block(self, ast):
        self.output('<pre><code>', newline=False)
        for child in ast["children"]:
            self.render(child)
        self.output("</code></pre>")

    def render_fenced_code(self, ast):
        self.output('<pre><code>', newline=False)
        for child in ast["children"]:
            self.render(child)
        self.output("</code></pre>")

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
        self.output("<hr></hr>")

    def render_link(self, ast):
        self.output(f'<a href="{ast["dest"]}">')
        for child in ast["children"]:
            self.render(child)
        self.output("</a>")

    def render_list(self, ast):
        if ast["ordered"]:
            self.output("<ol>")
        else:
            self.output("<ul>")
        for child in ast["children"]:
            self.render(child)
        if ast["ordered"]:
            self.output("</ol>")
        else:
            self.output("</ul>")

    def render_list_item(self, ast):
        self.output("<li>")
        for child in ast["children"]:
            self.render(child)
        self.output("</li>")

    def render_indexed(self, ast):
        self.output(ast["term"])
        # entries = self.indexed.setdefault(ast["canonical"], [])
        # self.indexed_count += 1
        # id = f"_Indexed-{self.indexed_count}"
        # entries.append(
        #     dict(
        #         id=id,
        #         fullname=self.current_text.fullname,
        #         heading=self.current_text.heading,
        #         ordinal=self.current_text.ordinal,
        #     )
        # )
        # self.output(
        #     f'<a id="{id}" href="{self.get_url("_Index", id=ast["canonical"])}">{ast["term"]}</a>'
        # )

    def render_footnote_ref(self, ast):
        self.output(ast["label"])
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
        self.output(ast["reference"])
        # entries = self.referenced.setdefault(ast["reference"], [])
        # self.referenced_count += 1
        # id = f"_Referenced-{self.referenced_count}"
        # entries.append(
        #     dict(
        #         id=id,
        #         fullname=self.current_text.fullname,
        #         heading=self.current_text.heading,
        #         ordinal=self.current_text.ordinal,
        #     )
        # )
        # self.output(
        #     f'<a id="{id}" href="{self.get_url("_References", id=ast["reference"])}">{ast["reference"]}</a>'
        # )


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
