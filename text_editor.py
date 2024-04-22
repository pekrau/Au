"Text editor window."

from icecream import ic

import io
import json
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
        self.menu_edit.add_command(label="Copy", command=self.copy_buffer)
        self.menu_edit.add_command(label="Cut", command=self.cut_buffer)
        self.menu_edit.add_command(label="Paste", command=self.paste_buffer)
        self.menu_edit.add_separator()
        self.menu_edit.add_command(label="Add link", command=self.add_link)
        self.menu_edit.add_command(label="Remove link", command=self.remove_link)
        self.menu_edit.add_separator()
        self.menu_edit.add_command(label="Add indexed", command=self.add_indexed)
        self.menu_edit.add_command(label="Remove indexed", command=self.remove_indexed)
        self.menu_edit.add_separator()
        self.menu_edit.add_command(label="Add reference", command=self.add_reference)
        self.menu_edit.add_command(label="Remove reference",
                                   command=self.remove_reference)

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
        self.status_var = tk.StringVar()
        for status in constants.STATUSES:
            self.menu_status.add_radiobutton(label=status,
                                             variable=self.status_var,
                                             command=self.set_status)

        self.setup_text()

        self.text.tag_configure(constants.FOOTNOTE_REF,
                                foreground=constants.FOOTNOTE_REF_COLOR)
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

        status_label = ttk.Label(self.info_frame)
        status_label.grid(row=0, column=1, padx=4, sticky=tk.E)
        status_label["textvariable"] = self.status_var # Defined above for menu.
        self.info_frame.columnconfigure(1, weight=1)

        self.set_status(self.frontmatter.get("status"))

        # The footnotes lookup is local for each TextEditor instance.
        self.footnotes = dict()
        # Used only while parsing.
        self.parsed_footnotes = dict()

        self.parse(self.ast)

        self.move_cursor(self.frontmatter.get("cursor"))
        self.info_update()

        self.ignore_modified_event = True
        self.text.edit_modified(False)

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
        # Insert the standard text '[footnote]' as the visible footnote reference.
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

    def parse_indexed(self, ast):
        self.text.insert(tk.INSERT, ast["target"], constants.INDEXED)

    def parse_reference(self, ast):
        self.text.insert(tk.INSERT, f"{{{ast['target']}}}", constants.REFERENCE)

    def info_update(self):
        self.size_var.set(f"{self.character_count} characters")
        self.main.update_treeview_entry(self.filepath,
                                        status=str(self.status),
                                        size=f"{self.character_count} ch",
                                        age=self.age)

    @property
    def timestamp(self):
        return utils.get_timestamp(self.absfilepath)

    @property
    def age(self):
        return utils.get_age(self.absfilepath)

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

    def save(self, event=None):
        "Save the text file."
        if not self.is_modified:
            return
        self.frontmatter["status"] = repr(self.status)
        self.frontmatter["geometry"] = self.toplevel.geometry()
        self.frontmatter["cursor"] = self.text.index(tk.INSERT)
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

    def add_indexed(self):
        raise NotImplementedError

    def remove_indexed(self):
        raise NotImplementedError

    def add_reference(self):
        raise NotImplementedError

    def remove_reference(self):
        raise NotImplementedError

    def add_footnote(self):
        try:
            first, last = self.get_selection()
        except ValueError:
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
        last = f"{first} +{len(constants.FOOTNOTE)}c"
        self.text.tag_add(constants.FOOTNOTE_REF, first, last)
        self.text.tag_add(ref_tag, first, last)
        self.text.tag_bind(ref_tag, "<Button-1>", self.footnote_toggle)

    def remove_footnote(self):
        current = self.text.index(tk.INSERT)
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
        self.text.configure(cursor="double_arrow")

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
        self.flag_do_not_write_text = False
        self.flag_remove_leading_character = None
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
        if self.flag_do_not_write_text:
            return
        if self.flag_remove_leading_character:
            text = item[1].lstrip(self.flag_remove_leading_character)
            self.flag_remove_leading_character = None            
        else:
            text = item[1]
        self.write_characters(text)

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
        self.flag_do_not_write_text = True

    def write_tagoff_footnote_ref(self, item):
        self.current_footnote = None
        self.flag_do_not_write_text = False

    def write_tagon_footnote_def(self, item):
        footnote = self.referred_footnotes[self.current_footnote]
        footnote["outfile"] = io.StringIO()
        self.outfiles_stack.append(footnote["outfile"])

    def write_tagoff_footnote_def(self, item):
        self.current_footnote = None
        outfile = self.outfiles_stack.pop()

    def write_tagon_indexed(self, item):
        self.write_characters("[#")

    def write_tagoff_indexed(self, item):
        self.write_characters("]")

    def write_tagon_reference(self, item):
        pass

    def write_tagoff_reference(self, item):
        pass

    def write_mark(self, item):
        pass
