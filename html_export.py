"HTML export."

from icecream import ic

import copy
import datetime
import io
import os
import tarfile
import time

import tkinter as tk

import utils
import constants
from utils import Tr

LANGUAGES = ("sv", "en")


class Exporter:
    "HTML exporter."

    def __init__(self, main, source, config):
        self.main = main
        self.source = source
        self.config = config

    def write(self):
        self.indexed = {}  # Key: canonical; value: dict(id, fullname, heading, ordinal)
        self.indexed_count = 0
        self.referenced = {}  # Key: reference id; value: dict(id, fullname, heading, ordinal)
        self.referenced_count = 0
        self.footnotes = {}  # Key: fullname; value: dict(label, ast_children)
        self.outputs = []
        self.footnote_output = None

        if self.config["multiple_files"]: # Separate files for each chapter.
            self.write_page_begin("index", self.main.title)
            self.write_title_page()
            self.write_toc()
            self.write_page_end()

            self.current_text = None
            for item in self.source.items:
                self.write_page_begin(item.name, item.name)
                if item.is_section:
                    self.write_section(item, level=1)
                else:
                    self.write_text(item, level=1)
            self.write_page_end()

            self.write_page_begin("_References", Tr("References"))
            self.write_references()
            self.write_page_end()
            self.write_page_begin("_Index", Tr("Index"))
            self.write_indexed()
            self.write_page_end()

        else:                   # All text in one single HTML file.
            self.write_page_begin("index", self.main.title)
            self.write_title_page()
            self.write_toc()
            self.current_text = None
            for item in self.source.items:
                self.output('<hr class="border border-secondary border-3 m-5">')
                if item.is_section:
                    self.write_section(item, level=1)
                else:
                    self.write_text(item, level=1)
            self.output('<hr class="border border-secondary border-3 m-5">')
            self.write_references()
            self.output('<hr class="border border-secondary border-3 m-5">')
            self.write_indexed()
            self.write_page_end()

        if self.config["tarfile"]:
            filepath = os.path.join(self.config["dirpath"], "book.tgz")
            with tarfile.open(filepath, mode="w:gz") as outfile:
                for basename, output in self.outputs:
                    info = tarfile.TarInfo(basename + ".html")
                    info.mtime = time.time()
                    data = output.getvalue().encode("utf-8")
                    info.size = len(data)
                    outfile.addfile(info, io.BytesIO(data))
        else:
            for basename, output in self.outputs:
                filepath = os.path.join(self.config["dirpath"], basename + ".html")
                with open(filepath, "w") as outfile:
                    outfile.write(output.getvalue())

    def output(self, line, newline=True):
        line = line.rstrip()
        if newline:
            line += "\n"
        return self.outputs[-1][1].write(line)

    def write_page_begin(self, basename, title):
        self.outputs.append((basename, io.StringIO()))
        self.output(
f"""<!doctype html>
<html lang="{self.config.get('language', 'en')}">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH" crossorigin="anonymous">
    <title>{title}</title>
  </head>
  <body>
    <div class="container-md">
""")

    def write_page_end(self):
        self.output(f"""
    </div>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.min.js" integrity="sha384-0pUGZvbkm6XF6gxjEnlmuGrJXVbNuzT9qBBavbLwCsOGabYfZo0T0to5eqruptLy" crossorigin="anonymous"></script>
  </body>
</html>
""")

    def write_title_page(self):
        self.output('<div class="row">')
        self.output('<div class="col-md-9 offset-md-1">')
        self.output(f'<h1 class="mt-5">{self.main.title}</h1>')
        if self.main.subtitle:
            self.output(f'<h2 class="mt-3 mb-5">{self.main.subtitle}</h2>')
        for author in self.main.authors:
            self.output(f'<h3 class="my-3">{author}</h3>')
        status = str(min([t.status for t in self.source.all_texts] + [max(constants.STATUSES)]))
        self.output(f'<p class="mt-5">{Tr("Status")}: {Tr(status)}</p>')
        now = datetime.datetime.now().strftime(constants.TIME_ISO_FORMAT)
        self.output(f'<p class="mb-4">{Tr("Created")}: {now}</p>')
        self.output("</div>")
        self.output("</div>")

    def write_toc(self):
        self.output('<div class="row">')
        self.output('<div class="col-md-5 offset-md-1">')
        self.output('<ul class="list-group">')
        for item in self.source.items:
            self.output('<li class="list-group-item">')
            self.output(f'<a href="{self.get_url(item.fullname)}">{item.heading}</a>')
            self.output("</li>")
        self.output('<li class="list-group-item">')
        self.output(f'<a href="{self.get_url("_References")}">{Tr("References")}</a>')
        self.output("</li>")
        self.output('<li class="list-group-item">')
        self.output(f'<a href="{self.get_url("_Index")}">{Tr("Index")}</a>')
        self.output("</li>")
        self.output("</ul>")
        self.output("</div>")
        self.output("</div>")

    def get_url(self, name, id=None):
        if self.config["multiple_files"]:
            if id:
                return f"{name}.html#{id}"
            else:
                return f"{name}.html"
        else:
            if id:
                return f"#{name}-{id}"
            else:
                return f"#{name}"

    def get_id(self, name, id):
        if self.config["multiple_files"]:
            return id
        else:
            return f"{name}-{id}"

    def write_section(self, section, level):
        self.output(f'<section id="{section.fullname}">')
        self.write_heading(section.heading, level)
        for item in section.items:
            if item.is_section:
                self.write_section(item, level=level + 1)
            else:
                self.write_text(item, level=level + 1)
        self.output('</section>')

    def write_text(self, text, level):
        self.output(f'<article id="{text.fullname}">')
        if self.config["multiple_files"] or text.get("display_heading", True):
            self.write_heading(text.heading, level)
        self.current_text = text
        self.render(text.ast)
        self.write_text_footnotes(text)
        self.output('</article>')

    def write_text_footnotes(self, text):
        "Footnotes at end of the text."
        try:
            footnotes = self.footnotes[text.fullname]
        except KeyError:
            return
        self.output('<hr class="mt-5 mx-5" width="50%">')
        self.write_heading(Tr("Footnotes"), 6)
        # This implementation relies on labels being consecutive numbers from 1.
        self.output('<ol>')
        for label, entry in sorted(footnotes.items()):
            self.output(f'<li id="{entry["id"]}">')
            for child in entry["ast_children"]:
                self.render(child)
            self.output("</li>")
        self.output("</ul>")

    def write_heading(self, title, level):
        level = min(level, constants.MAX_H_LEVEL)
        klass = f"my-{max(1, 6-level)}"
        self.output(f'<h{level} class="{klass}">{title}</h{level}>')

    def write_references(self):
        self.output(f'<section id="_References">')
        self.write_heading(Tr("References"), 1)
        lookup = self.main.references_viewer.reference_lookup
        for refid, entries in sorted(self.referenced.items()):
            reference = lookup[refid]
            self.output(f'<p id="{self.get_id("_References", refid)}">')
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
            self.output("</p>")
        self.output(f'</section>')

    def write_reference_authors(self, reference):
        count = len(reference["authors"])
        for pos, author in enumerate(reference["authors"]):
            if pos > 0:
                if pos == count - 1:
                    self.output("&amp;")
                else:
                    self.output(",")
            self.output(utils.shortname(author))

    def write_reference_article(self, reference):
        self.output(f"({reference['year']}) ")
        try:
            self.output(reference["title"].strip(".") + ". ")
        except KeyError:
            pass
        try:
            self.output(f"<em>{reference['journal']}</em>")
        except KeyError:
            pass
        try:
            self.output(reference["volume"])
        except KeyError:
            pass
        else:
            try:
                self.output(f"({reference['number']})")
            except KeyError:
                pass
        try:
            self.output(f": pp. {reference['pages'].replace('--', '-')}.")
        except KeyError:
            pass

    def write_reference_book(self, reference):
        self.output(f"({reference['year']}).")
        self.output(f"<em>{reference['title'].strip('.') + '. '}</em>")
        try:
            self.output(f"{reference['publisher']}.")
        except KeyError:
            pass

    def write_reference_link(self, reference):
        self.output(f"({reference['year']}).")
        try:
            self.output(reference["title"].strip(".") + ". ")
        except KeyError:
            pass
        try:
            self.output(f'<a href="{reference["url"]}"><{reference["title"]}</a>')
        except KeyError:
            pass
        try:
            self.output(f"Accessed {reference['accessed']}.")
        except KeyError:
            pass

    def write_reference_external_links(self, reference):
        any_item = False
        for key, label, template in constants.REFERENCE_LINKS:
            try:
                value = reference[key]
                if any_item:
                    self.output(",")
                url = template.format(value=value)
                self.output(f'<a target="_blank" href="{url}">{label}:{value}</a>')
                any_item = True
            except KeyError:
                pass

    def write_reference_xrefs(self, entries):
        self.output("<br>")
        entries.sort(key=lambda e: e["ordinal"])
        for entry in entries:
            if self.config["multiple_files"]:
                url = f'{entry["fullname"]}.html#{entry["id"]}'
            else:
                url = f'#{entry["id"]}'
            if entry is entries[0]:
                self.output(f'<a class="ms-4" href="{url}">{entry["heading"]}</a>')
            else:
                self.output(f'<a href="{url}">{entry["heading"]}</a>')
            if entry is not entries[-1]:
                self.output(",")

    def write_indexed(self):
        self.output(f'<section id="_Index">')
        self.write_heading(Tr("Index"), 1)
        items = sorted(self.indexed.items(), key=lambda i: i[0].lower())
        for canonical, entries in items:
            self.output(f'<p id="{self.get_id("_Index", canonical)}">')
            self.output(f"<strong>{canonical}</strong>")
            entries.sort(key=lambda e: e["ordinal"])
            for entry in entries:
                if self.config["multiple_files"]:
                    url = f'{entry["fullname"]}.html#{entry["id"]}'
                else:
                    url = f'#{entry["id"]}'
                self.output(f'<a href="{url}">{entry["heading"]}</a>')
                if entry is not entries[-1]:
                    self.output(",")
            self.output("</p>")
        self.output(f'</section>')

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
        self.output('<blockquote class="blockquote mx-5">')
        for child in ast["children"]:
            self.render(child)
        self.output('</blockquote>')

    def render_code_span(self, ast):
        self.output(f"<code>{ast['children']}</code>")
        
    def render_code_block(self, ast):
        self.output('<pre class="ms-5"><code>', newline=False)
        for child in ast["children"]:
            self.render(child)
        self.output("</code></pre>")

    def render_fenced_code(self, ast):
        self.output('<pre class="ms-5"><code>', newline=False)
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
        self.output("<hr>")

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
        entries = self.indexed.setdefault(ast["canonical"], [])
        self.indexed_count += 1
        id = f"_Indexed-{self.indexed_count}"
        entries.append(dict(id=id,
                            fullname=self.current_text.fullname,
                            heading=self.current_text.heading,
                            ordinal=self.current_text.ordinal,
                            ))
        self.output(f'<a id="{id}" href="{self.get_url("_Index", id=ast["canonical"])}">{ast["term"]}</a>')

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
        entries.append(dict(id=id,
                            fullname=self.current_text.fullname,
                            heading=self.current_text.heading,
                            ordinal=self.current_text.ordinal))
        self.output(f'<a id="{id}" href="{self.get_url("_References", id=ast["reference"])}">{ast["reference"]}</a>')


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
        label = tk.ttk.Label(body, text=Tr("Language"), padding=4)
        label.grid(row=row, column=0, sticky=tk.NE)
        self.language_var = tk.StringVar(value=self.config.get("language") or "")
        combobox = tk.ttk.Combobox(
            body,
            values=LANGUAGES,
            textvariable=self.language_var,
        )
        combobox.grid(row=row, column=1, sticky=tk.W)

        row += 1
        label = tk.ttk.Label(body, text=Tr("File or files"), padding=4)
        label.grid(row=row, column=0, sticky=tk.NE)
        self.multiple_files_var = tk.IntVar(value=self.config.get("multiple_files", False))
        frame = tk.ttk.Frame(body)
        frame.grid(row=row, column=1, sticky=tk.EW)
        button = tk.ttk.Radiobutton(frame,
                                    text=f"{Tr('All text in a single HTML file')} 'index.html'.",
                                    value=False,
                                    variable=self.multiple_files_var,
                                    padding=4)
        button.pack(anchor=tk.W)
        button = tk.ttk.Radiobutton(frame,
                                    text=f"{Tr('Separate files for each chapter')}.",
                                    value=True,
                                    variable=self.multiple_files_var,
                                    padding=4)
        button.pack(anchor=tk.W)

        row += 1
        label = tk.ttk.Label(body, text=Tr("Tar file"), padding=4)
        label.grid(row=row, column=0, sticky=tk.NE)
        self.tarfile_var = tk.IntVar(value=self.config.get("tarfile", False))
        button = tk.ttk.Checkbutton(body,
                                    text=f"{Tr('Store in gzipped tar file')} 'book.tgz'.",
                                    offvalue=False,
                                    onvalue=True,
                                    variable=self.tarfile_var,
                                    padding=4)
        button.grid(row=row, column=1, sticky=tk.W)

    def apply(self):
        self.config["dirpath"] = self.dirpath_entry.get().strip() or os.getcwd()
        self.config["language"] = self.language_var.get().strip()
        self.config["multiple_files"] = bool(self.multiple_files_var.get())
        self.config["tarfile"] = bool(self.tarfile_var.get())
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
