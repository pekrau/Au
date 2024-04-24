"Base text window with rendering methods and bindings."

from icecream import ic

import os.path

import tkinter as tk
from tkinter import ttk

import constants
import utils


class BaseText:
    "Text window base class with rendering methods and bindings."

    def __init__(self, main, filepath):
        self.main = main
        self.filepath = filepath

        parsed = utils.parse(self.absfilepath)
        self.frontmatter = parsed.frontmatter
        self.ast = parsed.ast

        # The footnotes lookup is local for each BaseText instance.
        self.footnotes = dict()

    def setup_text(self, parent):
        "Setup the text widget and its associates."
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill=tk.BOTH, expand=True)
        self.frame.rowconfigure(0, weight=1)
        self.frame.columnconfigure(0, weight=1)

        self.text = tk.Text(self.frame,
                            font=constants.FONT_FAMILY_NORMAL,
                            wrap=tk.WORD,
                            spacing1=4,
                            spacing2=8)
        self.text.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))

        self.text.tag_configure(constants.ITALIC, font=constants.FONT_ITALIC)
        self.text.tag_configure(constants.BOLD, font=constants.FONT_BOLD)
        self.text.tag_configure(constants.QUOTE,
                                lmargin1=constants.QUOTE_LEFT_INDENT,
                                lmargin2=constants.QUOTE_LEFT_INDENT,
                                rmargin=constants.QUOTE_RIGHT_INDENT,
                                spacing1=0,
                                spacing2=0,
                                font=constants.FONT_FAMILY_QUOTE)

        self.text.tag_configure(constants.LINK,
                                foreground=constants.LINK_COLOR,
                                underline=True)
        self.text.tag_bind(constants.LINK, "<Enter>", self.link_enter)
        self.text.tag_bind(constants.LINK, "<Leave>", self.link_leave)
        self.text.tag_bind(constants.LINK, "<Button-1>", self.link_action)

        self.text.tag_configure(constants.INDEXED, underline=True)
        self.text.tag_bind(constants.INDEXED, "<Enter>", self.indexed_enter)
        self.text.tag_bind(constants.INDEXED, "<Leave>", self.indexed_leave)
        self.text.tag_bind(constants.INDEXED, "<Button-1>", self.indexed_view)

        self.text.tag_configure(constants.REFERENCE,
                                foreground=constants.REFERENCE_COLOR,
                                underline=True)
        self.text.tag_bind(constants.REFERENCE, "<Enter>", self.reference_enter)
        self.text.tag_bind(constants.REFERENCE, "<Leave>", self.reference_leave)
        self.text.tag_bind(constants.REFERENCE, "<Button-1>", self.reference_view)

        self.text.tag_configure(constants.FOOTNOTE_REF,
                                foreground=constants.FOOTNOTE_REF_COLOR,
                                underline=True)
        self.text.tag_bind(constants.FOOTNOTE_REF, "<Enter>", self.footnote_enter)
        self.text.tag_bind(constants.FOOTNOTE_REF, "<Leave>", self.footnote_leave)
        self.text.tag_configure(constants.FOOTNOTE_DEF,
                                background=constants.FOOTNOTE_DEF_COLOR,
                                borderwidth=1,
                                relief=tk.SOLID,
                                lmargin1=4,
                                lmargin2=4,
                                rmargin=4)

        self.text_scroll_y = ttk.Scrollbar(self.frame,
                                           orient=tk.VERTICAL,
                                           command=self.text.yview)
        self.text_scroll_y.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.text.configure(yscrollcommand=self.text_scroll_y.set)

        self.text.bind("<Home>", self.move_cursor_home)
        self.text.bind("<End>", self.move_cursor_end)
        self.text.bind("<Key>", self.key_press)
        self.text.bind("<F1>", self.debug_tags)
        self.text.bind("<F2>", self.debug_selected)
        self.text.bind("<F3>", self.debug_buffer_paste)
        self.text.bind("<F4>", self.debug_dump)

    @property
    def absfilepath(self):
        return os.path.join(self.main.absdirpath, self.filepath)

    @property
    def timestamp(self):
        return utils.get_timestamp(self.absfilepath)

    @property
    def age(self):
        return utils.get_age(self.absfilepath)

    @property
    def is_modified(self):
        return self.text.edit_modified()

    @property
    def character_count(self):
        return len(self.text.get("1.0", tk.END))

    def key_press(self, event):
        raise NotImplementedError

    def move_cursor(self, position=None):
        if position is None:
            self.move_cursor_home()
        else:
            self.text.mark_set(tk.INSERT, position)
            self.text.see(position)

    def move_cursor_home(self, event=None):
        self.move_cursor("1.0")

    def move_cursor_end(self, event=None):
        self.move_cursor(tk.END)

    def get_link(self, tag=None):
        if tag is None:
            for tag in self.text.tag_names(tk.CURRENT):
                if tag.startswith(constants.LINK_PREFIX):
                    break
            else:
                return None
        return self.main.links.get(tag)

    def link_create(self, url, title, first, last):
        tag = self.main.link_create(url, title)
        self.text.tag_add(constants.LINK, first, last)
        self.text.tag_add(tag, first, last)

    def link_enter(self, event):
        link = self.get_link()
        if not link:
            return
        self.text.configure(cursor="hand2")

    def link_action(self, event):
        raise NotImplementedError

    def reference_enter(self, event):
        self.text.configure(cursor="hand2")

    def reference_leave(self, event):
        self.text.configure(cursor="")

    def reference_view(self, event):
        raise NotImplementedError

    def indexed_enter(self, event):
        self.text.configure(cursor="hand2")

    def indexed_leave(self, event):
        self.text.configure(cursor="")

    def indexed_view(self, event):
        raise NotImplementedError

    def link_leave(self, event):
        self.text.configure(cursor="")

    def footnote_enter(self, event=None):
        self.text.configure(cursor="hand2")

    def footnote_leave(self, event=None):
        self.text.configure(cursor="")

    def footnote_toggle(self, event=None):
        for tag in self.text.tag_names(tk.CURRENT):
            if tag.startswith(constants.FOOTNOTE_REF_PREFIX):
                label = tag[len(constants.FOOTNOTE_REF_PREFIX):]
                break
        else:
            return
        tag = constants.FOOTNOTE_DEF_PREFIX + label
        elided = bool(int(self.text.tag_cget(tag, "elide")))
        self.text.tag_configure(tag, elide=not elided)

    def render(self, ast):
        try:
            method = getattr(self, f"render_{ast['element']}")
        except AttributeError:
            ic("Could not handle ast", ast)
        else:
            method(ast)

    def render_document(self, ast):
        self.prev_blank_line = False
        for child in ast["children"]:
            self.render(child)

    def render_paragraph(self, ast):
        if self.prev_blank_line:
            self.text.insert(tk.INSERT, "\n")
            self.prev_blank_line = False
        for child in ast["children"]:
            self.render(child)

    def render_emphasis(self, ast):
        first = self.text.index(tk.INSERT)
        for child in ast["children"]:
            self.render(child)
        self.text.tag_add(constants.ITALIC, first, tk.INSERT)

    def render_strong_emphasis(self, ast):
        first = self.text.index(tk.INSERT)
        for child in ast["children"]:
            self.render(child)
        self.text.tag_add(constants.BOLD, first, tk.INSERT)

    def render_raw_text(self, ast):
        children = ast["children"]
        if type(children) == str:
            if children[-1] == "\n":
                children[-1] = " "
            self.text.insert(tk.INSERT, children)
        elif type(children) == list:
            for child in ast["children"]:
                self.render(child)

    def render_line_break(self, ast):
        self.text.insert(tk.INSERT, " ")

    def render_blank_line(self, ast):
        self.text.insert(tk.INSERT, "\n")
        self.prev_blank_line = True

    def render_link(self, ast):
        first = self.text.index(tk.INSERT)
        for child in ast["children"]:
            self.render(child)
        self.link_create(ast["dest"], ast["title"], first, tk.INSERT)

    def render_quote(self, ast):
        if self.prev_blank_line:
            self.text.insert(tk.INSERT, "\n")
        self.prev_blank_line = False
        first = self.text.index(tk.INSERT)
        for child in ast["children"]:
            self.render(child)
        self.text.tag_add("quote", first, tk.INSERT)

    def render_footnote_ref(self, ast):
        label = ast["label"]
        tag = constants.FOOTNOTE_REF_PREFIX + label
        self.footnotes[label] = dict(label=label, tag=tag)
        self.text.insert(tk.INSERT, f"^{label}", (constants.FOOTNOTE_REF, tag))
        self.text.tag_bind(tag, "<Button-1>", self.footnote_toggle)

    def render_footnote_def(self, ast):
        tag = self.footnotes[ast["label"]]["tag"]
        first = self.text.tag_nextrange(tag, "1.0")[1]
        self.text.mark_set(tk.INSERT, first)
        for child in ast["children"]:
            self.render(child)
        self.text.tag_add(constants.FOOTNOTE_DEF, first + "+1c", tk.INSERT)
        tag = constants.FOOTNOTE_DEF_PREFIX + ast["label"]
        self.text.tag_configure(tag, elide=True)
        self.text.tag_add(tag, first, tk.INSERT)

    def render_indexed(self, ast):
        self.text.insert(tk.INSERT, ast["target"], constants.INDEXED)

    def render_reference(self, ast):
        self.text.insert(tk.INSERT, f"{ast['target']}", constants.REFERENCE)

    def debug_tags(self, event=None):
        ic("--- tags ---", self.text.tag_names(tk.INSERT))

    def debug_selected(self, event=None):
        try:
            first, last = self.get_selection(check_no_boundary=False)
        except ValueError:
            return
        ic("--- selected ---",
           self.text.tag_names(first),
           self.text.tag_names(last),
           self.text.dump(first, last))

    def debug_buffer_paste(self, event=None):
        ic("--- paste buffer ---",  self.main.paste_buffer)

    def debug_dump(self, event=None):
        dump = self.text.dump("1.0", tk.END)
        ic("--- dump ---", dump)
