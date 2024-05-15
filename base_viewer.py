"Base viewer classes with rendering methods and bindings."

from icecream import ic

import os.path
import string
import webbrowser

import tkinter as tk
import tkinter.messagebox
import tkinter.ttk

import constants
import utils
from render_mixins import BaseRenderMixin


class BaseViewer:
    "Base class with methods for viewer using a 'tk.Text' instance."

    TEXT_COLOR = "white"

    def __init__(self, parent, main):
        self.main = main
        self.view_create(parent)
        self.view_configure_tags()
        self.view_configure_tag_bindings()
        self.view_bind_keys()

    def view_create(self, parent):
        "Create the view tk.Text widget and its associates."
        self.frame = tk.ttk.Frame(parent)
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
        self.scroll_y = tk.ttk.Scrollbar(self.frame,
                                         orient=tk.VERTICAL,
                                         command=self.view.yview)
        self.scroll_y.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.view.configure(yscrollcommand=self.scroll_y.set)

    @property
    def character_count(self):
        return len(self.view.get("1.0", tk.END))

    def view_configure_tags(self, view=None):
        "Configure the tags used in the 'tk.Text' instance."
        if view is None:
            view = self.view
        for h in constants.H_LOOKUP.values():
            view.tag_configure(h["tag"],
                               font=h["font"],
                               lmargin1=h["left_margin"],
                               lmargin2=h["left_margin"],
                               spacing3=h["spacing"])
        view.tag_configure(constants.ITALIC, font=constants.FONT_ITALIC)
        view.tag_configure(constants.BOLD, font=constants.FONT_BOLD)
        view.tag_configure(constants.LINK,
                           foreground=constants.LINK_COLOR,
                           underline=True)
        view.tag_configure(constants.XREF,
                           foreground=constants.XREF_COLOR,
                           underline=True)
        view.tag_configure(constants.LIST_BULLET, font=constants.FONT_BOLD)
        view.tag_configure(constants.HIGHLIGHT,
                           background=constants.HIGHLIGHT_COLOR)

    def view_configure_tag_bindings(self, view=None):
        "Configure the tag bindings used in the 'tk.Text' instance."
        if view is None:
            view = self.view
        view.tag_bind(constants.LINK, "<Enter>", self.link_enter)
        view.tag_bind(constants.LINK, "<Leave>", self.link_leave)
        view.tag_bind(constants.LINK, "<Button-1>", self.link_action)
        view.tag_bind(constants.XREF, "<Enter>", self.xref_enter)
        view.tag_bind(constants.XREF, "<Leave>", self.xref_leave)
        view.tag_bind(constants.XREF, "<Button-1>", self.xref_action)

    def view_bind_keys(self, view=None):
        "Configure the key bindings used in the 'tk.Text' instance."
        if view is None:
            view = self.view
        view.bind("<Home>", self.cursor_home)
        view.bind("<End>", self.cursor_end)
        view.bind("<Key>", self.key_press)
        view.bind("<Control-c>", self.clipboad_copy)
        view.bind("<Control-C>", self.clipboad_copy)
        view.bind("<Control-v>", self.clipboad_paste)
        view.bind("<Control-V>", self.clipboad_paste)
        view.bind("<F1>", self.debug_tags)
        view.bind("<F2>", self.debug_selected)
        view.bind("<F3>", self.debug_buffer_paste)
        view.bind("<F4>", self.debug_dump)

    def display_wipe(self):
        self.links = dict()
        self.xrefs = dict()
        self.highlighted = None
        self.view.delete("1.0", tk.END)

    def display_title(self):
        self.title = f"{self}\n"
        try:
            h = constants.H_LOOKUP[self.text.depth]
        except KeyError:
            h = constants.H_LOOKUP[constants.MAX_H_LEVEL]
        self.view.insert(tk.INSERT, self.title, (h["tag"], ))

    def cursor_home(self, event=None):
        self.view.mark_set(tk.INSERT, "1.0")
        self.view.see(tk.INSERT)

    def cursor_end(self, event=None):
        self.view.mark_set(tk.INSERT, tk.END)
        self.view.see(tk.INSERT)

    def get_cursor(self):
        "Get the position of cursor in absolute number of characters."
        result = len(self.view.get("1.0", tk.INSERT))
        try:
            result -= len(self.title)
        except AttributeError:
            pass
        return result

    def set_cursor(self, position):
        "Set the position of the cursor by the absolute number of characters."
        try:
            position += len(self.title)
        except AttributeError:
            pass
        self.view.mark_set(tk.INSERT, "1.0" + f"+{position}c")
        self.view.see(tk.INSERT)

    cursor = property(get_cursor, set_cursor)

    def clipboad_copy(self, event):
        "Copy any selected text to the clipboard."
        try:
            first = self.view.index(tk.SEL_FIRST)
            last = self.view.index(tk.SEL_LAST)
        except tk.TclError:
            return
        self.view.clipboard_clear()
        self.view.clipboard_append(self.view.get(first, last))
        return "break"

    def clipboad_paste(self, event):
        "Paste the clipboard contents into the text."
        self.view.insert(tk.INTER, self.view.clipboard_get())
        return "break"

    def key_press(self, event):
        "Stop all key presses that produce a character."
        if event.char:
            return "break"

    def render_link(self, ast):
        first = self.view.index(tk.INSERT)
        for child in ast["children"]:
            self.render(child)
        self.link_create(ast["dest"], ast["title"], first, self.view.index(tk.INSERT))

    def link_create(self, url, title, first, last):
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
        if not link:
            return
        webbrowser.open_new_tab(link["url"])

    def get_link(self, tag=None):
        if tag is None:
            for tag in self.view.tag_names(tk.CURRENT):
                if tag.startswith(constants.LINK_PREFIX):
                    break
            else:
                return None
        return self.links.get(tag)

    def xref_create(self, fullname, position, target_tag):
        tag = f"{constants.XREF_PREFIX}{len(self.xrefs) + 1}"
        self.view.insert(tk.INSERT, fullname, (constants.XREF, tag))
        self.xrefs[tag] = dict(tag=target_tag, fullname=fullname, position=position)

    def xref_enter(self, event):
        xref = self.get_xref()
        if not xref:
            return
        self.view.configure(cursor="hand1")

    def xref_leave(self, event):
        self.view.configure(cursor="")

    def xref_action(self, event):
        xref = self.get_xref()
        if not xref:
            return
        text = self.main.source[xref["fullname"]]
        assert text.is_text
        self.main.texts_notebook.select(text.tabid)
        text.viewer.highlight(xref["position"], tag=xref["tag"])

    def get_xref(self, tag=None):
        if tag is None:
            for tag in self.view.tag_names(tk.CURRENT):
                if tag.startswith(constants.XREF_PREFIX):
                    break
            else:
                return None
        return self.xrefs.get(tag)

    def highlight(self, first, last=None, tag=None):
        "Highlight the characters marked by the tag starting at the given position."
        self.view.focus_set()
        if self.highlighted:
            self.view.tag_remove(constants.HIGHLIGHT, *self.highlighted)
        if last is None:
            if tag is None:
                raise ValueError("Must provide either 'last' or 'tag'.")
            first, last = self.view.tag_nextrange(tag, first)
        self.view.tag_add(constants.HIGHLIGHT, first, last)
        self.highlighted = (first, last)
        self.view.see(first)
        self.view.update()

    def debug_tags(self, event=None):
        ic("--- insert ---",
           self.view.index(tk.INSERT),
           self.cursor,
           self.view.tag_names(tk.INSERT))

    def debug_selected(self, event=None):
        try:
            first, last = self.get_selection(allow_boundary=True)
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


class BaseTextViewer(BaseRenderMixin, BaseViewer):
    "Viewer base class for text with Markdown rendering methods and bindings."
 
    def __init__(self, parent, main, text):
        super().__init__(parent, main)
        self.text = text
        self.display(reread_text=False)

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

    def display(self, reread_text=True):
        if reread_text:
            self.text.read()
        self.display_wipe()
        self.display_title()
        self.prev_line_blank = True
        self.render(self.text.ast)
        self.locate_indexed()
        self.locate_references()

    def get_selection(self, allow_boundary=False, strip=False):
        """Raise ValueError if no current selection.
        Optionally allow tag region boundaries in the selection.
        Optionally modify range to have non-blank beginning and end.
        """
        try:
            first = self.view.index(tk.SEL_FIRST)
            last = self.view.index(tk.SEL_LAST)
        except tk.TclError:
            raise ValueError("no current selection")
        if strip:
            while self.view.get(first) in string.whitespace:
                if self.view.compare(first, ">=", last):
                    break
                first = self.view.index(first + "+1c")
            while self.view.get(last + "-1c") in string.whitespace:
                if self.view.compare(first, ">=", last):
                    break
                last = self.view.index(last + "-1c")
        if not allow_boundary:
            if self.selection_contains_boundary(first, last):
                raise ValueError
        return first, last

    def selection_contains_boundary(self, first=None, last=None, complain=True):
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
        if result and complain:
            tk.messagebox.showerror(
                parent=self.toplevel,
                title="Range boundary",
                message="Selection contains a range boundary.")
        return result

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
                return tag[len(constants.REFERENCE_PREFIX):]

    def indexed_enter(self, event):
        self.view.configure(cursor="hand2")

    def indexed_leave(self, event):
        self.view.configure(cursor="")

    def indexed_action(self, event):
        term = self.get_indexed()
        if term:
            self.main.indexed_viewer.highlight(term)

    def get_indexed(self):
        for tag in self.view.tag_names(tk.CURRENT):
            if tag.startswith(constants.INDEXED_PREFIX):
                return tag[len(constants.INDEXED_PREFIX):]

    def render_table(self, ast):
        self.table = Table(self, ast)


class Table(BaseRenderMixin):
    "Read-only table requires its own class for rendering."

    def __init__(self, master, ast):
        self.master = master
        self.frame = tk.ttk.Frame(self.master.view)
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
        self.view.configure(state=tk.DISABLED)

    def len_raw_text(self, ast):
        if ast["element"] == "raw_text":
            return len(ast["children"])
        else:
            return sum([self.len_raw_text(c) for c in ast["children"]])

    def render_link(self, ast):
        raise NotImplementedError
