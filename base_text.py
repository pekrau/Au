"Base text window with rendering methods and bindings."

from icecream import ic

import os.path

import tkinter as tk
from tkinter import ttk

import constants
import utils
from render_mixins import BaseRenderMixin


class TextMixin:
    "Mixin class setting up and configuring attribute 'text'; instance of tk.Text."

    TEXT_COLOR = "white"

    def text_setup(self, parent):
        "Setup the text widget and its associates."
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill=tk.BOTH, expand=True)
        self.frame.rowconfigure(0, weight=1)
        self.frame.columnconfigure(0, weight=1)

        self.text = tk.Text(self.frame,
                            background=self.TEXT_COLOR,
                            padx=constants.TEXT_PADX,
                            font=constants.FONT_NORMAL_FAMILY,
                            wrap=tk.WORD,
                            spacing1=constants.TEXT_SPACING1,
                            spacing2=constants.TEXT_SPACING2,
                            spacing3=constants.TEXT_SPACING3)
        self.text.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))

        self.scroll_y = ttk.Scrollbar(self.frame,
                                      orient=tk.VERTICAL,
                                      command=self.text.yview)
        self.scroll_y.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.text.configure(yscrollcommand=self.scroll_y.set)

    def text_configure_tags(self, text=None):
        "Configure the tags used in the 'tk.Text' instance."
        if text is None:
            text = self.text
        text.tag_configure(constants.TITLE,
                           font=constants.TITLE_FONT,
                           lmargin1=constants.TITLE_LEFT_MARGIN,
                           lmargin2=constants.TITLE_LEFT_MARGIN)
        text.tag_configure(constants.H1,
                           font=constants.H1_FONT,
                           lmargin1=constants.H_LEFT_MARGIN,
                           lmargin2=constants.H_LEFT_MARGIN)
        text.tag_configure(constants.H2,
                           font=constants.H2_FONT,
                           lmargin1=constants.H_LEFT_MARGIN,
                           lmargin2=constants.H_LEFT_MARGIN)
        text.tag_configure(constants.H3,
                           font=constants.H3_FONT,
                           lmargin1=constants.H_LEFT_MARGIN,
                           lmargin2=constants.H_LEFT_MARGIN)
        text.tag_configure(constants.H4,
                           font=constants.H4_FONT,
                           lmargin1=constants.H_LEFT_MARGIN,
                           lmargin2=constants.H_LEFT_MARGIN)
        text.tag_configure(constants.ITALIC, font=constants.FONT_ITALIC)
        text.tag_configure(constants.BOLD, font=constants.FONT_BOLD)
        text.tag_configure(constants.QUOTE,
                           lmargin1=constants.QUOTE_LEFT_INDENT,
                           lmargin2=constants.QUOTE_LEFT_INDENT,
                           rmargin=constants.QUOTE_RIGHT_INDENT,
                           spacing1=constants.QUOTE_SPACING1,
                           spacing2=constants.QUOTE_SPACING2,
                           font=constants.QUOTE_FONT)
        text.tag_configure(constants.THEMATIC_BREAK,
                           font=constants.FONT_BOLD,
                           justify=tk.CENTER)
        text.tag_configure(constants.LINK,
                           foreground=constants.LINK_COLOR,
                           underline=True)
        text.tag_configure(constants.INDEXED, underline=True)
        text.tag_configure(constants.REFERENCE,
                           foreground=constants.REFERENCE_COLOR,
                           underline=True)

    def text_configure_tag_bindings(self, text=None):
        "Configure the tag bindings used in the 'tk.Text' instance."
        if text is None:
            text = self.text
        text.tag_bind(constants.LINK, "<Enter>", self.link_enter)
        text.tag_bind(constants.LINK, "<Leave>", self.link_leave)
        text.tag_bind(constants.LINK, "<Button-1>", self.link_action)
        text.tag_bind(constants.INDEXED, "<Enter>", self.indexed_enter)
        text.tag_bind(constants.INDEXED, "<Leave>", self.indexed_leave)
        text.tag_bind(constants.INDEXED, "<Button-1>", self.indexed_view)
        text.tag_bind(constants.REFERENCE, "<Enter>", self.reference_enter)
        text.tag_bind(constants.REFERENCE, "<Leave>", self.reference_leave)
        text.tag_bind(constants.REFERENCE, "<Button-1>", self.reference_view)

    def text_bind_keys(self, text=None):
        "Configure the key bindings used in the 'tk.Text' instance."
        if text is None:
            text = self.text
        text.bind("<Home>", self.move_cursor_home)
        text.bind("<End>", self.move_cursor_end)
        text.bind("<Key>", self.key_press)
        text.bind("<F1>", self.debug_tags)
        text.bind("<F2>", self.debug_selected)
        text.bind("<F3>", self.debug_buffer_paste)
        text.bind("<F4>", self.debug_dump)


class BaseTextContainer(BaseRenderMixin):
    "Text container base class with Markdown rendering methods and bindings."

    def __init__(self, main, filepath, title=None):
        self.main = main
        self.filepath = filepath
        self.title = title
        self.frontmatter, self.ast = utils.parse(self.absfilepath)
        self.prev_line_not_blank = False
        self.links = dict()     # Lookup local for the instance.

    def __str__(self):
        return self.filepath

    def rerender(self):
        self.links = dict()
        self.frontmatter, self.ast = utils.parse(self.absfilepath)
        self.prev_line_not_blank = False
        self.text.delete("1.0", tk.END)
        self.render_title()
        self.render(self.ast)

    def render_title(self):
        if not self.title:
            return
        self.text.insert(tk.INSERT, self.title, constants.TITLE)
        self.text.insert(tk.INSERT, "\n\n")

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
        return False

    @property
    def character_count(self):
        result = len(self.text.get("1.0", tk.END))
        if self.title:
            result -= len(self.title) + 2
        return result

    def key_press(self, event):
        raise NotImplementedError

    def move_cursor(self, position):
        if position is None:
            self.move_cursor_home()
        else:
            position = self.text.index(position + self.cursor_offset())
            self.text.mark_set(tk.INSERT, position)
            # XXX This does not work?
            self.text.see(position)

    def move_cursor_home(self, event=None):
        self.move_cursor("1.0")

    def move_cursor_end(self, event=None):
        self.move_cursor(tk.END)

    def cursor_offset(self, sign="+"):
        "Return the offset to convert the cursor position to the one to use."
        if self.title:
            return f"{sign}{len(self.title)+2}c"
        else:
            return ""

    def cursor_normalized(self):
        "Return the normalized cursor position."
        return self.text.index(tk.INSERT + self.cursor_offset(sign="-"))

    def get_selection(self, check_no_boundary=True, adjust=False):
        """Raise ValueError if no current selection, or region boundary (if checked).
        Optionally adjust region to have non-blank beginning and end.
        """
        try:
            first = self.text.index(tk.SEL_FIRST)
            last = self.text.index(tk.SEL_LAST)
        except tk.TclError:
            raise ValueError("no current selection")
        if adjust:
            if self.text.get(first) in string.whitespace:
                original_first = first
                for offset in range(1, 10):
                    first = f"{original_first}+{offset}c"
                    if self.text.get(first) not in string.whitespace:
                        break
            if self.text.get(last + "-1c") in string.whitespace:
                original_last = last
                for offset in range(1, 11):
                    last = f"{original_last}-{offset}c"
                    probe = f"{original_last}-{offset+1}c"
                    if self.text.get(probe) not in string.whitespace:
                        break
        if check_no_boundary:
            if self.selection_contains_boundary(first, last):
                raise ValueError
        return first, last

    def selection_contains_boundary(self, first=None, last=None, show=True):
        try:
            if first is None or last is None:
                first, last = self.get_selection()
        except ValueError:
            return False
        first_tags = set(self.text.tag_names(first))
        first_tags.discard("sel")
        last_tags = set(self.text.tag_names(last))
        last_tags.discard("sel")
        result = first_tags != last_tags
        if result and show:
            tk_messagebox.showerror(
                parent=self.toplevel,
                title="Region boundary",
                message="Selection contains a region boundary")
        return result

    def get_link(self, tag=None):
        if tag is None:
            for tag in self.text.tag_names(tk.CURRENT):
                if tag.startswith(constants.LINK_PREFIX):
                    break
            else:
                return None
        return self.links.get(tag)

    def link_create(self, url, title, first, last):
        # Links are not removed from 'links' during a session.
        # The link count must remain strictly increasing.
        tag = f"{constants.LINK_PREFIX}{len(self.links) + 1}"
        self.links[tag] = dict(tag=tag, url=url, title=title)
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

    def render_table(self, ast):
        self.table = Table(self, ast)

    def debug_tags(self, event=None):
        ic("--- tags ---", self.text.tag_names(tk.INSERT))
        ic("--- current ---", self.text.index(tk.CURRENT))

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


class Table(BaseRenderMixin):
    "Table requires its own class for rendering."

    def __init__(self, master, ast):
        self.master = master
        self.frame = ttk.Frame(self.master.text)
        self.master.text.window_create(tk.INSERT, window=self.frame)
        self.prev_line_not_blank = False
        self.text = None
        self.current_row = -1
        self.delimiters = [len(d) for d in ast["delimiters"]]
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
        self.text = tk.Text(self.frame,
                            width=width,
                            height=height,
                            padx=constants.TEXT_PADX,
                            font=constants.FONT_NORMAL_FAMILY,
                            wrap=tk.WORD,
                            spacing1=constants.TEXT_SPACING1,
                            spacing2=constants.TEXT_SPACING2,
                            spacing3=constants.TEXT_SPACING3)
        self.master.text_configure_tags(self.text)
        self.text.grid(row=self.current_row, column=self.current_column,
                       sticky=(tk.W, tk.E, tk.N, tk.S))
        for child in ast["children"]:
            self.render(child)
        if ast.get("header"):
            self.text.tag_add(constants.BOLD, "1.0", tk.INSERT)

    def len_raw_text(self, ast):
        if ast["element"] == "raw_text":
            return len(ast["children"])
        else:
            return sum([self.len_raw_text(c) for c in ast["children"]])

    def render_link(self, ast):
        raise NotImplementedError
