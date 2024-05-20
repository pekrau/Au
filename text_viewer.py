"Viewer window for Markdown text file."

from icecream import ic

import tkinter as tk

import constants
import utils
from render_mixin import RenderMixin
from base_viewer import BaseViewer


class TextViewer(RenderMixin, BaseViewer):
    "Viewer window for Markdown text file."

    TEXT_COLOR = constants.TEXT_COLOR

    def __init__(self, parent, main, text):
        super().__init__(parent, main)
        self.text = text
        self.display()

    def __str__(self):
        "The full name of the text; filepath excluding extension."
        return self.text.fullname

    @property
    def section(self):
        "The section of the text; empty string if at top level."
        return self.text.parentpath

    @property
    def name(self):
        "The short name of the text."
        return self.text.name

    @property
    def absfilepath(self):
        return self.text.abspath

    @property
    def is_modified(self):
        return False

    @property
    def character_count(self):
        return len(self.view.get("1.0", tk.END)) - (len(str(self)) + 2)

    def view_configure_tags(self, view=None):
        "Configure the tags used in the 'tk.Text' instance."
        view = view or self.view
        super().view_configure_tags(view=view)
        view.tag_configure(
            constants.QUOTE,
            lmargin1=constants.QUOTE_LEFT_INDENT,
            lmargin2=constants.QUOTE_LEFT_INDENT,
            rmargin=constants.QUOTE_RIGHT_INDENT,
            spacing1=constants.QUOTE_SPACING1,
            spacing2=constants.QUOTE_SPACING2,
            font=constants.QUOTE_FONT,
        )
        view.tag_configure(
            constants.THEMATIC_BREAK, font=constants.FONT_BOLD, justify=tk.CENTER
        )
        view.tag_configure(constants.INDEXED, underline=True)
        view.tag_configure(
            constants.REFERENCE, foreground=constants.REFERENCE_COLOR, underline=True
        )
        view.tag_configure(
            constants.FOOTNOTE_REF,
            foreground=constants.FOOTNOTE_REF_COLOR,
            underline=True,
        )
        view.tag_configure(
            constants.FOOTNOTE_DEF,
            background=constants.FOOTNOTE_DEF_COLOR,
            borderwidth=1,
            relief=tk.SOLID,
            lmargin1=constants.FOOTNOTE_MARGIN,
            lmargin2=constants.FOOTNOTE_MARGIN,
            rmargin=constants.FOOTNOTE_MARGIN,
        )

    def view_bind_tags(self, view=None):
        "Configure the tag bindings used in the 'tk.Text' instance."
        view = view or self.view
        super().view_bind_tags(view=view)
        view.tag_bind(constants.INDEXED, "<Enter>", self.indexed_enter)
        view.tag_bind(constants.INDEXED, "<Leave>", self.indexed_leave)
        view.tag_bind(constants.INDEXED, "<Button-1>", self.indexed_action)
        view.tag_bind(constants.REFERENCE, "<Enter>", self.reference_enter)
        view.tag_bind(constants.REFERENCE, "<Leave>", self.reference_leave)
        view.tag_bind(constants.REFERENCE, "<Button-1>", self.reference_action)
        view.tag_bind(constants.FOOTNOTE_REF, "<Enter>", self.footnote_enter)
        view.tag_bind(constants.FOOTNOTE_REF, "<Leave>", self.footnote_leave)

    def reference_enter(self, event):
        self.view.configure(cursor="hand2")

    def reference_leave(self, event):
        self.view.configure(cursor="")

    def reference_action(self, event):
        refid = self.get_reference()
        if refid:
            self.main.references_viewer.highlight(refid)

    def get_reference(self):
        for tag in self.view.tag_names(tk.CURRENT):
            if tag.startswith(constants.REFERENCE_PREFIX):
                return tag[len(constants.REFERENCE_PREFIX) :]

    def indexed_enter(self, event):
        self.view.configure(cursor="hand2")

    def indexed_leave(self, event):
        self.view.configure(cursor="")

    def indexed_action(self, event):
        term = self.get_indexed()
        if term:
            self.main.indexed_viewer.highlight(term)

    def get_indexed(self):
        "Get the canonical indexed term at the current position."
        for tag in self.view.tag_names(tk.CURRENT):
            if tag.startswith(constants.INDEXED_PREFIX):
                return tag[len(constants.INDEXED_PREFIX) :]

    def footnote_enter(self, event=None):
        self.view.configure(cursor="hand2")

    def footnote_leave(self, event=None):
        self.view.configure(cursor="")

    def footnote_toggle(self, event=None):
        for tag in self.view.tag_names(tk.CURRENT):
            if tag.startswith(constants.FOOTNOTE_REF_PREFIX):
                label = tag[len(constants.FOOTNOTE_REF_PREFIX) :]
                break
        else:
            return
        self.tag_toggle_elide(constants.FOOTNOTE_DEF_PREFIX + label)

    def display(self):
        self.display_clear()
        self.display_title()
        self.render_initialize()
        self.render(self.text.ast)
        self.render_finalize()

    def render_table(self, ast):
        self.table = Table(self, ast)


class Table(RenderMixin):
    "Read-only table requires its own class for rendering."

    def __init__(self, master, ast):
        self.master = master
        self.frame = tk.ttk.Frame(self.master.view)
        self.master.view.window_create(tk.INSERT, window=self.frame)
        self.view = None
        self.current_row = -1
        self.delimiters = [len(d) for d in ast["delimiters"]]
        self.render_initialize()
        for child in ast["children"]:
            self.render(child)

    def render_table_row(self, ast):
        self.current_row += 1
        self.current_column = -1
        for child in ast["children"]:
            self.render(child)

    def render_table_cell(self, ast):
        self.current_column += 1
        width = max(6, self.delimiters[self.current_column])
        height = max(1, self.len_raw_text(ast) / self.delimiters[self.current_column])
        self.view = tk.Text(
            self.frame,
            width=width,
            height=height,
            padx=constants.TEXT_PADX,
            font=constants.FONT,
            wrap=tk.WORD,
            spacing1=constants.TEXT_SPACING1,
            spacing2=constants.TEXT_SPACING2,
            spacing3=constants.TEXT_SPACING3,
        )
        self.master.view_configure_tags(view=self.view)
        self.view.grid(
            row=self.current_row,
            column=self.current_column,
            sticky=(tk.W, tk.E, tk.N, tk.S),
        )
        for child in ast["children"]:
            self.render(child)
        if ast.get("header"):
            self.view.tag_add(constants.BOLD, "1.0", tk.INSERT)
        self.view.configure(state=tk.DISABLED)

    def len_raw_text(self, ast):
        if ast["element"] == "raw_text":
            return len(ast["children"])
        else:
            return sum([self.len_raw_text(c) for c in ast["children"]])

    def render_link(self, ast):
        raise NotImplementedError
