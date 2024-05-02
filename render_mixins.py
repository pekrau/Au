"Mixin classes containing methods to render Marko AST to tk.Text instance."

from icecream import ic

import tkinter as tk

import constants
import utils


class BaseRenderMixin:
    """Mixin class containing basic methods to render Marko AST to tk.Text instance.
    It assumes:
    - An attribute '.view'; instance of tk.Text.
    - An attribute '.indexed'; a dict containing indexed terms.
    - An attribute '.referenced'; a dict containing references.
    """

    def render(self, ast):
        try:
            method = getattr(self, f"render_{ast['element']}")
        except AttributeError:
            ic("Could not handle ast", ast)
        else:
            method(ast)

    def get_prev_line_not_blank(self):
        try:
            return self._prev_line_not_blank
        except AttributeError:
            self._prev_line_not_blank = False
            return self._prev_line_not_blank

    def set_prev_line_not_blank(self, value):
        self._prev_line_not_blank = value

    prev_line_not_blank = property(get_prev_line_not_blank, set_prev_line_not_blank)

    def render_document(self, ast):
        self.prev_line_not_blank = False
        for child in ast["children"]:
            self.render(child)

    def render_heading(self, ast):
        self.conditional_line_break()
        first = self.view.index(tk.INSERT)
        h = constants.H.get(ast["level"], constants.H4)
        for child in ast["children"]:
            self.render(child)
        self.view.tag_add(h, first, tk.INSERT)
        self.conditional_line_break()

    def render_paragraph(self, ast):
        self.conditional_line_break(flag=False)
        for child in ast["children"]:
            self.render(child)

    def render_emphasis(self, ast):
        first = self.view.index(tk.INSERT)
        for child in ast["children"]:
            self.render(child)
        self.view.tag_add(constants.ITALIC, first, tk.INSERT)

    def render_strong_emphasis(self, ast):
        first = self.view.index(tk.INSERT)
        for child in ast["children"]:
            self.render(child)
        self.view.tag_add(constants.BOLD, first, tk.INSERT)

    def render_raw_text(self, ast):
        children = ast["children"]
        if type(children) == str:
            if children[-1] == "\n":
                children[-1] = " "
            self.view.insert(tk.INSERT, children)
        elif type(children) == list:
            for child in ast["children"]:
                self.render(child)

    def render_line_break(self, ast):
        self.view.insert(tk.INSERT, " ")

    def render_blank_line(self, ast):
        self.view.insert(tk.INSERT, "\n")
        self.prev_line_not_blank = True

    def render_link(self, ast):
        first = self.view.index(tk.INSERT)
        for child in ast["children"]:
            self.render(child)
        self.link_create(ast["dest"], ast["title"], first, self.view.index(tk.INSERT))

    def render_quote(self, ast):
        self.conditional_line_break(flag=False)
        first = self.view.index(tk.INSERT)
        for child in ast["children"]:
            self.render(child)
        self.view.tag_add("quote", first, tk.INSERT)

    def render_literal(self, ast):
        self.view.insert(tk.INSERT, ast["children"])

    def render_thematic_break(self, ast):
        self.conditional_line_break(flag=True)
        self.view.insert(tk.INSERT, "------------------------------------",
                         (constants.THEMATIC_BREAK, ))

    def render_indexed(self, ast):
        self.indexed.setdefault(ast["canonical"], set()).add(self.view.index(tk.INSERT))
        tag = f"{constants.INDEXED_PREFIX}{ast['canonical']}"
        self.view.insert(tk.INSERT, ast["term"], (constants.INDEXED, tag))

    def render_reference(self, ast):
        self.references.setdefault(ast["reference"], set()).add(self.view.index(tk.INSERT))
        self.view.insert(tk.INSERT, f"{ast['reference']}", (constants.REFERENCE, ))

    def conditional_line_break(self, flag=True):
        if self.prev_line_not_blank:
            self.view.insert(tk.INSERT, "\n")
            self.prev_line_not_blank = flag


class FootnoteRenderMixin:
    """Mixin class containing  methods to render footnote Marko AST to tk.Text instance.
    It assumes the presence of an attribute 'view'; instance of tk.Text.
    """

    def render_footnote_ref(self, ast):
        label = ast["label"]
        tag = constants.FOOTNOTE_REF_PREFIX + label
        self.footnotes[label] = dict(label=label, tag=tag)
        self.view.insert(tk.INSERT, f"^{label}", (constants.FOOTNOTE_REF, tag))
        self.view.tag_bind(tag, "<Button-1>", self.footnote_toggle)

    def render_footnote_def(self, ast):
        tag = self.footnotes[ast["label"]]["tag"]
        first = self.view.tag_nextrange(tag, "1.0")[1]
        self.view.mark_set(tk.INSERT, first)
        for child in ast["children"]:
            self.render(child)
        self.view.tag_add(constants.FOOTNOTE_DEF, first + "+1c", tk.INSERT)
        tag = constants.FOOTNOTE_DEF_PREFIX + ast["label"]
        self.view.tag_configure(tag, elide=True)
        self.view.tag_add(tag, first, tk.INSERT)
