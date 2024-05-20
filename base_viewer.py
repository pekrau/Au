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
from render_mixin import RenderMixin


class BaseViewer:
    "Base class with methods for viewer using a 'tk.Text' instance."

    TEXT_COLOR = "white"

    def __init__(self, parent, main):
        self.main = main
        self.view_create(parent)
        self.view_configure_tags()
        self.view_bind_tags()
        self.view_bind_keys()

    def view_create(self, parent):
        "Create the view tk.Text widget and its associates."
        self.frame = tk.ttk.Frame(parent)
        self.frame.pack(fill=tk.BOTH, expand=True)
        self.frame.rowconfigure(0, weight=1)
        self.frame.columnconfigure(0, weight=1)
        self.view = tk.Text(
            self.frame,
            background=self.TEXT_COLOR,
            padx=constants.TEXT_PADX,
            font=constants.FONT,
            wrap=tk.WORD,
            spacing1=constants.TEXT_SPACING1,
            spacing2=constants.TEXT_SPACING2,
            spacing3=constants.TEXT_SPACING3,
        )
        self.view.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.scroll_y = tk.ttk.Scrollbar(
            self.frame, orient=tk.VERTICAL, command=self.view.yview
        )
        self.scroll_y.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.view.configure(yscrollcommand=self.scroll_y.set)

    @property
    def character_count(self):
        return len(self.view.get("1.0", tk.END))

    def view_configure_tags(self, view=None):
        "Configure the tags used in the 'tk.Text' instance."
        view = view or self.view
        for h in constants.H_LOOKUP.values():
            view.tag_configure(
                h["tag"],
                font=h["font"],
                lmargin1=h["left_margin"],
                lmargin2=h["left_margin"],
                spacing3=h["spacing"],
            )
        view.tag_configure(constants.ITALIC, font=constants.FONT_ITALIC)
        view.tag_configure(constants.BOLD, font=constants.FONT_BOLD)
        view.tag_configure(
            constants.LINK, foreground=constants.LINK_COLOR, underline=True
        )
        view.tag_configure(
            constants.XREF, foreground=constants.XREF_COLOR, underline=True
        )
        # view.tag_configure(constants.LIST_BULLET, font=constants.FONT_BOLD)
        view.tag_configure(constants.HIGHLIGHT, background=constants.HIGHLIGHT_COLOR)

    def view_bind_tags(self, view=None):
        "Configure the tag bindings used in the 'tk.Text' instance."
        view = view or self.view
        view.tag_bind(constants.LINK, "<Enter>", self.link_enter)
        view.tag_bind(constants.LINK, "<Leave>", self.link_leave)
        view.tag_bind(constants.LINK, "<Button-1>", self.link_action)
        view.tag_bind(constants.XREF, "<Enter>", self.xref_enter)
        view.tag_bind(constants.XREF, "<Leave>", self.xref_leave)
        view.tag_bind(constants.XREF, "<Button-1>", self.xref_action)

    def view_bind_keys(self, view=None):
        "Configure the key bindings used in the 'tk.Text' instance."
        view = view or self.view
        view.bind("<Home>", self.cursor_home)
        view.bind("<End>", self.cursor_end)
        view.bind("<Key>", self.key_press)
        view.bind("<Control-c>", self.clipboard_copy)
        view.bind("<Control-C>", self.clipboard_copy)
        view.bind("<F1>", self.debug_tags)
        view.bind("<F2>", self.debug_selected)
        view.bind("<F3>", self.debug_clipboard)
        view.bind("<F4>", self.debug_dump)

    def display(self):
        self.display_clear()
        self.display_title()

    def display_clear(self):
        self.links = {}
        self.xrefs = {}
        self.footnotes = {}
        self.highlighted = None
        self.view.delete("1.0", tk.END)

    def display_title(self):
        self.title = str(self) + "\n"
        try:
            h = constants.H_LOOKUP[self.text.depth]
        except KeyError:
            h = constants.H_LOOKUP[constants.MAX_H_LEVEL]
        self.view.insert(tk.INSERT, self.title, (h["tag"],))

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

    def clipboard_copy(self, event=None):
        """Copy the current selection into the clipboard.
        Two variants: with formatting for intra-Au use,
        and characters-only for cross-application use.
        """
        try:
            first, last = self.get_selection()
        except ValueError:
            return
        self.main.clipboard = self.get_dump(first, last)
        self.main.clipboard_chars = self.view.get(first, last)
        self.view.clipboard_clear()
        self.view.clipboard_append(self.main.clipboard_chars)
        return "break"

    def get_dump(self, first, last):
        "Get the dump of the contents, cleanup and preprocess."
        # Get rid of irrelevant marks.
        dump = [
            e
            for e in self.view.dump(first, last)
            if not (
                e[0] == "mark"
                and (e[1] in (tk.INSERT, tk.CURRENT) or e[1].startswith("tk::"))
            )
        ]
        # Get rid of tag SEL.
        dump = [e for e in dump if not (e[0] == "tagon" and e[1] == tk.SEL)]
        # Get link data to make a copy. Skip the position; not relevant.
        result = []
        for kind, value, pos in dump:
            if kind == "tagoff" and value.startswith(constants.LINK_PREFIX):
                link = self.get_link(value)
                result.append((kind, value, link["url"], link["title"]))
            else:
                result.append((kind, value))
        return result

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
                message="Selection contains a range boundary.",
            )
        return result

    def debug_tags(self, event=None):
        ic(
            "--- insert ---",
            self.view.index(tk.INSERT),
            self.cursor,
            self.view.tag_names(tk.INSERT),
        )

    def debug_selected(self, event=None):
        try:
            first, last = self.get_selection(allow_boundary=True)
        except ValueError:
            return
        ic(
            "--- selected ---",
            self.view.tag_names(first),
            self.view.tag_names(last),
            self.view.dump(first, last),
        )

    def debug_clipboard(self, event=None):
        ic("--- clipboard ---", self.main.clipboard)

    def debug_dump(self, event=None):
        dump = self.view.dump("1.0", tk.END)
        ic("--- dump ---", dump)
