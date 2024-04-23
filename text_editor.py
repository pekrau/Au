"Text editor window."

from icecream import ic

import os
import string

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox as tk_messagebox
from tkinter import simpledialog as tk_simpledialog

import yaml

import constants
import utils
from editor_mixin import EditorMixin


class TextEditor(EditorMixin):
    "Text editor window."

    def __init__(self, main, filepath):
        self.main = main
        self.filepath = filepath

        parsed = utils.parse(self.absfilepath)
        self.frontmatter = parsed.frontmatter
        self.ast = parsed.ast

        self.setup_toplevel(self.main.root,
                            os.path.splitext(self.filepath)[0],
                            self.frontmatter.get("geometry"))

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
        self.menu_file.add_command(label="Delete", command=self.delete)
        self.menu_file.add_command(label="Close", command=self.close,
                                   accelerator="Ctrl-Q")

        self.menu_edit = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_edit, label="Edit")
        self.menu_edit.add_command(label="Copy", command=self.buffer_copy)
        self.menu_edit.add_command(label="Cut", command=self.buffer_cut)
        self.menu_edit.add_command(label="Paste", command=self.buffer_paste)
        self.menu_edit.add_separator()
        self.menu_edit.add_command(label="Add link", command=self.link_add)
        self.menu_edit.add_command(label="Remove link", command=self.link_remove)
        self.menu_edit.add_separator()
        self.menu_edit.add_command(label="Add footnote", command=self.footnote_add)
        self.menu_edit.add_command(label="Remove footnote",

                                   command=self.footnote_remove)
        self.menu_edit.add_separator()
        self.menu_edit.add_command(label="Add indexed", command=self.indexed_add)
        self.menu_edit.add_command(label="Remove indexed", command=self.indexed_remove)
        self.menu_edit.add_separator()
        self.menu_edit.add_command(label="Add reference", command=self.reference_add)
        self.menu_edit.add_command(label="Remove reference",
                                   command=self.reference_remove)

        self.menu_format = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_format, label="Format")
        self.menu_format.add_command(label="Bold", command=self.bold_add)
        self.menu_format.add_command(label="Italic", command=self.italic_add)
        self.menu_format.add_command(label="Quote", command=self.quote_add)
        self.menu_format.add_separator()
        self.menu_format.add_command(label="Remove bold", command=self.bold_remove)
        self.menu_format.add_command(label="Remove italic", command=self.italic_remove)
        self.menu_format.add_command(label="Remove quote", command=self.quote_remove)

        self.menu_status = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_status, label="Status")
        self.status_var = tk.StringVar()
        for status in constants.STATUSES:
            self.menu_status.add_radiobutton(label=status,
                                             variable=self.status_var,
                                             command=self.set_status)

        self.setup_text()
        self.set_status(self.frontmatter.get("status"))

        self.info_frame = ttk.Frame(self.text_frame, padding=2)
        self.info_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        self.text_frame.rowconfigure(1, minsize=22)

        self.size_var = tk.StringVar()
        size_label = ttk.Label(self.info_frame)
        size_label.grid(row=0, column=0, padx=4, sticky=tk.W)
        self.info_frame.columnconfigure(0, weight=1)
        size_label["textvariable"] = self.size_var

        status_label = ttk.Label(self.info_frame)
        status_label.grid(row=0, column=1, padx=4, sticky=tk.E)
        status_label["textvariable"] = self.status_var # Defined above for menu.
        self.info_frame.columnconfigure(1, weight=1)

        self.render(self.ast)

        self.info_update()
        self.move_cursor(self.frontmatter.get("cursor"))
        self.ignore_modified_event = True
        self.text.edit_modified(False)

    @property
    def absfilepath(self):
        return os.path.join(self.main.absdirpath, self.filepath)

    @property
    def timestamp(self):
        return utils.get_timestamp(self.absfilepath)

    @property
    def age(self):
        return utils.get_age(self.absfilepath)

    def key_press(self, event):
        if event.char not in constants.AFFECTS_CHARACTER_COUNT:
            return
        pos = self.text.index(tk.INSERT)
        tags = self.text.tag_names(pos)
        # Do not allow modifying keys from encroaching on a footnote reference.
        if constants.FOOTNOTE_REF in tags:
            return "break"
        # Do not allow modifying keys from encroaching on a reference.
        if constants.REFERENCE in tags:
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

    def info_update(self):
        self.size_var.set(f"{self.character_count} characters")
        self.main.update_treeview_entry(self.filepath,
                                        status=str(self.status),
                                        size=f"{self.character_count} ch",
                                        age=self.age)

    def rename(self):
        "Rename the text file."
        self.main.rename_text(parent=self.toplevel, oldpath=self.filepath)

    def copy(self, event=None, parent=None):
        "Make a copy of the text file."
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
        absfilepath = os.path.normpath(os.path.join(self.main.absdirpath, filepath))
        if not absfilepath.startswith(self.main.absdirpath):
            tk_messagebox.showerror(
                parent=parent or self.toplevel,
                title="Wrong directory",
                message=f"Must be within {self.main.absdirpath}")
            return
        self.save_file(absfilepath)
        self.main.add_treeview_entry(filepath)
        self.main.open_text(filepath=filepath)

    def save(self, event=None):
        "Save the text file."
        if not self.is_modified:
            return
        self.frontmatter["status"] = repr(self.status)
        self.frontmatter["geometry"] = self.toplevel.geometry()
        self.frontmatter["cursor"] = self.text.index(tk.INSERT)
        self.main.move_file_to_archive(self.filepath)
        self.save_file(self.absfilepath)
        self.menubar.configure(background=self.original_menubar_background)
        self.info_update()
        self.main.update_treeview_entry(self.filepath, modified=False)
        self.ignore_modified_event = True
        self.text.edit_modified(False)

    def delete(self):
        "Delete the text file."
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

    def set_status(self, status=None):
        if status:
            self.status = constants.Status.lookup(status) or constants.STARTED
            self.status_var.set(str(self.status))
        else:
            try:
                old_status = self.status
            except AttributeError:
                old_status =  None
            self.status = constants.Status.lookup(self.status_var.get().lower()) or constants.STARTED
            self.text.edit_modified(self.status != old_status)

    def save_file(self, filepath):
        with open(filepath, "w") as outfile:
            self.set_outfile(outfile)
            self.outfile.write("---\n")
            self.outfile.write(yaml.dump(self.frontmatter))
            self.outfile.write("---\n")
            self.write()
            self.set_outfile()
