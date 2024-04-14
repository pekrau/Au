"Text editor window."

from icecream import ic

import collections
import json
import os

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
        self.menu_edit.add_command(label="Link", command=self.set_link)
        self.menu_edit.add_command(label="Bold", command=self.set_bold)
        self.menu_edit.add_command(label="Italic", command=self.set_italic)
        self.menu_edit.add_command(label="Quote", command=self.set_quote)
        self.menu_edit.add_separator()
        self.menu_edit.add_command(label="Remove link", command=self.unset_link)
        self.menu_edit.add_command(label="Remove bold", command=self.unset_bold)
        self.menu_edit.add_command(label="Remove italic", command=self.unset_italic)
        self.menu_edit.add_command(label="Remove quote", command=self.unset_quote)

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
                                background=constants.FOOTNOTE_DEF_COLOR)
        self.text.tag_bind(constants.FOOTNOTE_REF, "<Enter>", self.footnote_enter)
        self.text.tag_bind(constants.FOOTNOTE_REF, "<Leave>", self.footnote_leave)
        self.text.tag_bind(constants.FOOTNOTE_REF, "<Button-1>", self.footnote_toggle)

        self.menu_right_click = tk.Menu(self.text, tearoff=False)
        self.menu_right_click.add_command(label="Link", command=self.set_link)
        self.menu_right_click.add_command(label="Bold", command=self.set_bold)
        self.menu_right_click.add_command(label="Italic", command=self.set_italic)
        self.menu_right_click.add_command(label="Quote", command=self.set_quote)
        self.menu_right_click.add_separator()
        self.menu_right_click.add_command(label="Remove link", command=self.unset_link)
        self.menu_right_click.add_command(label="Remove bold", command=self.unset_bold)
        self.menu_right_click.add_command(label="Remove italic", command=self.unset_italic)
        self.menu_right_click.add_command(label="Remove quote", command=self.unset_quote)
        self.text.bind("<Button-3>", self.popup_menu_right_click)

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
        start = self.text.index(tk.INSERT)
        for child in ast["children"]:
            self.parse(child)
        self.text.tag_add("quote", start, self.text.index(tk.INSERT))

    def parse_footnote_ref(self, ast):
        label = ast["label"]
        tag = constants.FOOTNOTE_PREFIX + label
        self.footnotes[label] = dict(label=label, tag=tag)
        start = self.text.index(tk.INSERT)
        self.text.insert(tk.INSERT, f"[{label}]")
        self.text.tag_add(constants.FOOTNOTE_REF, start, self.text.index(tk.INSERT))
        self.text.tag_add(tag, start, self.text.index(tk.INSERT))
        self.footnotes[label]["first"] = self.text.index(tk.INSERT)

    def parse_footnote_def(self, ast):
        label = ast["label"]
        footnote = self.footnotes[label]
        tag = constants.FOOTNOTE_DEF_PREFIX + label
        self.text.tag_configure(tag, elide=True)
        self.text.mark_set(tk.INSERT, footnote["first"])
        for child in ast["children"]:
            self.parse(child)
        self.text.tag_add(constants.FOOTNOTE_DEF, footnote["first"], tk.INSERT)
        self.text.tag_add(tag, footnote["first"], tk.INSERT)
        footnote["last"] = self.text.index(tk.INSERT)

    def info_update(self, size_only=False):
        self.size_var.set(f"{self.character_count} characters")
        self.main.treeview.set(self.filepath, "characters", str(self.character_count))
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

    def set_link(self):
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

    def unset_link(self):
        try:
            current = self.text.index(tk.CURRENT)
        except tk.TclError:
            return
        for tag in self.text.tag_names(current):
            if not tag.startswith(constants.LINK): continue
            pos = self.text.tag_prevrange(tag, current)
            if pos:
                self.text.tag_remove(tag, *pos)
        self.ignore_modified_event = True
        self.text.edit_modified(True)

    def set_bold(self):
        try:
            first = self.text.index(tk.SEL_FIRST)
            last = self.text.index(tk.SEL_LAST)
        except tk.TclError:
            return
        self.text.tag_add(constants.BOLD, first, last)
        self.ignore_modified_event = True
        self.text.edit_modified(True)

    def unset_bold(self):
        try:
            current = self.text.index(tk.CURRENT)
        except tk.TclError:
            return
        pos = self.text.tag_prevrange(constants.BOLD, current)
        if pos:
            self.text.tag_remove(constants.BOLD, *pos)
        self.ignore_modified_event = True
        self.text.edit_modified(True)

    def set_italic(self):
        try:
            first = self.text.index(tk.SEL_FIRST)
            last = self.text.index(tk.SEL_LAST)
        except tk.TclError:
            return
        self.text.tag_add(constants.ITALIC, first, last)
        self.ignore_modified_event = True
        self.text.edit_modified(True)

    def unset_italic(self):
        try:
            current = self.text.index(tk.CURRENT)
        except tk.TclError:
            return
        pos = self.text.tag_prevrange(constants.ITALIC, current)
        if pos:
            self.text.tag_remove(constants.ITALIC, *pos)
        self.ignore_modified_event = True
        self.text.edit_modified(True)

    def set_quote(self):
        try:
            first = self.text.index(tk.SEL_FIRST)
            last = self.text.index(tk.SEL_LAST)
        except tk.TclError:
            return
        self.text.tag_add("quote", first, last)
        self.ignore_modified_event = True
        self.text.edit_modified(True)

    def unset_quote(self):
        try:
            current = self.text.index(tk.CURRENT)
        except tk.TclError:
            return
        pos = self.text.tag_prevrange("quote", current)
        if pos:
            self.text.tag_remove(constants.QUOTE, *pos)
        self.ignore_modified_event = True
        self.text.edit_modified(True)

    def footnote_enter(self, event=None):
        self.text.configure(cursor="dot")

    def footnote_leave(self, event=None):
        self.text.configure(cursor="")

    def footnote_toggle(self, event=None, tags=None):
        if tags is None:
            tags = self.text.tag_names(tk.CURRENT)
        for tag in tags:
            if tag.startswith(constants.FOOTNOTE_PREFIX):
                label = tag[len(constants.FOOTNOTE_PREFIX):]
                break
        else:
            return
        tag = constants.FOOTNOTE_DEF_PREFIX + label
        # ic(self.text.tag_ranges(tag))
        # ic(self.text.dump(*self.text.tag_ranges(tag)))
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
        self.write_file(absfilepath)
        self.main.add_treeview_entry(filepath)
        self.main.open_text(filepath=filepath)

    def save(self, event=None):
        if not self.is_modified:
            return
        self.main.move_file_to_archive(self.filepath)
        self.write_file(os.path.join(self.main.absdirpath, self.filepath))
        self.menubar.configure(background=self.original_menubar_background)
        self.info_update()
        self.main.flag_treeview_entry(self.filepath, modified=False)
        self.ignore_modified_event = True
        self.text.edit_modified(False)

    def write_file(self, filepath):
        self.current_link_tag = None
        self.line_indents = []
        with open(filepath, "w") as outfile:
            self.outfile = outfile
            for item in self.text.dump("1.0", tk.END):
                try:
                    method = getattr(self, f"save_{item[0]}")
                except AttributeError:
                    ic("Could not handle item", item)
                else:
                    method(item)
            self.outfile = None

    def write_characters(self, characters):
        if characters == "\n":
            return
        segments = characters.split("\n")
        for segment in segments:
            self.outfile.write("".join(self.line_indents))
            self.outfile.write(segment)
            if len(segments) > 1:
                self.outfile.write("\n")

    def save_text(self, item):
        self.write_characters(item[1])

    def save_tagon(self, item):
        try:
            method = getattr(self, f"save_tagon_{item[1]}")
        except AttributeError:
            pass
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
        self.line_indents.append("> ")

    def save_tagoff_quote(self, item):
        self.line_indents.pop()
        self.outfile.write("\n")

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
        self.main.texts[self.filepath].pop("editor")
        self.toplevel.destroy()
