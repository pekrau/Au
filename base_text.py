"Base text window with rendering methods and bindings."

from icecream import ic

import os.path

import tkinter as tk
from tkinter import ttk

import constants
import utils


class RenderMixin:
    "Mixin class containing rendering methods."

    def render(self, ast):
        try:
            method = getattr(self, f"render_{ast['element']}")
        except AttributeError:
            ic("Could not handle ast", ast)
        else:
            method(ast)

    def render_document(self, ast):
        self.prev_line_not_blank = False
        for child in ast["children"]:
            self.render(child)

    def render_heading(self, ast):
        self.conditional_line_break()
        first = self.text.index(tk.INSERT)
        h = constants.H.get(ast["level"], constants.H4)
        for child in ast["children"]:
            self.render(child)
        self.text.tag_add(h, first, tk.INSERT)
        self.conditional_line_break()

    def render_paragraph(self, ast):
        self.conditional_line_break(flag=False)
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
        self.prev_line_not_blank = True

    def render_link(self, ast):
        first = self.text.index(tk.INSERT)
        for child in ast["children"]:
            self.render(child)
        self.link_create(ast["dest"], ast["title"], first, self.text.index(tk.INSERT))

    def render_quote(self, ast):
        self.conditional_line_break(flag=False)
        first = self.text.index(tk.INSERT)
        for child in ast["children"]:
            self.render(child)
        self.text.tag_add("quote", first, tk.INSERT)

    def render_thematic_break(self, ast):
        self.conditional_line_break(flag=True)
        self.text.insert(tk.INSERT, "------------------------------------",
                         (constants.THEMATIC_BREAK, ))

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

    def conditional_line_break(self, flag=True):
        if self.prev_line_not_blank:
            self.text.insert(tk.INSERT, "\n")
            self.prev_line_not_blank = flag


class BaseText(RenderMixin):
    "Text window base class with rendering methods and bindings."

    TEXT_COLOR = constants.TEXT_COLOR

    def __init__(self, main, filepath, title=None):
        self.main = main
        self.filepath = filepath
        self.title = title
        self.frontmatter, self.ast = utils.parse(self.absfilepath)
        self.prev_line_not_blank = False
        # These lookups are local for each BaseText instance.
        self.links = dict()
        self.footnotes = dict()

    def __str__(self):
        return self.filepath

    def setup_text(self, parent):
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

        self.text_scroll_y = ttk.Scrollbar(self.frame,
                                           orient=tk.VERTICAL,
                                           command=self.text.yview)
        self.text_scroll_y.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.text.configure(yscrollcommand=self.text_scroll_y.set)

        self.configure_text_tags(self.text)
        self.configure_text_tag_bindings(self.text)

        self.text.bind("<Home>", self.move_cursor_home)
        self.text.bind("<End>", self.move_cursor_end)
        self.text.bind("<Key>", self.key_press)
        self.text.bind("<F1>", self.debug_tags)
        self.text.bind("<F2>", self.debug_selected)
        self.text.bind("<F3>", self.debug_buffer_paste)
        self.text.bind("<F4>", self.debug_dump)

    def configure_text_tags(self, text):
        text.tag_configure(constants.TITLE, font=constants.TITLE_FONT)
        text.tag_configure(constants.H1, font=constants.H1_FONT)
        text.tag_configure(constants.H2, font=constants.H2_FONT)
        text.tag_configure(constants.H3, font=constants.H3_FONT)
        text.tag_configure(constants.H4, font=constants.H4_FONT)
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
        text.tag_configure(constants.FOOTNOTE_REF,
                           foreground=constants.FOOTNOTE_REF_COLOR,
                           underline=True)
        text.tag_configure(constants.FOOTNOTE_DEF,
                           background=constants.FOOTNOTE_DEF_COLOR,
                           borderwidth=1,
                           relief=tk.SOLID,
                           lmargin1=constants.FOOTNOTE_MARGIN,
                           lmargin2=constants.FOOTNOTE_MARGIN,
                           rmargin=constants.FOOTNOTE_MARGIN)

    def configure_text_tag_bindings(self, text):
        text.tag_bind(constants.LINK, "<Enter>", self.link_enter)
        text.tag_bind(constants.LINK, "<Leave>", self.link_leave)
        text.tag_bind(constants.LINK, "<Button-1>", self.link_action)
        text.tag_bind(constants.INDEXED, "<Enter>", self.indexed_enter)
        text.tag_bind(constants.INDEXED, "<Leave>", self.indexed_leave)
        text.tag_bind(constants.INDEXED, "<Button-1>", self.indexed_view)
        text.tag_bind(constants.REFERENCE, "<Enter>", self.reference_enter)
        text.tag_bind(constants.REFERENCE, "<Leave>", self.reference_leave)
        text.tag_bind(constants.REFERENCE, "<Button-1>", self.reference_view)
        text.tag_bind(constants.FOOTNOTE_REF, "<Enter>", self.footnote_enter)
        text.tag_bind(constants.FOOTNOTE_REF, "<Leave>", self.footnote_leave)

    def rerender(self):
        self.frontmatter, self.ast = utils.parse(self.absfilepath)
        self.links = dict()
        self.footnotes = dict()
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
        return len(self.text.get("1.0", tk.END))

    def info_update(self):
        self.main.update_treeview_entry(self.filepath,
                                        status=str(self.status),
                                        size=str(self.character_count),
                                        age=self.age)

    def key_press(self, event):
        raise NotImplementedError

    def move_cursor(self, position):
        if position is None:
            self.move_cursor_home()
        else:
            self.text.mark_set(tk.INSERT, position + self.cursor_offset())
            # XXX This does not work?
            self.text.see(position + self.cursor_offset())

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


    def render_table(self, ast):
        self.table = Table(self, ast)

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


class Table(RenderMixin):
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
        self.master.configure_text_tags(self.text)
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
