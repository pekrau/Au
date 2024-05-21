"""Abstract viewer class containing a tk.Text instance, defining tags and callbacks.
Methods for rendering Marko AST to the tk.Text instance.
"""
import string
import webbrowser

import tkinter as tk
import tkinter.messagebox
import tkinter.ttk

import constants
import utils

from icecream import ic


class Viewer:
    """Abstract viewer class containing a tk.Text instance, defining tags and callbacks.
    Methods for rendering Marko AST to the tk.Text instance.
    """

    TEXT_COLOR = "white"

    def __init__(self, parent, main):
        self.main = main
        self.view_create(parent)
        self.configure_tags()
        self.bind_tags()
        self.bind_events()

    def __len__(self):
        "Number of characters in the 'view' tk.Text instance.."
        return len(self.view.get("1.0", tk.END))

    def view_create(self, parent):
        "Create the 'view' tk.Text instance and its associates."
        self.view_frame = tk.ttk.Frame(parent)
        self.view_frame.pack(fill=tk.BOTH, expand=True)
        self.view_frame.rowconfigure(0, weight=1)
        self.view_frame.columnconfigure(0, weight=1)
        self.view = tk.Text(
            self.view_frame,
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
            self.view_frame, orient=tk.VERTICAL, command=self.view.yview
        )
        self.scroll_y.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.view.configure(yscrollcommand=self.scroll_y.set)

    def configure_tags(self):
        for h in constants.H_LOOKUP.values():
            self.view.tag_configure(
                h["tag"],
                font=h["font"],
                lmargin1=h["left_margin"],
                lmargin2=h["left_margin"],
                spacing3=h["spacing"],
            )
        self.view.tag_configure(constants.ITALIC, font=constants.FONT_ITALIC)
        self.view.tag_configure(constants.BOLD, font=constants.FONT_BOLD)
        self.view.tag_configure(
            constants.QUOTE,
            lmargin1=constants.QUOTE_LEFT_INDENT,
            lmargin2=constants.QUOTE_LEFT_INDENT,
            rmargin=constants.QUOTE_RIGHT_INDENT,
            spacing1=constants.QUOTE_SPACING1,
            spacing2=constants.QUOTE_SPACING2,
            font=constants.QUOTE_FONT,
        )
        self.view.tag_configure(
            constants.THEMATIC_BREAK, font=constants.FONT_BOLD, justify=tk.CENTER
        )
        self.view.tag_configure(constants.INDEXED, underline=True)
        self.view.tag_configure(
            constants.REFERENCE, foreground=constants.REFERENCE_COLOR, underline=True
        )
        self.view.tag_configure(
            constants.FOOTNOTE_REF,
            foreground=constants.FOOTNOTE_REF_COLOR,
            underline=True,
        )
        self.view.tag_configure(
            constants.FOOTNOTE_DEF,
            background=constants.FOOTNOTE_DEF_COLOR,
            borderwidth=1,
            relief=tk.SOLID,
            lmargin1=constants.FOOTNOTE_MARGIN,
            lmargin2=constants.FOOTNOTE_MARGIN,
            rmargin=constants.FOOTNOTE_MARGIN,
        )
        self.view.tag_configure(
            constants.LINK, foreground=constants.LINK_COLOR, underline=True
        )
        self.view.tag_configure(
            constants.XREF, foreground=constants.XREF_COLOR, underline=True
        )
        self.view.tag_configure(
            constants.HIGHLIGHT, background=constants.HIGHLIGHT_COLOR
        )

    def bind_tags(self):
        "Configure the tag bindings used in the 'view' tk.Text instance."
        self.view.tag_bind(constants.LINK, "<Enter>", self.link_enter)
        self.view.tag_bind(constants.LINK, "<Leave>", self.link_leave)
        self.view.tag_bind(constants.LINK, "<Button-1>", self.link_action)
        self.view.tag_bind(constants.XREF, "<Enter>", self.xref_enter)
        self.view.tag_bind(constants.XREF, "<Leave>", self.xref_leave)
        self.view.tag_bind(constants.XREF, "<Button-1>", self.xref_action)
        self.view.tag_bind(constants.INDEXED, "<Enter>", self.indexed_enter)
        self.view.tag_bind(constants.INDEXED, "<Leave>", self.indexed_leave)
        self.view.tag_bind(constants.INDEXED, "<Button-1>", self.indexed_action)
        self.view.tag_bind(constants.REFERENCE, "<Enter>", self.reference_enter)
        self.view.tag_bind(constants.REFERENCE, "<Leave>", self.reference_leave)
        self.view.tag_bind(constants.REFERENCE, "<Button-1>", self.reference_action)
        self.view.tag_bind(constants.FOOTNOTE_REF, "<Enter>", self.footnote_enter)
        self.view.tag_bind(constants.FOOTNOTE_REF, "<Leave>", self.footnote_leave)
        self.view.tag_bind(constants.FOOTNOTE_REF, "<Button-1>", self.footnote_toggle)

    def bind_events(self):
        "Configure the key bindings used in the 'tk.Text' instance."
        self.view.bind("<Home>", self.cursor_home)
        self.view.bind("<End>", self.cursor_end)
        self.view.bind("<Key>", self.key_press)
        self.view.bind("<Control-c>", self.clipboard_copy)
        self.view.bind("<Control-C>", self.clipboard_copy)
        self.view.bind("<F1>", self.debug_tags)
        self.view.bind("<F2>", self.debug_selected)
        self.view.bind("<F3>", self.debug_clipboard)
        self.view.bind("<F4>", self.debug_dump)

    def display(self):
        self.display_initialize()
        self.display_title()
        self.display_view()
        self.display_finalize()

    def display_initialize(self):
        self.prev_line_blank = True
        self.links = {}
        self.xrefs = {}
        self.indexed = {}
        self.references = {}
        self.footnotes = {}
        self.highlighted = None
        self.view.delete("1.0", tk.END)

    def display_title(self):
        "To be defined."
        raise NotImplementedError

    def display_view(self):
        "To be defined."
        raise NotImplementedError

    def display_finalize(self):
        """Get the final positions of the indexed terms and references.
        These are affected by footnotes and can be obtained only after rendering.
        """
        for tag in self.view.tag_names():
            if not tag.startswith(constants.INDEXED_PREFIX):
                continue
            canonical = tag[len(constants.INDEXED_PREFIX) :]
            range = self.view.tag_nextrange(tag, "1.0")
            while range:
                self.indexed.setdefault(canonical, set()).add(range[0])
                range = self.view.tag_nextrange(tag, range[0] + "+1c")
        range = self.view.tag_nextrange(constants.REFERENCE, "1.0")
        while range:
            self.references.setdefault(self.view.get(*range), set()).add(range[0])
            range = self.view.tag_nextrange(constants.REFERENCE, range[0] + "+1c")

    def cursor_home(self, event=None):
        self.view.mark_set(tk.INSERT, "1.0")
        self.view.see(tk.INSERT)

    def cursor_end(self, event=None):
        self.view.mark_set(tk.INSERT, tk.END)
        self.view.see(tk.INSERT)

    def get_cursor(self):
        "Get the position of cursor in absolute number of characters."
        return len(self.view.get("1.0", tk.INSERT))

    def set_cursor(self, position):
        "Set the position of the cursor by the absolute number of characters."
        self.view.mark_set(tk.INSERT, "1.0" + f"+{position}c")
        self.view.see(tk.INSERT)

    cursor = property(get_cursor, set_cursor)

    def clipboard_copy(self, event=None):
        """Copy the current selection into the clipboard.
        Two variants: dump containing formatting for intra-Au use,
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
        "Get the dump of the 'view' tk.Text contents; cleanup and preprocess it."
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

    def conditional_line_break(self, flag=False):
        if self.prev_line_blank:
            return
        self.view.insert(tk.INSERT, "\n")
        self.prev_line_blank = flag

    def render(self, ast):
        try:
            method = getattr(self, f"render_{ast['element']}")
        except AttributeError:
            ic("Could not handle ast", ast)
        else:
            method(ast)

    def render_document(self, ast):
        self.prev_line_blank = True
        for child in ast["children"]:
            self.render(child)

    def render_heading(self, ast):
        "Render as ordinary text."
        self.conditional_line_break()
        for child in ast["children"]:
            self.render(child)

    def render_paragraph(self, ast):
        self.conditional_line_break(flag=True)
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

    def render_line_break(self, ast):
        self.view.insert(tk.INSERT, " ")

    def render_blank_line(self, ast):
        self.view.insert(tk.INSERT, "\n")
        self.prev_line_blank = False

    def render_quote(self, ast):
        self.conditional_line_break(flag=True)
        first = self.view.index(tk.INSERT)
        for child in ast["children"]:
            self.render(child)
        self.view.tag_add(constants.QUOTE, first, tk.INSERT)

    def render_literal(self, ast):
        self.view.insert(tk.INSERT, ast["children"])

    def render_thematic_break(self, ast):
        self.conditional_line_break()
        self.view.insert(tk.INSERT, "\u2014" * 20, (constants.THEMATIC_BREAK,))

    def render_link(self, ast):
        first = self.view.index(tk.INSERT)
        for child in ast["children"]:
            self.render(child)
        self.link_create(ast["dest"], ast["title"], first, self.view.index(tk.INSERT))

    def render_indexed(self, ast):
        # Position at this time is not useful; will be affected by footnotes.
        tag = constants.INDEXED_PREFIX + ast["canonical"]
        self.view.insert(tk.INSERT, ast["term"], (constants.INDEXED, tag))

    def render_reference(self, ast):
        # Position at this time is not useful; will be affected by footnotes.
        tag = constants.REFERENCE_PREFIX + ast["reference"]
        self.view.insert(tk.INSERT, ast["reference"], (constants.REFERENCE, tag))

    def render_footnote_ref(self, ast):
        label = ast["label"]
        tag = constants.FOOTNOTE_REF_PREFIX + label
        self.footnotes[label] = dict(label=label, tag=tag)
        self.view.insert(tk.INSERT, f"^{label}", (constants.FOOTNOTE_REF, tag))

    def render_footnote_def(self, ast):
        tag = self.footnotes[ast["label"]]["tag"]
        first = self.view.tag_nextrange(tag, "1.0")[1]
        self.view.mark_set(tk.INSERT, first)
        for child in ast["children"]:
            self.render(child)
        self.view.tag_add(constants.FOOTNOTE_DEF, first + "+1c", tk.INSERT)
        tag = constants.FOOTNOTE_DEF_PREFIX + ast["label"]
        self.tag_elide(tag)
        self.view.tag_add(tag, first, tk.INSERT)

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

    def indexed_enter(self, event):
        self.view.configure(cursor="hand2")

    def indexed_leave(self, event):
        self.view.configure(cursor="")

    def indexed_action(self, event):
        canonical = self.get_indexed()
        if canonical:
            self.main.indexed_viewer.highlight(canonical)

    def get_indexed(self):
        "Get the canonical indexed term at the current position."
        for tag in self.view.tag_names(tk.CURRENT):
            if tag.startswith(constants.INDEXED_PREFIX):
                return tag[len(constants.INDEXED_PREFIX) :]

    def reference_enter(self, event):
        self.view.configure(cursor="hand2")

    def reference_leave(self, event):
        self.view.configure(cursor="")

    def reference_action(self, event):
        reference = self.get_reference()
        if reference:
            self.main.references_viewer.highlight(reference)

    def get_reference(self):
        for tag in self.view.tag_names(tk.CURRENT):
            if tag.startswith(constants.REFERENCE_PREFIX):
                return tag[len(constants.REFERENCE_PREFIX) :]

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

    @property
    def elided_tags(self):
        """Horrible work-around for apparent Tk/Tcl bug that affects
        searches ot text with tags for elided parts.
        Keep track of all tags set as elided, so that they can be
        temporarily be unelided before a search, and restored after.
        """
        try:
            return self._elided_tags
        except AttributeError:
            self._elided_tags = set()
            return self._elided_tags

    def tag_toggle_elide(self, tag):
        if int(self.view.tag_cget(tag, "elide")):
            self.tag_not_elide(tag)
        else:
            self.tag_elide(tag)

    def tag_elide(self, tag):
        self.view.tag_configure(tag, elide=True)
        self.elided_tags.add(tag)

    def tag_not_elide(self, tag):
        self.view.tag_configure(tag, elide=False)
        self.elided_tags.remove(tag)

    def tags_inhibit_elide(self):
        "Before search, temporarily set all elide tags to not elide."
        for tag in self.elided_tags:
            self.view.tag_configure(tag, elide=False)

    def tags_restore_elide(self):
        "After search, set all elide tags to elide again."
        for tag in self.elided_tags:
            self.view.tag_configure(tag, elide=True)

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
