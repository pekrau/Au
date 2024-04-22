"Mixin for Editor classes."

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
                            width=getattr(self, "TEXT_WIDTH",
                                          constants.DEFAULT_TEXT_WIDTH),
                            height=getattr(self, "TEXT_HEIGHT",
                                           constants.DEFAULT_TEXT_HEIGHT),
                            padx=10,
                            font=constants.FONT_FAMILY_NORMAL,
                            wrap=tk.WORD,
                            spacing1=4,
                            spacing2=8)
        self.text.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.text_frame.rowconfigure(0, weight=1)
        self.text_frame.columnconfigure(0, weight=1)

        self.text.tag_configure(constants.LINK,
                                foreground=constants.LINK_COLOR,
                                underline=True)
        self.text.tag_bind(constants.LINK, "<Enter>", self.link_enter)
        self.text.tag_bind(constants.LINK, "<Leave>", self.link_leave)
        self.text.tag_bind(constants.LINK, "<Button-1>", self.link_edit)

        self.text.tag_configure(constants.INDEXED, underline=True)
        self.text.tag_configure(constants.REFERENCE,
                                foreground=constants.REFERENCE_COLOR)

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
        self.text.bind("<F3>", self.debug_paste_buffer)
        self.text.bind("<F4>", self.debug_dump)
        self.text.bind("<F5>", self.debug_raw_dump)

        self.text.tag_configure(constants.ITALIC, font=constants.FONT_ITALIC)
        self.text.tag_configure(constants.BOLD, font=constants.FONT_BOLD)
        self.text.tag_configure(constants.QUOTE,
                                lmargin1=constants.QUOTE_LEFT_INDENT,
                                lmargin2=constants.QUOTE_LEFT_INDENT,
                                rmargin=constants.QUOTE_RIGHT_INDENT,
                                spacing1=0,
                                spacing2=0,
                                font=constants.FONT_FAMILY_QUOTE)

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
        self.text.configure(cursor="hand1")

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

    def copy_buffer(self):
        "Copy the current selection into the paste buffer."
        try:
            first, last = self.get_selection()
        except ValueError:
            return
        self.set_paste_buffer(first, last)

    def set_paste_buffer(self, first, last):
        self.main.paste_buffer = self.dump(first, last)
        self.text.tag_remove(tk.SEL, first, last)

    def dump(self, first, last):
        "Clean up the raw dump to make it consistent."
        # The selection may contain 'footnote_ref' without the corresponding
        # 'footnote_def', and vice versa. Remove such entries from the dump.
        dump = self.text.dump(first, last)
        footnote_ref = None
        for name, content, pos in dump:
            if name in ("tagon", "tagoff") and content == constants.FOOTNOTE_REF:
                footnote_ref = content
                break
        footnote_def = None
        for name, content, pos in dump:
            if name in ("tagon", "tagoff") and content == constants.FOOTNOTE_DEF:
                footnote_def = content
                break
        broken_footnote = ((footnote_ref and not footnote_def) or
                            (not footnote_ref and footnote_def))
        if broken_footnote:
            result = []
            for name, content, pos in dump:
                if name in ("tagon", "tagoff"):
                    if content == constants.FOOTNOTE_REF:
                        continue
                    if content == constants.FOOTNOTE_DEF:
                        continue
                    if content.startswith(constants.FOOTNOTE_REF_PREFIX):
                        continue
                    if content.startswith(constants.FOOTNOTE_DEF_PREFIX):
                        continue
                result.append((name, content, pos))
            dump = result

        first_tags = list(self.text.tag_names(first))
        skip_tags = set([tk.SEL,
                         constants.LINK,
                         constants.FOOTNOTE_REF,
                         constants.FOOTNOTE_DEF])
        for tag in skip_tags:
            try:
                first_tags.remove(tag)
            except ValueError:
                pass
        for tag in list(first_tags):
            if tag.startswith(constants.FOOTNOTE_DEF_PREFIX):
                first_tags.remove(tag)
        last_tags = set(self.text.tag_names(last)).difference(skip_tags)

        if broken_footnote:
            first_tags = set([t for t in first_tags
                              if not (t.startswith(constants.FOOTNOTE_REF_PREFIX) or
                                      t.startswith(constants.FOOTNOTE_DEF_PREFIX))])
            last_tags = set([t for t in last_tags
                             if not (t.startswith(constants.FOOTNOTE_REF_PREFIX) or
                                     t.startswith(constants.FOOTNOTE_DEF_PREFIX))])

        current_tags = []
        footnote_ref_labels = set()
        result = []
        for name, content, pos in dump:
            if name == "tagon":
                if content in skip_tags:
                    continue
                current_tags.append(content)
            elif name == "tagoff":
                if content in skip_tags:
                    continue
                try:
                    current_tags.remove(content)
                except ValueError:
                    result.insert(0, ("tagon", content, "?"))
            elif name == "mark":
                continue
            result.append((name, content, pos))
        current_tags.extend(last_tags.difference(current_tags))
        for tag in current_tags:
            result.append(("tagoff", tag, "?"))
        return result

    def cut_buffer(self):
        "Cut the current selection into the paste buffer."
        try:
            first, last = self.get_selection()
        except ValueError:
            return
        self.set_paste_buffer(first, last)
        self.text.delete(first, last)

    def paste_buffer(self):
        "Paste in contents from the paste buffer."
        tags_first = dict()
        first = self.text.index(tk.INSERT)
        current_link = None
        current_footnote = None
        do_output_text = True
        self.parsed_footnotes = dict() # For use only while pasting.
        for name, content, pos in self.main.paste_buffer:
            if name == "text":
                if do_output_text:
                    self.text.insert(tk.INSERT, content)

            elif name == "tagon":
                first = self.text.index(tk.INSERT)
                if content.startswith(constants.LINK_PREFIX):
                    current_link = self.get_link(tag=content)
                    current_link["first"] = first

                elif content.startswith(constants.FOOTNOTE_REF_PREFIX):
                    current_footnote = self.new_footnote_ref(
                        parsed_label=content[len(constants.FOOTNOTE_REF_PREFIX):])
                    do_output_text = False

                elif content.startswith(constants.FOOTNOTE_DEF_PREFIX):
                    current_footnote["first"] = first
                    tag = constants.FOOTNOTE_DEF_PREFIX + current_footnote["label"]
                    current_footnote["tag"] = tag
                else:
                    tags_first[content] = first

            elif name == "tagoff":
                if content.startswith(constants.LINK_PREFIX):
                    self.new_link(current_link["url"],
                                  current_link["title"],
                                  current_link["first"],
                                  tk.INSERT)

                elif content == constants.LINK:
                    pass

                elif content == constants.FOOTNOTE:
                    pass

                elif content.startswith(constants.FOOTNOTE_REF_PREFIX):
                    do_output_text = True

                elif content.startswith(constants.FOOTNOTE_DEF_PREFIX):
                    first = current_footnote["first"]
                    self.text.tag_add(constants.FOOTNOTE_DEF, first, tk.INSERT)
                    self.text.tag_add(current_footnote["tag"], first, tk.INSERT)
                    self.text.tag_configure(current_footnote["tag"], elide=False)
                    current_footnote = None

                else:
                    self.text.tag_add(content, tags_first[content], tk.INSERT)
        self.text.tag_remove(tk.SEL, first, tk.INSERT)

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

    def debug_tags(self, event=None):
        print("--- tags ---")
        print(self.text.index(tk.INSERT), self.text.tag_names(tk.INSERT))

    def debug_selected(self, event=None):
        try:
            first, last = self.get_selection(check_no_boundary=False)
        except ValueError:
            return
        print(f"--- dump selected: {first}, {last} ---")
        print(self.text.tag_names(first), self.text.tag_names(last))
        for entry in self.text.dump(first, last):
            print(entry)

    def debug_paste_buffer(self, event=None):
        print("--- dump paste buffer ---")
        for entry in self.main.paste_buffer:
            print(entry)

    def debug_dump(self, event=None):
        print("--- entire dump ---")
        for entry in self.dump("1.0", tk.END):
            print(entry)

    def debug_raw_dump(self, event=None):
        print("--- entire raw dump ---")
        for entry in self.text.dump("1.0", tk.END):
            print(entry)
