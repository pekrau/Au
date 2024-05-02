"Base viewer classes with rendering methods and bindings."

from icecream import ic

import os.path
import webbrowser

import tkinter as tk
from tkinter import ttk

import constants
import utils
from render_mixins import BaseRenderMixin


class BaseViewer:
    "Base class with methods for viewer using a 'tk.Text' instance."

    TEXT_COLOR = "white"

    def __init__(self, parent, main):
        self.main = main
        self.links = dict()       # Lookup local for the instance.
        self.view_create(parent)
        self.view_configure_tags()
        self.view_configure_tag_bindings()
        self.view_bind_keys()

    def view_create(self, parent):
        "Create the view tk.Text widget and its associates."
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill=tk.BOTH, expand=True)
        self.frame.rowconfigure(0, weight=1)
        self.frame.columnconfigure(0, weight=1)

        self.view = tk.Text(self.frame,
                            background=self.TEXT_COLOR,
                            padx=constants.TEXT_PADX,
                            font=constants.FONT_NORMAL_FAMILY,
                            wrap=tk.WORD,
                            spacing1=constants.TEXT_SPACING1,
                            spacing2=constants.TEXT_SPACING2,
                            spacing3=constants.TEXT_SPACING3)
        self.view.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))

        self.scroll_y = ttk.Scrollbar(self.frame,
                                      orient=tk.VERTICAL,
                                      command=self.view.yview)
        self.scroll_y.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.view.configure(yscrollcommand=self.scroll_y.set)

    def render_title(self):
        self.view.insert(tk.INSERT, str(self), constants.TITLE)
        self.view.insert(tk.INSERT, "\n\n")

    def view_configure_tags(self, view=None):
        "Configure the tags used in the 'tk.Text' instance."
        if view is None:
            view = self.view
        view.tag_configure(constants.TITLE,
                           font=constants.TITLE_FONT,
                           lmargin1=constants.TITLE_LEFT_MARGIN,
                           lmargin2=constants.TITLE_LEFT_MARGIN)
        view.tag_configure(constants.ITALIC, font=constants.FONT_ITALIC)
        view.tag_configure(constants.BOLD, font=constants.FONT_BOLD)
        view.tag_configure(constants.LINK,
                           foreground=constants.LINK_COLOR,
                           underline=True)
        view.tag_configure(constants.HIGHLIGHT,
                           background=constants.HIGHLIGHT_COLOR)

    def view_configure_tag_bindings(self, view=None):
        "Configure the tag bindings used in the 'tk.Text' instance."
        if view is None:
            view = self.view
        view.tag_bind(constants.LINK, "<Enter>", self.link_enter)
        view.tag_bind(constants.LINK, "<Leave>", self.link_leave)
        view.tag_bind(constants.LINK, "<Button-1>", self.link_action)

    def view_bind_keys(self, view=None):
        "Configure the key bindings used in the 'tk.Text' instance."
        if view is None:
            view = self.view
        view.bind("<Home>", self.move_cursor_home)
        view.bind("<End>", self.move_cursor_end)
        view.bind("<Key>", self.key_press)
        view.bind("<F1>", self.debug_tags)
        view.bind("<F2>", self.debug_selected)
        view.bind("<F3>", self.debug_buffer_paste)
        view.bind("<F4>", self.debug_dump)

    def move_cursor(self, position):
        if position is None:
            self.move_cursor_home()
        else:
            position = self.view.index(position + self.cursor_offset())
            self.view.mark_set(tk.INSERT, position)
            # XXX This does not work?
            self.view.see(position)

    def move_cursor_home(self, event=None):
        self.move_cursor("1.0")

    def move_cursor_end(self, event=None):
        self.move_cursor(tk.END)

    def cursor_offset(self, sign="+"):
        "Return the offset to convert the cursor position to the one to use."
        return f"{sign}{len(str(self))+2}c"

    def cursor_normalized(self):
        "Return the normalized cursor position."
        return self.view.index(tk.INSERT + self.cursor_offset(sign="-"))

    def key_press(self, event):
        "Stop modifying actions."
        if event.char in constants.AFFECTS_CHARACTER_COUNT:
            return "break"

    def get_link(self, tag=None):
        if tag is None:
            for tag in self.view.tag_names(tk.CURRENT):
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
        self.view.tag_add(constants.LINK, first, last)
        self.view.tag_add(tag, first, last)

    def link_enter(self, event):
        link = self.get_link()
        if not link:
            return
        self.view.configure(cursor="hand2")

    def link_leave(self, event):
        self.view.configure(cursor="")

    def link_action(self, event):
        link = self.get_link()
        if link:
            webbrowser.open_new_tab(link["url"])

    def debug_tags(self, event=None):
        ic("--- tags ---", self.view.tag_names(tk.INSERT))
        ic("--- current ---", self.view.index(tk.CURRENT))

    def debug_selected(self, event=None):
        try:
            first, last = self.get_selection(check_no_boundary=False)
        except ValueError:
            return
        ic("--- selected ---",
           self.view.tag_names(first),
           self.view.tag_names(last),
           self.view.dump(first, last))

    def debug_buffer_paste(self, event=None):
        ic("--- paste buffer ---",  self.main.paste_buffer)

    def debug_dump(self, event=None):
        dump = self.view.dump("1.0", tk.END)
        ic("--- dump ---", dump)


class TextViewer(BaseRenderMixin, BaseViewer):
    "Viewer base class for text with Markdown rendering methods and bindings."
 
    def __init__(self, parent, main, text):
        self.indexed = dict()     # Lookup local for the instance.
        self.references = dict()  # Lookup local for the instance.
        super().__init__(parent, main)
        self.text = text
        self.render_title()
        self.render(self.text.ast)

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
        if view is None:
            view = self.view
        super().view_configure_tags(view=view)
        view.tag_configure(constants.H1,
                           font=constants.H1_FONT,
                           lmargin1=constants.H_LEFT_MARGIN,
                           lmargin2=constants.H_LEFT_MARGIN)
        view.tag_configure(constants.H2,
                           font=constants.H2_FONT,
                           lmargin1=constants.H_LEFT_MARGIN,
                           lmargin2=constants.H_LEFT_MARGIN)
        view.tag_configure(constants.H3,
                           font=constants.H3_FONT,
                           lmargin1=constants.H_LEFT_MARGIN,
                           lmargin2=constants.H_LEFT_MARGIN)
        view.tag_configure(constants.H4,
                           font=constants.H4_FONT,
                           lmargin1=constants.H_LEFT_MARGIN,
                           lmargin2=constants.H_LEFT_MARGIN)
        view.tag_configure(constants.QUOTE,
                           lmargin1=constants.QUOTE_LEFT_INDENT,
                           lmargin2=constants.QUOTE_LEFT_INDENT,
                           rmargin=constants.QUOTE_RIGHT_INDENT,
                           spacing1=constants.QUOTE_SPACING1,
                           spacing2=constants.QUOTE_SPACING2,
                           font=constants.QUOTE_FONT)
        view.tag_configure(constants.THEMATIC_BREAK,
                           font=constants.FONT_BOLD,
                           justify=tk.CENTER)
        view.tag_configure(constants.INDEXED, underline=True)
        view.tag_configure(constants.REFERENCE,
                           foreground=constants.REFERENCE_COLOR,
                           underline=True)

    def view_configure_tag_bindings(self, view=None):
        "Configure the tag bindings used in the 'tk.Text' instance."
        if view is None:
            view = self.view
        super().view_configure_tag_bindings(view=view)
        view.tag_bind(constants.INDEXED, "<Enter>", self.indexed_enter)
        view.tag_bind(constants.INDEXED, "<Leave>", self.indexed_leave)
        view.tag_bind(constants.INDEXED, "<Button-1>", self.indexed_action)
        view.tag_bind(constants.REFERENCE, "<Enter>", self.reference_enter)
        view.tag_bind(constants.REFERENCE, "<Leave>", self.reference_leave)
        view.tag_bind(constants.REFERENCE, "<Button-1>", self.reference_action)

    def rerender(self):
        self.links = dict()
        self.text.read()
        self.view.delete("1.0", tk.END)
        self.prev_line_not_blank = False
        self.render_title()
        self.render(self.text.ast)

    def get_selection(self, check_no_boundary=True, adjust=False):
        """Raise ValueError if no current selection, or region boundary (if checked).
        Optionally adjust region to have non-blank beginning and end.
        """
        try:
            first = self.view.index(tk.SEL_FIRST)
            last = self.view.index(tk.SEL_LAST)
        except tk.TclError:
            raise ValueError("no current selection")
        if adjust:
            if self.view.get(first) in string.whitespace:
                original_first = first
                for offset in range(1, 10):
                    first = f"{original_first}+{offset}c"
                    if self.view.get(first) not in string.whitespace:
                        break
            if self.view.get(last + "-1c") in string.whitespace:
                original_last = last
                for offset in range(1, 11):
                    last = f"{original_last}-{offset}c"
                    probe = f"{original_last}-{offset+1}c"
                    if self.view.get(probe) not in string.whitespace:
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
        first_tags = set(self.view.tag_names(first))
        first_tags.discard("sel")
        last_tags = set(self.view.tag_names(last))
        last_tags.discard("sel")
        result = first_tags != last_tags
        if result and show:
            tk_messagebox.showerror(
                parent=self.toplevel,
                title="Region boundary",
                message="Selection contains a region boundary")
        return result

    def reference_enter(self, event):
        self.view.configure(cursor="hand2")

    def reference_leave(self, event):
        self.view.configure(cursor="")

    def reference_action(self, event):
        raise NotImplementedError

    def indexed_enter(self, event):
        self.view.configure(cursor="hand2")

    def indexed_leave(self, event):
        self.view.configure(cursor="")

    def indexed_action(self, event):
        for tag in self.view.tag_names(tk.CURRENT):
            if tag.startswith(constants.INDEXED_PREFIX):
                break
        else:
            return
        self.main.indexed.highlight(tag[len(constants.INDEXED_PREFIX):])

    def render_table(self, ast):
        self.table = Table(self, ast)


class Table(BaseRenderMixin):
    "Table requires its own class for rendering."

    def __init__(self, master, ast):
        self.master = master
        self.frame = ttk.Frame(self.master.view)
        self.master.view.window_create(tk.INSERT, window=self.frame)
        self.view = None
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
        self.view = tk.Text(self.frame,
                            width=width,
                            height=height,
                            padx=constants.TEXT_PADX,
                            font=constants.FONT_NORMAL_FAMILY,
                            wrap=tk.WORD,
                            spacing1=constants.TEXT_SPACING1,
                            spacing2=constants.TEXT_SPACING2,
                            spacing3=constants.TEXT_SPACING3)
        self.master.view_configure_tags(view=self.view)
        self.view.grid(row=self.current_row, column=self.current_column,
                       sticky=(tk.W, tk.E, tk.N, tk.S))
        for child in ast["children"]:
            self.render(child)
        if ast.get("header"):
            self.view.tag_add(constants.BOLD, "1.0", tk.INSERT)

    def len_raw_text(self, ast):
        if ast["element"] == "raw_text":
            return len(ast["children"])
        else:
            return sum([self.len_raw_text(c) for c in ast["children"]])

    def render_link(self, ast):
        raise NotImplementedError
