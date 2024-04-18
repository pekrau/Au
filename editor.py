"Text editor window."

from icecream import ic

import collections
import functools
import io
import json
import os
import webbrowser

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox as tk_messagebox
from tkinter import simpledialog as tk_simpledialog

import yaml

import constants
import utils


class Editor:
    "Text editor window."

    def __init__(self, main, filepath, config):
        self.main = main
        self.filepath = filepath

        # The footnotes lookup is local to each editor window.
        self.footnotes = dict()

        self.toplevel = tk.Toplevel(self.main.root)
        self.toplevel.title(os.path.splitext(self.filepath)[0])
        self.toplevel.bind("<Control-s>", self.save_text)
        self.toplevel.protocol("WM_DELETE_WINDOW", self.close)
        self.toplevel.bind("<Control-q>", self.close)
        self.toplevel.bind("<Home>", self.move_cursor_home)
        self.toplevel.bind("<End>", self.move_cursor_end)
        self.toplevel.bind("<F1>", self.debug_tags)
        self.toplevel.bind("<F2>", self.debug_selected)
        self.toplevel.bind("<F3>", self.debug_paste_buffer)
        self.toplevel.bind("<F4>", self.debug_dump)
        self.toplevel.bind("<F5>", self.debug_raw_dump)

        try:
            self.toplevel.geometry(config["geometry"])
        except KeyError:
            pass

        self.menubar = tk.Menu(self.toplevel)
        self.toplevel["menu"] = self.menubar
        self.menubar.add_command(label="Au",
                                 font=constants.FONT_LARGE_BOLD,
                                 background="gold",
                                 command=self.main.root.lift)

        self.menu_file = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_file, label="File")
        self.menu_file.add_command(label="Rename", command=self.rename_text)
        self.menu_file.add_command(label="Copy", command=self.copy_text)
        self.menu_file.add_command(label="Save",
                                   command=self.save_text,
                                   accelerator="Ctrl-S")
        self.menu_file.add_command(label="Delete", command=self.delete_text)
        self.menu_file.add_command(label="Close", command=self.close,
                                   accelerator="Ctrl-Q")

        self.menu_edit = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_edit, label="Edit")
        self.menu_edit.add_command(label="Copy", command=self.copy)
        self.menu_edit.add_command(label="Cut", command=self.cut)
        self.menu_edit.add_command(label="Paste", command=self.paste)
        self.menu_edit.add_separator()
        self.menu_edit.add_command(label="Add link", command=self.add_link)
        self.menu_edit.add_command(label="Remove link", command=self.remove_link)

        self.menu_format = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_format, label="Format")
        self.menu_format.add_command(label="Bold", command=self.add_bold)
        self.menu_format.add_command(label="Italic", command=self.add_italic)
        self.menu_format.add_command(label="Quote", command=self.add_quote)
        self.menu_format.add_command(label="Footnote", command=self.add_footnote)
        self.menu_format.add_separator()
        self.menu_format.add_command(label="Remove bold", command=self.remove_bold)
        self.menu_format.add_command(label="Remove italic", command=self.remove_italic)
        self.menu_format.add_command(label="Remove quote", command=self.remove_quote)
        self.menu_format.add_command(label="Remove footnote",
                                     command=self.remove_footnote)

        self.menu_status = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_status, label="Status")
        for status in constants.STATUSES:
            command = functools.partial(self.set_status, status=repr(status))
            self.menu_status.add_command(label=str(status), command=command)

        self.text_frame = ttk.Frame(self.toplevel, padding=4)
        self.text_frame.pack(fill=tk.BOTH, expand=1)

        self.text = tk.Text(self.text_frame,
                            width=constants.DEFAULT_TEXT_WIDTH,
                            height=constants.DEFAULT_TEXT_HEIGHT,
                            padx=10,
                            font=constants.FONT_FAMILY_NORMAL,
                            wrap=tk.WORD,
                            spacing1=4,
                            spacing2=8)
        self.text.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.text_frame.rowconfigure(0, weight=1)
        self.text_frame.columnconfigure(0, weight=1)

        self.text.bind("<Key>", self.key_press)
        self.text.bind("<<Modified>>", self.handle_modified)
        self.text.bind("<Button-3>", self.popup_menu)
        self.text.tag_configure(constants.LINK,
                                foreground=constants.LINK_COLOR,
                                underline=True)
        self.text.tag_bind(constants.LINK, "<Enter>", self.enter_link)
        self.text.tag_bind(constants.LINK, "<Leave>", self.leave_link)
        self.text.tag_bind(constants.LINK, "<Button-1>", self.edit_link)

        self.text_scroll_y = ttk.Scrollbar(self.text_frame,
                                           orient=tk.VERTICAL,
                                           command=self.text.yview)
        self.text_scroll_y.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.text.configure(yscrollcommand=self.text_scroll_y.set)

        self.text.tag_configure(constants.ITALIC, font=constants.FONT_ITALIC)
        self.text.tag_configure(constants.BOLD, font=constants.FONT_BOLD)
        self.text.tag_configure("quote",
                                lmargin1=constants.QUOTE_LEFT_INDENT,
                                lmargin2=constants.QUOTE_LEFT_INDENT,
                                rmargin=constants.QUOTE_RIGHT_INDENT,
                                spacing1=0,
                                spacing2=0,
                                font=constants.FONT_FAMILY_QUOTE)
        self.text.tag_configure(constants.FOOTNOTE_REF,
                                foreground=constants.FOOTNOTE_REF_COLOR,
                                font=constants.FONT_BOLD)
        self.text.tag_configure(constants.FOOTNOTE_DEF,
                                background=constants.FOOTNOTE_DEF_COLOR,
                                lmargin1=constants.FOOTNOTE_DEF_MARGIN,
                                lmargin2=constants.FOOTNOTE_DEF_MARGIN,
                                rmargin=constants.FOOTNOTE_DEF_MARGIN)
        self.text.tag_bind(constants.FOOTNOTE_REF, "<Enter>", self.footnote_enter)
        self.text.tag_bind(constants.FOOTNOTE_REF, "<Leave>", self.footnote_leave)

        self.info_frame = ttk.Frame(self.text_frame, padding=2)
        self.info_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        self.text_frame.rowconfigure(1, minsize=22)

        self.size_var = tk.StringVar()
        size_label = ttk.Label(self.info_frame)
        size_label.grid(row=0, column=0, padx=4, sticky=tk.W)
        self.info_frame.columnconfigure(0, weight=1)

        size_label["textvariable"] = self.size_var
        self.url_var = tk.StringVar()
        url_label = ttk.Label(self.info_frame)
        url_label.grid(row=0, column=1, padx=4, sticky=tk.W)
        url_label["textvariable"] = self.url_var
        self.info_frame.columnconfigure(1, weight=1)

        self.title_var = tk.StringVar()
        title_label = ttk.Label(self.info_frame)
        title_label.grid(row=0, column=2, padx=4, sticky=tk.W)
        title_label["textvariable"] = self.title_var
        self.info_frame.columnconfigure(2, weight=1)

        self.status_var = tk.StringVar()
        status_label = ttk.Label(self.info_frame)
        status_label.grid(row=0, column=3, padx=4, sticky=tk.E)
        status_label["textvariable"] = self.status_var
        self.info_frame.columnconfigure(3, weight=1)

        self.frontmatter, ast = utils.get_frontmatter_ast(self.absfilepath)
        self.parsed_footnotes = dict() # For use only while parsing.
        self.parse(ast)

        self.set_status(status=self.frontmatter.get("status"))

        cursor = self.frontmatter.get("cursor") or "1.0"
        self.text.mark_set(tk.INSERT, cursor)
        self.text.see(cursor)
        self.info_update()

        self.ignore_modified_event = True
        self.text.edit_modified(False)
        self.text.update()
        width = self.text.winfo_width() / 2
        url_label.configure(wraplength=width)
        title_label.configure(wraplength=width)
        self.ignore_modified_event = True
        self.text.edit_modified(False)

    def key_press(self, event):
        if event.char not in constants.AFFECTS_CHARACTER_COUNT:
            return
        pos = self.text.index(tk.INSERT)
        tags = self.text.tag_names(pos)
        # Do not allow modifying keys from encroaching on a footnote reference.
        quench = False
        if constants.FOOTNOTE_REF in tags:
            ref_at_right = self.text.tag_nextrange(constants.FOOTNOTE_REF, pos, tk.END)
            if event.keysym == "Return" and not ref_at_right:
                self.footnote_toggle(tags=self.text.tag_names(tk.INSERT))
            quench = True
            if ref_at_right:
                # Delete is special; do not allow it to remove characters at
                # right when just at the beginning of the footnote reference.
                quench = event.keysym == "Delete"
        if quench:
            return "break"
        self.size_var.set(f"{self.character_count} characters")

    def handle_modified(self, event=None):
        if self.ignore_modified_event:
            self.ignore_modified_event = False
        if not self.is_modified:
            return
        self.original_menubar_background = self.menubar.cget("background")
        self.menubar.configure(background=constants.MODIFIED_COLOR)
        self.main.update_treeview_entry(self.filepath, modified=True)

    def get_link(self, tag=None):
        if tag is None:
            for tag in self.text.tag_names(tk.CURRENT):
                if tag.startswith(constants.LINK_PREFIX):
                    break
            else:
                return None
        return self.main.links.get(tag)

    def enter_link(self, event):
        link = self.get_link()
        if not link:
            return
        self.url_var.set(link["url"])
        self.title_var.set(link["title"] or "-")
        self.text.configure(cursor="hand1")

    def leave_link(self, event):
        self.text.configure(cursor="")
        self.url_var.set("")
        self.title_var.set("")

    def edit_link(self, event):
        link = self.get_link()
        if not link:
            return
        edit = EditLink(self.toplevel, link)
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

    def popup_menu(self, event):
        menu = tk.Menu(self.text, tearoff=False)
        tags = self.text.tag_names(tk.CURRENT)
        any_item = False
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
        if constants.FOOTNOTE_REF in tags or constants.FOOTNOTE_DEF in tags:
            menu.add_command(label="Remove footnote", command=self.remove_footnote)
            any_item = True
        try:
            self.text.index(tk.SEL_FIRST)
        except tk.TclError:
            if self.main.paste_buffer:
                menu.add_command(label="Paste", command=self.paste)
                any_item = True
        else:
            if any_item:
                menu.add_separator()
            menu.add_command(label="Link", command=self.add_link)
            menu.add_command(label="Bold", command=self.add_bold)
            menu.add_command(label="Italic", command=self.add_italic)
            menu.add_command(label="Quote", command=self.add_quote)
            menu.add_command(label="Footnote", command=self.add_footnote)
            menu.add_separator()
            menu.add_command(label="Copy", command=self.copy)
            menu.add_command(label="Cut", command=self.cut)
            any_item = True
        if any_item:
            menu.tk_popup(event.x_root, event.y_root)

    @property
    def is_modified(self):
        return self.text.edit_modified()

    def parse(self, ast):
        try:
            method = getattr(self, f"parse_{ast['element']}")
        except AttributeError:
            ic("Could not handle ast", ast)
        else:
            method(ast)

    def parse_document(self, ast):
        self.prev_blank_line = False
        for child in ast["children"]:
            self.parse(child)

    def parse_paragraph(self, ast):
        if self.prev_blank_line:
            self.text.insert(tk.INSERT, "\n")
            self.prev_blank_line = False
        for child in ast["children"]:
            self.parse(child)

    def parse_emphasis(self, ast):
        start = self.text.index(tk.INSERT)
        for child in ast["children"]:
            self.parse(child)
        self.text.tag_add(constants.ITALIC, start, tk.INSERT)

    def parse_strong_emphasis(self, ast):
        start = self.text.index(tk.INSERT)
        for child in ast["children"]:
            self.parse(child)
        self.text.tag_add(constants.BOLD, start, tk.INSERT)

    def parse_raw_text(self, ast):
        children = ast["children"]
        if type(children) == str:
            if children[-1] == "\n":
                children[-1] = " "
            self.text.insert(tk.INSERT, children)
        elif type(children) == list:
            for child in ast["children"]:
                self.parse(child)

    def parse_line_break(self, ast):
        self.text.insert(tk.INSERT, " ")

    def parse_blank_line(self, ast):
        self.text.insert(tk.INSERT, "\n")
        self.prev_blank_line = True

    def parse_link(self, ast):
        start = self.text.index(tk.INSERT)
        for child in ast["children"]:
            self.parse(child)
        self.new_link(ast["dest"], ast["title"], start, tk.INSERT)

    def parse_quote(self, ast):
        if self.prev_blank_line:
            self.text.insert(tk.INSERT, "\n")
        self.prev_blank_line = False
        start = self.text.index(tk.INSERT)
        for child in ast["children"]:
            self.parse(child)
        self.text.tag_add("quote", start, tk.INSERT)

    def parse_footnote_ref(self, ast):
        self.new_footnote_ref(parsed_label=ast["label"])

    def new_footnote_ref(self, parsed_label=None):
        "Create a new footnote in the lookup with unique label and tag."
        label = str(len(self.footnotes) + 1)
        tag = constants.FOOTNOTE_REF_PREFIX + label
        footnote = dict(parsed_label=parsed_label, label=label, tag=tag)
        self.footnotes[label] = footnote
        if parsed_label:
            self.parsed_footnotes[parsed_label] = footnote
        # Insert the standard text '[footnote]' as the visible reference.
        self.text.insert(tk.INSERT, constants.FOOTNOTE, (constants.FOOTNOTE_REF, tag))
        self.text.tag_bind(tag, "<Button-1>", self.footnote_toggle)
        return footnote

    def parse_footnote_def(self, ast):
        parsed_label = ast["label"]
        try:
            footnote = self.parsed_footnotes[parsed_label]
        except KeyError:
            return
        first = self.text.tag_nextrange(footnote["tag"], "1.0", tk.END)[1]
        tag = constants.FOOTNOTE_DEF_PREFIX + footnote["label"]
        self.text.tag_configure(tag, elide=True)
        self.text.mark_set(tk.INSERT, first)
        self.prev_blank_line = False
        for child in ast["children"]:
            self.parse(child)
        # The order of adding tags is essential for 'write_outfile'.
        self.text.tag_add(constants.FOOTNOTE_DEF, first, tk.INSERT)
        self.text.tag_add(tag, first, tk.INSERT)

    def info_update(self):
        self.size_var.set(f"{self.character_count} characters")
        self.status_var.set(str(self.status))
        self.main.update_treeview_entry(self.filepath,
                                        status=str(self.status),
                                        size=f"{self.character_count} ch",
                                        age=self.age)

    @property
    def character_count(self):
        return len(self.text.get("1.0", tk.END))

    @property
    def timestamp(self):
        return utils.get_timestamp(self.absfilepath)

    @property
    def age(self):
        return utils.get_age(self.absfilepath)

    def move_cursor_home(self, event=None):
        self.text.mark_set(tk.INSERT, "1.0")
        self.text.see("1.0")

    def move_cursor_end(self, event=None):
        self.text.mark_set(tk.INSERT, tk.END)
        self.text.see(tk.END)

    def rename_text(self):
        self.main.rename_text(parent=self.toplevel, oldpath=self.filepath)

    def copy_text(self, event=None, parent=None):
        dirpath, filename = os.path.split(self.filepath)
        initialdir = os.path.join(self.main.absdirpath, dirpath)
        name = tk_simpledialog.askstring(
            parent=parent or self.toplevel,
            title="Text copy name",
            prompt="Give the name for the text copy:",
            initialvalue=f"Copy of {os.path.splitext(filename)[0]}")
        if not name:
            return
        name = os.path.splitext(name)[0]
        filepath = os.path.join(dirpath, name + ".md")
        if not self.absfilepath.startswith(self.main.absdirpath):
            tk_messagebox.showerror(
                parent=parent or self.toplevel,
                title="Wrong directory",
                message=f"Must be within {self.main.absdirpath}")
            return
        with open(self.absfilepath, "w") as outfile:
            self.outfiles_stack = [outfile]
            self.write_outfile()
            self.outfiles_stack = []
        self.main.add_treeview_entry(filepath)
        self.main.open_text(filepath=filepath)

    def save_text(self, event=None):
        if not self.is_modified:
            return
        self.frontmatter["cursor"] = self.text.index(tk.INSERT)
        self.frontmatter["status"] = repr(self.status)
        self.main.move_file_to_archive(self.filepath)
        with open(self.absfilepath, "w") as outfile:
            outfile.write("---\n")
            outfile.write(yaml.dump(self.frontmatter))
            outfile.write("---\n")
            self.outfiles_stack = [outfile]
            self.write_outfile()
            self.outfiles_stack = []
        self.menubar.configure(background=self.original_menubar_background)
        self.info_update()
        self.main.update_treeview_entry(self.filepath, modified=False)
        self.ignore_modified_event = True
        self.text.edit_modified(False)

    def delete_text(self):
        if not tk_messagebox.askokcancel(
                parent=self.toplevel,
                title="Delete text?",
                message=f"Really delete text '{self.filepath}'?"):
            return
        self.close(force=True)
        self.main.delete_text(self.filepath, force=True)

    def close(self, event=None, force=False):
        if self.is_modified and not force:
            if not tk_messagebox.askokcancel(
                    parent=self.toplevel,
                    title="Close?",
                    message="Modifications will not be saved. Really close?"):
                return
        self.main.update_treeview_entry(self.filepath, modified=False)
        self.main.texts[self.filepath].pop("editor")
        self.toplevel.destroy()

    def copy(self):
        try:
            first = self.text.index(tk.SEL_FIRST)
            last = self.text.index(tk.SEL_LAST)
        except tk.TclError:
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

    def cut(self):
        try:
            first = self.text.index(tk.SEL_FIRST)
            last = self.text.index(tk.SEL_LAST)
        except tk.TclError:
            return
        self.set_paste_buffer(first, last)
        self.text.delete(first, last)

    def paste(self):
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
                    ic(first, self.text.index(tk.INSERT))
                    self.text.tag_add(constants.FOOTNOTE_DEF, first, tk.INSERT)
                    self.text.tag_add(current_footnote["tag"], first, tk.INSERT)
                    self.text.tag_configure(current_footnote["tag"], elide=False)
                    current_footnote = None

                else:
                    self.text.tag_add(content, tags_first[content], tk.INSERT)
        self.text.tag_remove(tk.SEL, first, tk.INSERT)

    def add_link(self):
        try:
            first = self.text.index(tk.SEL_FIRST)
            last = self.text.index(tk.SEL_LAST)
        except tk.TclError:
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

    def add_bold(self):
        try:
            first = self.text.index(tk.SEL_FIRST)
            last = self.text.index(tk.SEL_LAST)
        except tk.TclError:
            return
        self.text.tag_add(constants.BOLD, first, last)
        self.ignore_modified_event = True
        self.text.edit_modified(True)

    def remove_bold(self):
        try:
            current = self.text.index(tk.INSERT)
        except tk.TclError:
            return
        if constants.BOLD in self.text.tag_names(current):
            pos = self.text.tag_prevrange(constants.BOLD, current)
            if pos:
                self.text.tag_remove(constants.BOLD, *pos)
                self.ignore_modified_event = True
                self.text.edit_modified(True)

    def add_italic(self):
        try:
            first = self.text.index(tk.SEL_FIRST)
            last = self.text.index(tk.SEL_LAST)
        except tk.TclError:
            return
        self.text.tag_add(constants.ITALIC, first, last)
        self.ignore_modified_event = True
        self.text.edit_modified(True)

    def remove_italic(self):
        try:
            current = self.text.index(tk.INSERT)
        except tk.TclError:
            return
        if constants.ITALIC in self.text.tag_names(current):
            pos = self.text.tag_prevrange(constants.ITALIC, current)
            if pos:
                self.text.tag_remove(constants.ITALIC, *pos)
                self.ignore_modified_event = True
                self.text.edit_modified(True)

    def add_quote(self):
        try:
            first = self.text.index(tk.SEL_FIRST)
            last = self.text.index(tk.SEL_LAST)
        except tk.TclError:
            return
        self.text.tag_add(constants.QUOTE, first, last)
        if "\n\n" not in self.text.get(last, last + "+2c"):
            self.text.insert(last, "\n\n")
        if "\n\n" not in self.text.get(first + "-2c", first):
            self.text.insert(first, "\n\n")
        self.ignore_modified_event = True
        self.text.edit_modified(True)

    def remove_quote(self):
        try:
            current = self.text.index(tk.INSERT)
        except tk.TclError:
            return
        if constants.QUOTE in self.text.tag_names(current):
            pos = self.text.tag_prevrange(constants.QUOTE, current)
            if pos:
                self.text.tag_remove(constants.QUOTE, *pos)
                self.ignore_modified_event = True
                self.text.edit_modified(True)

    def add_footnote(self):
        try:
            first = self.text.index(tk.SEL_FIRST)
            last = self.text.index(tk.SEL_LAST)
        except tk.TclError:
            return
        label = str(len(self.footnotes) + 1)
        ref_tag = constants.FOOTNOTE_REF_PREFIX + label
        def_tag = constants.FOOTNOTE_DEF_PREFIX + label
        footnote = dict(label=label, tag=ref_tag, first=first, last=last)
        # The order of adding tags is essential for 'write_outfile'.
        self.text.tag_add(constants.FOOTNOTE_DEF, first, last)
        self.text.tag_add(def_tag, first, last)
        self.text.tag_configure(def_tag, elide=True)
        self.footnotes[label] = footnote
        self.text.insert(first, constants.FOOTNOTE)
        self.text.tag_add(constants.FOOTNOTE_REF, first, tk.INSERT)
        self.text.tag_add(ref_tag, first, tk.INSERT)
        self.text.tag_bind(ref_tag, "<Button-1>", self.footnote_toggle)

    def remove_footnote(self):
        try:
            current = self.text.index(tk.INSERT)
        except tk.TclError:
            return
        tags = self.text.tag_names(tk.INSERT)
        for tag in tags:
            if tag.startswith(constants.FOOTNOTE_REF_PREFIX):
                label = tag[len(constants.FOOTNOTE_REF_PREFIX):]
                break
            elif tag.startswith(constants.FOOTNOTE_DEF_PREFIX):
                label = tag[len(constants.FOOTNOTE_DEF_PREFIX):]
                break
        else:
            return
        # Remove '[footnote]' text.
        tag = constants.FOOTNOTE_REF_PREFIX + label
        first, last = self.text.tag_nextrange(tag, "1.0")
        self.text.tag_remove(constants.FOOTNOTE_REF, first, last)
        self.text.delete(first, last)
        self.text.tag_delete(tag)
        # Remove footnote definition tag; text displayed and selected.
        tag = constants.FOOTNOTE_DEF_PREFIX + label
        first, last = self.text.tag_nextrange(tag, "1.0")
        self.text.tag_remove(constants.FOOTNOTE_DEF, first, last)
        self.text.tag_delete(tag)
        self.text.tag_add(tk.SEL, first, last)
        self.text.mark_set(tk.INSERT, last)
        self.text.see(last)

    def footnote_enter(self, event=None):
        self.text.configure(cursor="dot")

    def footnote_leave(self, event=None):
        self.text.configure(cursor="")

    def footnote_toggle(self, event=None, tags=None):
        if tags is None:
            tags = self.text.tag_names(tk.CURRENT)
        for tag in tags:
            if tag.startswith(constants.FOOTNOTE_REF_PREFIX):
                label = tag[len(constants.FOOTNOTE_REF_PREFIX):]
                break
        else:
            return
        tag = constants.FOOTNOTE_DEF_PREFIX + label
        self.text.tag_configure(tag, elide=not int(self.text.tag_cget(tag, "elide") or 0))

    def set_status(self, status=None):
        ic(status)
        self.status = constants.STATUS_LOOKUP.get(status or 1) or constants.STARTED
        ic(self.status)
        self.status_var.set(str(self.status))
        self.text.edit_modified(True)

    @property
    def absfilepath(self):
        return os.path.join(self.main.absdirpath, self.filepath)

    @property
    def outfile(self):
        return self.outfiles_stack[-1]

    def write_outfile(self):
        self.current_link_tag = None
        self.write_line_indents = []
        self.write_line_indented = False
        self.referred_footnotes = dict()
        self.current_footnote = None
        self.do_not_write_text = False
        for item in self.text.dump("1.0", tk.END):
            try:
                method = getattr(self, f"write_{item[0]}")
            except AttributeError:
                ic("Could not handle item", item)
            else:
                method(item)
        self.write_line_indents = ["  "]
        footnotes = list(self.referred_footnotes.values())
        footnotes.sort(key=lambda f: int(f["label"]))
        previous_newline = False
        for footnote in footnotes:
            if not previous_newline:
                self.outfile.write("\n")
            self.outfile.write(f"\n[^{footnote['label']}]: ")
            self.write_line_indented = True
            value = footnote["outfile"].getvalue() or "*To be defined.*"
            previous_newline = value[-1] == "\n"
            self.write_characters(value)
        self.write_line_indents = []
        if not previous_newline:
            self.outfile.write("\n")

    def write_line_indent(self):
        if self.write_line_indented:
            return
        self.outfile.write("".join(self.write_line_indents))
        self.write_line_indented = True

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
                self.write_line_indented = False
            if segments[-1]:
                self.write_line_indent()
                self.outfile.write(segments[-1])
                self.outfile.write("\n")
                self.write_line_indented = False

    def write_text(self, item):
        if self.do_not_write_text:
            return
        self.write_characters(item[1])

    def write_tagon(self, item):
        tag = item[1]
        try:
            method = getattr(self, f"write_tagon_{tag}")
        except AttributeError:
            # This relies on the order of tags added in 'parse_footnote_def'.
            if tag.startswith(constants.FOOTNOTE_REF_PREFIX):
                self.current_footnote = tag[len(constants.FOOTNOTE_REF_PREFIX):]
            elif tag.startswith(constants.FOOTNOTE_DEF_PREFIX):
                self.current_footnote = tag[len(constants.FOOTNOTE_DEF_PREFIX):]
        else:
            method(item)

    def write_tagoff(self, item):
        try:
            method = getattr(self, f"write_tagoff_{item[1]}")
        except AttributeError:
            pass
        else:
            method(item)

    def write_tagon_italic(self, item):
        self.write_characters("*")

    def write_tagoff_italic(self, item):
        self.write_characters("*")

    def write_tagon_bold(self, item):
        self.write_characters("**")

    def write_tagoff_bold(self, item):
        self.write_characters("**")

    def write_tagon_link(self, item):
        for tag in self.text.tag_names(item[2]):
            if tag.startswith(constants.LINK_PREFIX):
                self.current_link_tag = tag
                self.write_characters("[")
                return

    def write_tagoff_link(self, item):
        link = self.main.links.get(self.current_link_tag)
        if link["title"]:
            self.write_characters(f"""]({link['url']} "{link['title']}")""")
        else:
            self.write_characters(f"]({link['url']})")
        self.current_link_tag = None

    def write_tagon_quote(self, item):
        self.write_line_indents.append("> ")

    def write_tagoff_quote(self, item):
        self.write_line_indents.pop()

    def write_tagon_footnote_ref(self, item):
        try:
            footnote = self.referred_footnotes[self.current_footnote]
        except KeyError:
            # Renumber labels according to which footnote references actually exist.
            label = str(len(self.referred_footnotes) + 1)
            footnote = dict(label=label)
            # 'current_footnote' is the old label.
            self.referred_footnotes[self.current_footnote] = footnote
        self.write_characters(f"[^{label}]")
        self.do_not_write_text = True

    def write_tagoff_footnote_ref(self, item):
        self.current_footnote = None
        self.do_not_write_text = False

    def write_tagon_footnote_def(self, item):
        footnote = self.referred_footnotes[self.current_footnote]
        footnote["outfile"] = io.StringIO()
        self.outfiles_stack.append(footnote["outfile"])

    def write_tagoff_footnote_def(self, item):
        self.current_footnote = None
        outfile = self.outfiles_stack.pop()

    def write_mark(self, item):
        pass

    def debug_tags(self, event=None):
        print("--- tags ---")
        print(self.text.index(tk.INSERT), self.text.tag_names(tk.INSERT))

    def debug_selected(self, event=None):
        try:
            first = self.text.index(tk.SEL_FIRST)
            last = self.text.index(tk.SEL_LAST)
        except tk.TclError:
            return
        print(f"--- dump selected: {first}, {last} ---")
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


class EditLink(tk_simpledialog.Dialog):
    "Dialog window for editing the URL and title for a link."

    def __init__(self, toplevel, link):
        self.link = link
        self.result = None
        super().__init__(toplevel, title="Edit link")

    def body(self, body):
        label = ttk.Label(body, text="URL")
        label.grid(row=0, column=0, padx=4, sticky=tk.E)
        self.url_entry = tk.Entry(body, width=50)
        if self.link["url"]:
            self.url_entry.insert(0, self.link["url"])
        self.url_entry.grid(row=0, column=1)
        label = ttk.Label(body, text="Title")
        label.grid(row=1, column=0, padx=4, sticky=tk.E)
        self.title_entry = tk.Entry(body, width=50)
        if self.link["title"]:
            self.title_entry.insert(0, self.link["title"])
        self.title_entry.grid(row=1, column=1)
        return self.url_entry

    def validate(self):
        self.result = dict(url=self.url_entry.get(),
                           title=self.title_entry.get())
        return True

    def buttonbox(self):
        box = tk.Frame(self)
        w = ttk.Button(box, text="OK", width=10, command=self.ok, default=tk.ACTIVE)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        w = ttk.Button(box, text="Visit", width=10, command=self.visit)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        w = ttk.Button(box, text="Cancel", width=10, command=self.cancel)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)
        box.pack()

    def visit(self):
        webbrowser.open_new_tab(self.url_entry.get())
