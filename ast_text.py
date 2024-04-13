"AST parser mixin; Text widget actions."

from icecream import ic

import tkinter as tk

import constants


class Ast2TextMixin:
    "Requires an attribute Text widget 'text'."

    def parse(self, ast):
        try:
            method = getattr(self, f"parse_{ast['element']}")
        except AttributeError:
            ic("Could not handle ast", ast)
        else:
            method(ast)

    def parse_document(self, ast):
        self._prev_blank_line = False
        for child in ast["children"]:
            self.parse(child)

    def parse_paragraph(self, ast):
        if self._prev_blank_line:
            self.text.insert(tk.END, "\n")
            self._prev_blank_line = False
        for child in ast["children"]:
            self.parse(child)

    def parse_emphasis(self, ast):
        start = self.text.index(tk.INSERT)
        for child in ast["children"]:
            self.parse(child)
        self.text.tag_add(constants.ITALIC, start, self.text.index(tk.INSERT))

    def parse_strong_emphasis(self, ast):
        start = self.text.index(tk.INSERT)
        for child in ast["children"]:
            self.parse(child)
        self.text.tag_add(constants.BOLD, start, self.text.index(tk.INSERT))

    def parse_raw_text(self, ast):
        children = ast["children"]
        if type(children) == str:
            if children[-1] == "\n":
                children[-1] = " "
            self.text.insert(tk.END, children)
        elif type(children) == list:
            for child in ast["children"]:
                self.parse(child)

    def parse_line_break(self, ast):
        self.text.insert(tk.END, " ")

    def parse_blank_line(self, ast):
        self.text.insert(tk.END, "\n")
        self._prev_blank_line = True

    def parse_link(self, ast):
        start = self.text.index(tk.INSERT)
        for child in ast["children"]:
            self.parse(child)
        try:
            links = self.links
        except AttributeError:
            pass
        else:
            links.add(ast, start, tk.INSERT)

    def parse_quote(self, ast):
        start = self.text.index(tk.INSERT)
        for child in ast["children"]:
            self.parse(child)
        self.text.tag_add("quote", start, self.text.index(tk.INSERT))

    def parse_footnote_ref(self, ast):
        start = self.text.index(tk.INSERT)
        self.text.insert(tk.END, "[note]")
        try:
            footnotes = self.footnotes
        except AttributeError:
            pass
        else:
            footnotes.add(ast, start, self.text.index(tk.INSERT))

    def parse_footnote_def(self, ast):
        try:
            footnotes = self.footnotes
        except AttributeError:
            pass
        else:
            footnotes.set(ast)
