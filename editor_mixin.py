"Mixin for Editor classes."

import io

from icecream import ic

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox as tk_messagebox
from tkinter import simpledialog as tk_simpledialog

import constants
import utils
from link_edit import LinkEdit


class EditorMixin:
    "Mixin containing common code for different editor classes."

    TEXT_WIDTH = constants.DEFAULT_TEXT_WIDTH
    TEXT_HEIGHT = constants.DEFAULT_TEXT_HEIGHT

    def setup_toplevel(self, parent, title, geometry=None):
        "Setup the toplevel window."
        self.toplevel = tk.Toplevel(parent)
        self.toplevel.title(title)
        self.toplevel.bind("<Control-s>", self.save)
        self.toplevel.bind("<Control-q>", self.close)
        self.toplevel.protocol("WM_DELETE_WINDOW", self.close)
        if geometry:
            self.toplevel.geometry(geometry)

    def setup_text(self):
        "Setup the text widget and its associates."
        self.text_frame = ttk.Frame(self.toplevel, padding=4)
        self.text_frame.pack(fill=tk.BOTH, expand=1)

        self.text = tk.Text(self.text_frame,
                            width=self.TEXT_WIDTH,
                            height=self.TEXT_HEIGHT,
                            padx=10,
                            font=constants.FONT_FAMILY_NORMAL,
                            wrap=tk.WORD,
                            spacing1=4,
                            spacing2=8)
        self.text.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.text_frame.rowconfigure(0, weight=1)
        self.text_frame.columnconfigure(0, weight=1)

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
        self.text.tag_bind(constants.LINK, "<Button-1>", self.link_edit)

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

        self.text_scroll_y = ttk.Scrollbar(self.text_frame,
                                           orient=tk.VERTICAL,
                                           command=self.text.yview)
        self.text_scroll_y.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.text.configure(yscrollcommand=self.text_scroll_y.set)

        self.text.bind("<<Modified>>", self.handle_modified)
        self.text.bind("<Home>", self.move_cursor_home)
        self.text.bind("<End>", self.move_cursor_end)
        self.text.bind("<Key>", self.key_press)
        self.text.bind("<Button-3>", self.popup_menu)
        self.text.bind("<F1>", self.debug_tags)
        self.text.bind("<F2>", self.debug_selected)
        self.text.bind("<F4>", self.debug_paste_buffer)
        self.text.bind("<F3>", self.debug_dump)

        # The footnotes lookup is local for each TextEditor instance.
        self.footnotes = dict()

        self.ignore_modified_event = False
        self.text.update()

    @property
    def is_modified(self):
        return self.text.edit_modified()

    @property
    def character_count(self):
        return len(self.text.get("1.0", tk.END))

    def handle_modified(self, event=None):
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

    def key_press(self, event):
        raise NotImplementedError

    def popup_menu(self, event):
        menu = tk.Menu(self.text)
        any_item = False
        try:
            first, last = self.get_selection(check_no_boundary=False)
        except ValueError:
            if self.main.paste_buffer:
                menu.add_command(label="Paste", command=self.paste_buffer)
                any_item = True
            tags = self.text.tag_names(tk.CURRENT)
            if constants.LINK in tags:
                menu.add_command(label="Remove link", command=self.remove_link)
                any_item = True
            if constants.BOLD in tags:
                menu.add_command(label="Remove bold", command=self.remove_bold)
                any_item = True
            if constants.ITALIC in tags:
                menu.add_command(label="Remove italic", command=self.remove_italic)
                any_item = True
            if constants.QUOTE in tags:
                menu.add_command(label="Remove quote", command=self.remove_quote)
                any_item = True
        else:
            if not self.selection_contains_boundary(first, last, show=False):
                menu.add_command(label="Link", command=self.add_link)
                menu.add_command(label="Bold", command=self.add_bold)
                menu.add_command(label="Italic", command=self.add_italic)
                menu.add_command(label="Quote", command=self.add_quote)
                menu.add_separator()
                menu.add_command(label="Copy", command=self.copy_buffer)
                menu.add_command(label="Cut", command=self.cut_buffer)
                any_item = True
        if any_item:
            menu.tk_popup(event.x_root, event.y_root)

    def add_bold(self):
        try:
            first, last = self.get_selection(adjust=True)
        except ValueError:
            return
        self.text.tag_add(constants.BOLD, first, last)
        self.ignore_modified_event = True
        self.text.edit_modified(True)

    def remove_bold(self):
        current = self.text.index(tk.INSERT)
        if constants.BOLD in self.text.tag_names(current):
            region = self.text.tag_prevrange(constants.BOLD, current)
            if region:
                self.text.tag_remove(constants.BOLD, *region)
                self.ignore_modified_event = True
                self.text.edit_modified(True)

    def add_italic(self):
        try:
            first, last = self.get_selection(adjust=True)
        except ValueError:
            return
        self.text.tag_add(constants.ITALIC, first, last)
        self.ignore_modified_event = True
        self.text.edit_modified(True)

    def remove_italic(self):
        current = self.text.index(tk.INSERT)
        if constants.ITALIC in self.text.tag_names(current):
            region = self.text.tag_prevrange(constants.ITALIC, current)
            if region:
                self.text.tag_remove(constants.ITALIC, *region)
                self.ignore_modified_event = True
                self.text.edit_modified(True)

    def add_quote(self):
        try:
            first, last = self.get_selection()
        except ValueError:
            return
        self.text.tag_add(constants.QUOTE, first, last)
        if "\n\n" not in self.text.get(last, last + "+2c"):
            self.text.insert(last, "\n\n")
        if "\n\n" not in self.text.get(first + "-2c", first):
            self.text.insert(first, "\n\n")
        self.ignore_modified_event = True
        self.text.edit_modified(True)

    def remove_quote(self):
        current = self.text.index(tk.INSERT)
        if constants.QUOTE in self.text.tag_names(current):
            region = self.text.tag_prevrange(constants.QUOTE, current)
            if region:
                self.text.tag_remove(constants.QUOTE, *region)
                self.ignore_modified_event = True
                self.text.edit_modified(True)

    def save(self, event=None):
        raise NotImplementedError

    def close(self, event=None):
        raise NotImplementedError

    def get_link(self, tag=None):
        if tag is None:
            for tag in self.text.tag_names(tk.CURRENT):
                if tag.startswith(constants.LINK_PREFIX):
                    break
            else:
                return None
        return self.main.links.get(tag)

    def link_enter(self, event):
        link = self.get_link()
        if not link:
            return
        self.text.configure(cursor="hand2")

    def link_leave(self, event):
        self.text.configure(cursor="")

    def link_edit(self, event):
        link = self.get_link()
        if not link:
            return
        edit = LinkEdit(self.toplevel, link)
        if edit.result:
            if edit.result["url"]:
                link["url"] = edit.result["url"]
                link["title"] = edit.result["title"]
            else:
                region = self.text.tag_nextrange(link["tag"], "1.0")
                self.text.tag_remove(constants.LINK, *region)
                self.text.tag_delete(link["tag"])
                # Do not remove entry from 'main.links': the count must be preserved.
            self.ignore_modified_event = True
            self.text.edit_modified(True)

    def add_link(self):
        try:
            first, last = self.get_selection()
        except ValueError:
            return
        url = tk_simpledialog.askstring(
            parent=self.toplevel,
            title="Link URL?",
            prompt="Give URL for link:")
        if not url:
            return
        try:
            url, title = url.strip().split(" ", 1)
            title = title.strip()
            if title.startswith('"'):
                title = title.strip('"')
                title = title.strip()
            elif title.startswith("'"):
                title = title.strip("'")
                title = title.strip()
        except ValueError:
            title = None
        self.new_link(url, title, first, last)
        self.text.tag_remove(tk.SEL, first, last)
        self.ignore_modified_event = True
        self.text.edit_modified(True)

    def new_link(self, url, title, first, last):
        tag = self.main.new_link(url, title)
        self.text.tag_add(constants.LINK, first, last)
        self.text.tag_add(tag, first, last)

    def remove_link(self):
        link = self.get_link()
        if not link:
            return
        if not tk_messagebox.askokcancel(
                parent=self.toplevel,
                title="Remove link?",
                message=f"Really remove link?"):
            return
        first, last = self.text.tag_nextrange(link["tag"], "1.0")
        self.text.tag_delete(link["tag"])
        self.text.tag_remove(constants.LINK, first, last)
        self.ignore_modified_event = True
        self.text.edit_modified(True)
        # Links are not removed from 'main.lookup' during a session.
        # The link count must remain strictly increasing.

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

    def copy_buffer(self):
        "Copy the current selection into the paste buffer."
        try:
            first, last = self.get_selection()
        except ValueError:
            return
        self.main.paste_buffer = self.text.dump(first, last)

    def cut_buffer(self):
        "Cut the current selection into the paste buffer."
        try:
            first, last = self.get_selection()
        except ValueError:
            return
        self.main.paste_buffer = self.text.dump(first, last)
        self.text.delete(first, last)

    def paste_buffer(self):
        "Paste in contents from the paste buffer."
        start = self.text.index(tk.INSERT)
        self.undump(self.main.paste_buffer)
        self.text.tag_remove(tk.SEL, start, tk.INSERT)

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
        start = self.text.index(tk.INSERT)
        for child in ast["children"]:
            self.render(child)
        self.text.tag_add(constants.ITALIC, start, tk.INSERT)

    def render_strong_emphasis(self, ast):
        start = self.text.index(tk.INSERT)
        for child in ast["children"]:
            self.render(child)
        self.text.tag_add(constants.BOLD, start, tk.INSERT)

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
        start = self.text.index(tk.INSERT)
        for child in ast["children"]:
            self.render(child)
        self.new_link(ast["dest"], ast["title"], start, tk.INSERT)

    def render_quote(self, ast):
        if self.prev_blank_line:
            self.text.insert(tk.INSERT, "\n")
        self.prev_blank_line = False
        start = self.text.index(tk.INSERT)
        for child in ast["children"]:
            self.render(child)
        self.text.tag_add("quote", start, tk.INSERT)

    def render_footnote_ref(self, ast):
        label = ast["label"]
        tag = constants.FOOTNOTE_REF_PREFIX + label
        self.text.insert(tk.INSERT, f"^{label}", (constants.FOOTNOTE_REF, tag))
        self.footnotes[label] = dict(label=label, tag=tag)
        self.text.tag_bind(tag, "<Button-1>", self.footnote_toggle)

    def render_footnote_def(self, ast):
        tag = self.footnotes[ast["label"]]["tag"]
        start = self.text.tag_nextrange(tag, "1.0")[1]
        self.text.mark_set(tk.INSERT, start)
        for child in ast["children"]:
            self.render(child)
        self.text.tag_add(constants.FOOTNOTE_DEF, start + "+1c", tk.INSERT)
        tag = constants.FOOTNOTE_DEF_PREFIX + ast["label"]
        self.text.tag_configure(tag, elide=True)
        self.text.tag_add(tag, start, tk.INSERT)

    def render_indexed(self, ast):
        self.text.insert(tk.INSERT, ast["target"], constants.INDEXED)

    def render_reference(self, ast):
        self.text.insert(tk.INSERT, f"{ast['target']}", constants.REFERENCE)

    def undump(self, dump):
        tags = dict()
        for entry in dump:
            try:
                method = getattr(self, f"undump_{entry[0]}")
            except AttributeError:
                ic("Could not handle", entry)
            else:
                method(entry, tags)

    def undump_text(self, entry, tags):
        self.text.insert(tk.INSERT, entry[1])

    def undump_tagon(self, entry, tags):
        tags[entry[1]] = self.text.index(tk.INSERT)

    def undump_tagoff(self, entry, tags):
        try:
            start = tags.pop(entry[1])
        except KeyError:
            ic("No tagon for", entry)
        else:
            self.text.tag_add(entry[1], start, tk.INSERT)

    def undump_mark(self, entry, tags):
        if entry[1] in (tk.INSERT, tk.CURRENT):
            return
        if entry[1].startswith("tk::"):
            return
        self.text.mark_set(entry[1], tk.INSERT)

    @property
    def outfile(self):
        return self.outfile_stack[-1]

    def set_outfile(self, outfile=None):
        if outfile is None:
            self.outfile_stack = []
        else:
            self.outfile_stack = [outfile]

    def write(self):
        self.current_link_tag = None
        self.write_line_indents = []
        self.written_line_indent = False
        self.write_skip_text = False
        self.referred_footnotes = dict()
        for item in self.text.dump("1.0", tk.END):
            try:
                method = getattr(self, f"handle_{item[0]}")
            except AttributeError:
                ic("Could not handle item", item)
            else:
                method(item)
        for label, footnote in sorted(self.referred_footnotes.items()):
            self.outfile.write(f"[^{label}]: ")
            lines = footnote["outfile"].getvalue().split("\n")
            self.outfile.write(lines[0] + "\n")
            for line in lines[1:]:
                self.outfile.write("  " + line + "\n")

    def write_line_indent(self):
        if self.written_line_indent:
            return
        self.outfile.write("".join(self.write_line_indents))
        self.written_line_indent = True

    def write_characters(self, characters):
        if not characters:
            return
        segments = characters.split("\n")
        if len(segments) == 1:
            self.write_line_indent()
            self.outfile.write(segments[0])
        else:
            for segment in segments[:-1]:
                self.write_line_indent()
                self.outfile.write(segment)
                self.outfile.write("\n")
                self.written_line_indent = False
            if segments[-1]:
                self.write_line_indent()
                self.outfile.write(segments[-1])
                self.outfile.write("\n")
                self.written_line_indent = False

    def handle_text(self, item):
        if self.write_skip_text:
            return
        self.write_characters(item[1])

    def handle_mark(self, item):
        pass

    def handle_tagon(self, item):
        tag = item[1]
        try:
            method = getattr(self, f"handle_tagon_{tag}")
        except AttributeError:
            pass
        else:
            method(item)

    def handle_tagoff(self, item):
        try:
            method = getattr(self, f"handle_tagoff_{item[1]}")
        except AttributeError:
            pass
        else:
            method(item)

    def handle_tagon_italic(self, item):
        self.write_characters("*")

    def handle_tagoff_italic(self, item):
        self.write_characters("*")

    def handle_tagon_bold(self, item):
        self.write_characters("**")

    def handle_tagoff_bold(self, item):
        self.write_characters("**")

    def handle_tagon_link(self, item):
        for tag in self.text.tag_names(item[2]):
            if tag.startswith(constants.LINK_PREFIX):
                self.current_link_tag = tag
                self.write_characters("[")
                return

    def handle_tagoff_link(self, item):
        link = self.main.links.get(self.current_link_tag)
        if link["title"]:
            self.write_characters(f"""]({link['url']} "{link['title']}")""")
        else:
            self.write_characters(f"]({link['url']})")
        self.current_link_tag = None

    def handle_tagon_quote(self, item):
        self.write_line_indents.append("> ")

    def handle_tagoff_quote(self, item):
        self.write_line_indents.pop()

    def handle_tagon_footnote_ref(self, item):
        for tag in self.text.tag_names(item[2]):
            if tag.startswith(constants.FOOTNOTE_REF_PREFIX):
                label = tag[len(constants.FOOTNOTE_REF_PREFIX):]
                self.referred_footnotes[label] = self.footnotes[label]
                break
        self.write_characters(f"[^{label}]")
        self.write_skip_text = True

    def handle_tagoff_footnote_ref(self, item):
        pass

    def handle_tagon_footnote_def(self, item):
        for tag in self.text.tag_names(item[2]):
            if tag.startswith(constants.FOOTNOTE_DEF_PREFIX):
                label = tag[len(constants.FOOTNOTE_DEF_PREFIX):]
        footnote = self.referred_footnotes[label]
        footnote["outfile"] = io.StringIO()
        self.outfile_stack.append(footnote["outfile"])
        self.write_skip_text = False

    def handle_tagoff_footnote_def(self, item):
        self.outfile_stack.pop()

    def handle_tagon_indexed(self, item):
        self.write_characters("[#")

    def handle_tagoff_indexed(self, item):
        self.write_characters("]")

    def handle_tagon_reference(self, item):
        self.write_characters("[@")

    def handle_tagoff_reference(self, item):
        self.write_characters("]")

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

    def debug_paste_buffer(self, event=None):
        ic("--- paste buffer ---",  self.main.paste_buffer)

    def debug_dump(self, event=None):
        dump = self.text.dump("1.0", tk.END)
        ic("--- dump ---", dump)
