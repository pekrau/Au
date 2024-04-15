"Text editor window."

from icecream import ic

import collections
import io
import json
import os
import sys

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox as tk_messagebox
from tkinter import simpledialog as tk_simpledialog

import constants
import links
import utils


class Editor:
    "Text editor window."

    def __init__(self, main, filepath):
        self.main = main
        self.filepath = filepath
        self.toplevel = tk.Toplevel(self.main.root)
        self.toplevel.title(os.path.splitext(self.filepath)[0])
        self.toplevel.protocol("WM_DELETE_WINDOW", self.close)

        config = self.main.configuration["texts"].setdefault(self.filepath, dict())
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
        self.menu_file.add_command(label="Rename", command=self.rename)
        self.menu_file.add_command(label="Copy", command=self.copy)
        self.menu_file.add_command(label="Save",
                                   command=self.save,
                                   accelerator="Ctrl-S")
        self.toplevel.bind("<Control-s>", self.save)
        self.menu_file.add_separator()
        self.menu_file.add_command(label="Delete", command=self.delete)
        self.menu_file.add_separator()
        self.menu_file.add_command(label="Close", command=self.close,
                                   accelerator="Ctrl-W")
        self.toplevel.bind("<Control-w>", self.close)
        self.toplevel.bind("<Home>", self.move_cursor_home)
        self.toplevel.bind("<End>", self.move_cursor_end)

        self.menu_edit = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_edit, label="Edit")
        self.menu_edit.add_command(label="Link", command=self.add_link)
        self.menu_edit.add_command(label="Bold", command=self.add_bold)
        self.menu_edit.add_command(label="Italic", command=self.add_italic)
        self.menu_edit.add_command(label="Quote", command=self.add_quote)
        self.menu_edit.add_command(label="Footnote", command=self.add_footnote)
        self.menu_edit.add_separator()
        self.menu_edit.add_command(label="Remove link", command=self.remove_link)
        self.menu_edit.add_command(label="Remove bold", command=self.remove_bold)
        self.menu_edit.add_command(label="Remove italic", command=self.remove_italic)
        self.menu_edit.add_command(label="Remove quote", command=self.remove_quote)
        self.menu_edit.add_command(label="Remove footnote",
                                   command=self.remove_footnote)

        self.text_frame = ttk.Frame(self.toplevel, padding=4)
        self.text_frame.pack(fill=tk.BOTH, expand=1)
        self.text_frame.rowconfigure(0, weight=1)
        self.text_frame.columnconfigure(0, weight=1)

        self.text = tk.Text(self.text_frame,
                            width=constants.DEFAULT_TEXT_WIDTH,
                            height=constants.DEFAULT_TEXT_HEIGHT,
                            padx=10,
                            font=constants.FONT_FAMILY_NORMAL,
                            wrap=tk.WORD,
                            spacing1=4,
                            spacing2=8)
        self.text.grid(column=0, row=0, sticky=(tk.N, tk.S, tk.E, tk.W))
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
                                lmargin1=constants.FOOTNOTE_DEF_MARGIN,
                                lmargin2=constants.FOOTNOTE_DEF_MARGIN,
                                rmargin=constants.FOOTNOTE_DEF_MARGIN,
                                background=constants.FOOTNOTE_DEF_COLOR,
                                borderwidth=3,
                                relief=tk.SUNKEN)
        self.text.tag_bind(constants.FOOTNOTE_REF, "<Enter>", self.footnote_enter)
        self.text.tag_bind(constants.FOOTNOTE_REF, "<Leave>", self.footnote_leave)
        self.text.tag_bind(constants.FOOTNOTE_REF, "<Button-1>", self.footnote_toggle)

        self.menu_right_click = tk.Menu(self.text, tearoff=False)
        self.text.bind("<Button-3>", self.popup_menu_right_click)
        self.menu_right_click.add_command(label="Link", command=self.add_link)
        self.menu_right_click.add_command(label="Bold", command=self.add_bold)
        self.menu_right_click.add_command(label="Italic", command=self.add_italic)
        self.menu_right_click.add_command(label="Quote", command=self.add_quote)
        self.menu_right_click.add_command(label="Footnote", command=self.add_footnote)
        self.menu_right_click.add_separator()
        self.menu_right_click.add_command(label="Remove link", command=self.remove_link)
        self.menu_right_click.add_command(label="Remove bold", command=self.remove_bold)
        self.menu_right_click.add_command(label="Remove italic",
                                          command=self.remove_italic)
        self.menu_right_click.add_command(label="Remove footnote",
                                          command=self.remove_footnote)

        self.info_frame = ttk.Frame(self.toplevel, padding=4)
        self.info_frame.pack(fill=tk.X, expand=1)
        self.info_frame.rowconfigure(0, weight=1)
        self.info_frame.columnconfigure(0, weight=1)
        self.info_frame.columnconfigure(1, weight=2)
        self.info_frame.columnconfigure(2, weight=2)
        self.size_var = tk.StringVar()
        size_label = ttk.Label(self.info_frame)
        size_label.grid(column=0, row=0, sticky=tk.W, padx=4)
        size_label["textvariable"] = self.size_var
        self.url_var = tk.StringVar()
        url_label = ttk.Label(self.info_frame, anchor=tk.W)
        url_label.grid(column=1, row=0, sticky=tk.W, padx=4)
        url_label["textvariable"] = self.url_var
        self.title_var = tk.StringVar()
        title_label = ttk.Label(self.info_frame, anchor=tk.W)
        title_label.grid(column=2, row=0, sticky=tk.W, padx=4)
        title_label["textvariable"] = self.title_var

        path = os.path.join(self.main.absdirpath, self.filepath)
        self.timestamp = utils.get_time(path)
        with open(path) as infile:
            ast = utils.get_ast(infile.read())
        # ic(ast)
        self.links = links.Links(self)
        self.footnotes = dict()
        self.footnotes_tmp = dict()
        self.parse(ast)
        self.info_update()

        self.text.update()
        width = self.text.winfo_width() / 2
        url_label.configure(wraplength=width)
        title_label.configure(wraplength=width)

        self.text.bind("<Key>", self.key_press)
        self.text.bind("<<Modified>>", self.handle_modified)
        self.ignore_modified_event = True
        self.text.edit_modified(False)

    def popup_menu_right_click(self, event):
        self.menu_right_click.tk_popup(event.x_root, event.y_root)

    def key_press(self, event):
        if event.keysym == "Escape":
            for entry in self.text.dump("1.0", tk.END):
                print(entry)
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
        self.info_update(size_only=True)

    def handle_modified(self, event=None):
        if self.ignore_modified_event:
            self.ignore_modified_event = False
        if not self.is_modified:
            return
        self.original_menubar_background = self.menubar.cget("background")
        self.menubar.configure(background=constants.MODIFIED_COLOR)
        self.main.flag_treeview_entry(self.filepath, modified=True)

    def get_configuration(self):
        return dict(geometry=self.toplevel.geometry())

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
        self.text.tag_add(constants.ITALIC, start, self.text.index(tk.INSERT))

    def parse_strong_emphasis(self, ast):
        start = self.text.index(tk.INSERT)
        for child in ast["children"]:
            self.parse(child)
        self.text.tag_add(constants.BOLD, start, self.text.index(tk.INSERT))

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
        try:
            links = self.links
        except AttributeError:
            pass
        else:
            links.add(ast, start, tk.INSERT)

    def parse_quote(self, ast):
        if self.prev_blank_line:
            self.text.insert(tk.INSERT, "\n")
        self.prev_blank_line = False
        start = self.text.index(tk.INSERT)
        for child in ast["children"]:
            self.parse(child)
        self.text.tag_add("quote", start, self.text.index(tk.INSERT))

    def parse_footnote_ref(self, ast):
        parsed_label = ast["label"]
        # Re-label using the number of actually occurring footnotes.
        label = str(len(self.footnotes) + 1)
        tag = constants.FOOTNOTE_REF_PREFIX + label
        footnote = dict(label=label, tag=tag)
        self.footnotes[label] = footnote
        self.footnotes_tmp[parsed_label] = footnote
        start = self.text.index(tk.INSERT)
        self.text.insert(tk.INSERT, "[footnote]")
        self.text.tag_add(constants.FOOTNOTE_REF, start, self.text.index(tk.INSERT))
        self.text.tag_add(tag, start, self.text.index(tk.INSERT))
        footnote["first"] = self.text.index(tk.INSERT)

    def parse_footnote_def(self, ast):
        label = ast["label"]
        try:
            footnote = self.footnotes_tmp[label]
        except KeyError:
            return
        tag = constants.FOOTNOTE_DEF_PREFIX + label
        self.text.tag_configure(tag, elide=True)
        self.text.mark_set(tk.INSERT, footnote["first"])
        for child in ast["children"]:
            self.parse(child)
        # The order of added tags is essential for 'write_outfile'.
        self.text.tag_add(constants.FOOTNOTE_DEF, footnote["first"], tk.INSERT)
        self.text.tag_add(tag, footnote["first"], tk.INSERT)
        footnote["last"] = self.text.index(tk.INSERT)

    def info_update(self, size_only=False):
        self.size_var.set(f"{self.character_count} characters")
        self.main.treeview.set(self.filepath, "characters",
                               f"{self.character_count} ch")
        if not size_only:
            self.main.treeview.set(self.filepath, "timestamp", self.timestamp)

    @property
    def character_count(self):
        return len(self.text.get("1.0", tk.END))

    def move_cursor_home(self, event=None):
        self.text.mark_set(tk.INSERT, "1.0")
        self.text.see("1.0")

    def move_cursor_end(self, event=None):
        self.text.mark_set(tk.INSERT, tk.END)
        self.text.see(tk.END)

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
        self.links.new(url, title, first, last)
        self.ignore_modified_event = True
        self.text.edit_modified(True)

    def remove_link(self):
        try:
            current = self.text.index(tk.INSERT)
        except tk.TclError:
            return
        for tag in self.text.tag_names(current):
            if not tag.startswith(constants.LINK): continue
            pos = self.text.tag_prevrange(tag, current)
            if pos:
                self.text.tag_remove(tag, *pos)
        self.ignore_modified_event = True
        self.text.edit_modified(True)

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
        self.ignore_modified_event = True
        self.text.edit_modified(True)

    def remove_quote(self):
        try:
            current = self.text.index(tk.INSERT)
        except tk.TclError:
            return
        pos = self.text.tag_prevrange(constants.QUOTE, current)
        if pos:
            self.text.tag_remove(constants.QUOTE, *pos)
            self.ignore_modified_event = True
            self.text.edit_modified(True)

    def add_footnote(self):
        try:
            first = str(self.text.index(tk.SEL_FIRST))
            last = self.text.index(tk.SEL_LAST)
        except tk.TclError:
            return
        # XXX Get new footnote tag, add to lookup.
        self.text.tag_add(constants.FOOTNOTE_DEF, first, last)
        self.text.insert(first, "[footnote]", (constants.FOOTNOTE_REF, ))

    def remove_footnote(self):
        # XXX Include the footnote text into the text proper,
        # XXX and set selection to the footnote text.
        pass

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
        self.text.tag_configure(tag, elide=not int(self.text.tag_cget(tag, "elide")))

    def rename(self):
        self.main.rename_text(parent=self.toplevel, oldpath=self.filepath)

    def copy(self, event=None, parent=None):
        dirpath, filename = os.path.split(self.filepath)
        initialdir = os.path.join(self.main.absdirpath, dirpath)
        name = tk_simpledialog.askstring(
            parent=parent or self.toplevel,
            title="Copy name",
            prompt="Give the name for the copy:",
            initialvalue=f"Copy of {os.path.splitext(filename)[0]}")
        if not name:
            return
        name = os.path.splitext(name)[0]
        filepath = os.path.join(dirpath, name + ".md")
        absfilepath = os.path.normpath(os.path.join(self.main.absdirpath, filepath))
        if not absfilepath.startswith(self.main.absdirpath):
            tk_messagebox.showerror(
                parent=parent or self.toplevel,
                title="Wrong directory",
                message=f"Must be within {self.main.absdirpath}")
            return
        with open(absfilepath, "w") as outfile:
            self.outfiles_stack = [outfile]
            self.write_outfile()
            self.outfiles_stack = []
        self.main.add_treeview_entry(filepath)
        self.main.open_text(filepath=filepath)

    def save(self, event=None):
        if not self.is_modified:
            return
        self.main.move_file_to_archive(self.filepath)
        with open(os.path.join(self.main.absdirpath, self.filepath), "w") as outfile:
            self.outfiles_stack = [outfile]
            self.write_outfile()
            self.outfiles_stack = []
        self.menubar.configure(background=self.original_menubar_background)
        self.info_update()
        self.main.flag_treeview_entry(self.filepath, modified=False)
        self.ignore_modified_event = True
        self.text.edit_modified(False)

    @property
    def outfile(self):
        return self.outfiles_stack[-1]

    def write_outfile(self):
        self.current_link_tag = None
        self.write_line_indents = []
        self.write_line_indented = False
        self.footnotes_tmp = dict()
        self.current_footnote = None
        self.do_not_save_text = False
        for item in self.text.dump("1.0", tk.END):
            try:
                method = getattr(self, f"save_{item[0]}")
            except AttributeError:
                ic("Could not handle item", item)
            else:
                method(item)
        self.write_line_indents = ["  "]
        for old_label, footnote in sorted(self.footnotes_tmp.items()):
            self.outfile.write(f"\n[^{footnote['newlabel']}]: ")
            self.write_line_indented = True
            self.write_characters(footnote["outfile"].getvalue().lstrip("\n") or
                                  "*To be defined.*")

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

    def save_text(self, item):
        if self.do_not_save_text:
            return
        self.write_characters(item[1])

    def save_tagon(self, item):
        tag = item[1]
        try:
            method = getattr(self, f"save_tagon_{tag}")
        except AttributeError:
            # This relies on the order of tags added in 'parse_footnote_def'.
            if tag.startswith(constants.FOOTNOTE_REF_PREFIX):
                self.current_footnote = tag[len(constants.FOOTNOTE_REF_PREFIX):]
            elif tag.startswith(constants.FOOTNOTE_DEF_PREFIX):
                self.current_footnote = tag[len(constants.FOOTNOTE_DEF_PREFIX):]
        else:
            method(item)

    def save_tagoff(self, item):
        try:
            method = getattr(self, f"save_tagoff_{item[1]}")
        except AttributeError:
            pass
        else:
            method(item)

    def save_tagon_italic(self, item):
        self.write_characters("*")

    def save_tagoff_italic(self, item):
        self.write_characters("*")

    def save_tagon_bold(self, item):
        self.write_characters("**")

    def save_tagoff_bold(self, item):
        self.write_characters("**")

    def save_tagon_link(self, item):
        for tag in self.text.tag_names(item[2]):
            if tag.startswith(constants.LINK_PREFIX):
                self.current_link_tag = tag
                self.write_characters("[")
                return

    def save_tagoff_link(self, item):
        link = self.links.get(self.current_link_tag)
        if link["title"]:
            self.write_characters(f"""]({link['url']} "{link['title']}")""")
        else:
            self.write_characters(f"]({link['url']})")
        self.current_link_tag = None

    def save_tagon_quote(self, item):
        self.write_line_indents.append("> ")

    def save_tagoff_quote(self, item):
        self.write_line_indents.pop()

    def save_tagon_footnote_ref(self, item):
        try:
            footnote = self.footnotes_tmp[self.current_footnote]
        except KeyError:
            newlabel = str(len(self.footnotes_tmp) + 1)
            footnote = dict(current_label=self.current_footnote, newlabel=newlabel)
            self.footnotes_tmp[self.current_footnote] = footnote
        self.write_characters(f"[^{newlabel}]")
        self.do_not_save_text = True

    def save_tagoff_footnote_ref(self, item):
        self.current_footnote = None
        self.do_not_save_text = False

    def save_tagon_footnote_def(self, item):
        footnote = self.footnotes_tmp[self.current_footnote]
        footnote["outfile"] = io.StringIO()
        self.outfiles_stack.append(footnote["outfile"])

    def save_tagoff_footnote_def(self, item):
        self.current_footnote = None
        self.outfiles_stack.pop()

    def save_mark(self, item):
        pass

    def delete(self):
        if not tk_messagebox.askokcancel(
                parent=self.toplevel,
                title="Delete text?",
                message=f"Really delete text '{self.filepath}'?"):
            return
        self.close(force=True)
        self.main.delete_text(self.filepath, force=True)

    def delete_text(self, filepath):
        self.main.treeview.delete(self.filepath)

    def close(self, event=None, force=False):
        if self.is_modified and not force:
            if not tk_messagebox.askokcancel(
                    parent=self.toplevel,
                    title="Close?",
                    message="Modifications will not be saved. Really close?"):
                return
        self.main.flag_treeview_entry(self.filepath, modified=False)
        self.main.texts[self.filepath].pop("editor")
        self.toplevel.destroy()
