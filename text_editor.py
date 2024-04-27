"Text editor window class."

from icecream import ic

import io
import os.path
import string
import webbrowser

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox as tk_messagebox
from tkinter import simpledialog as tk_simpledialog

import yaml

import constants
import utils
from base_text import TextMixin, BaseTextContainer


class TextEditor(TextMixin, BaseTextContainer):
    "Text editor window."

    def __init__(self, main, filepath):
        super().__init__(main, filepath)

        self.toplevel = tk.Toplevel(self.main.root)
        self.toplevel.title(os.path.splitext(self.filepath)[0])
        self.toplevel.bind("<Control-s>", self.save)
        self.toplevel.bind("<Control-q>", self.close)
        self.toplevel.protocol("WM_DELETE_WINDOW", self.close)
        geometry = self.frontmatter.get("geometry")
        if geometry:
            self.toplevel.geometry(geometry)

        self.menubar_setup()

        self.text_setup(self.toplevel)
        self.text_configure_tags()
        self.text_configure_tag_bindings()
        self.text_bind_keys()

        self.set_status(self.frontmatter.get("status"))
        # NOTE: Do not call 'render_title'.
        self.render(self.ast)

        self.info_setup()
        self.chars_var.set(f"{self.character_count} characters")

        self.ignore_modified_event = True
        self.text.edit_modified(False)

    def menubar_setup(self):
        self.menubar = tk.Menu(self.toplevel, background="gold")
        self.toplevel["menu"] = self.menubar
        self.menubar.add_command(label="Au",
                                 font=constants.FONT_LARGE_BOLD,
                                 background="gold",
                                 command=self.main.root.lift)

        self.menu_file = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_file, label="File")
        self.menu_file.add_command(label="Rename", command=self.rename)
        self.menu_file.add_command(label="Copy", command=self.copy)
        self.menu_file.add_command(label="Delete", command=self.delete)
        self.menu_file.add_command(label="Save",
                                   command=self.save,
                                   accelerator="Ctrl-S")
        self.menu_file.add_command(label="Close",
                                   command=self.close,
                                   accelerator="Ctrl-Q")

        self.menu_edit = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_edit, label="Edit")
        self.menu_edit.add_command(label="Copy", command=self.buffer_copy)
        self.menu_edit.add_command(label="Cut", command=self.buffer_cut)
        self.menu_edit.add_command(label="Paste", command=self.buffer_paste)

        self.menu_bold = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_bold, label="Bold")
        self.menu_bold.add_command(label="Add", command=self.bold_add)
        self.menu_bold.add_command(label="Remove", command=self.bold_remove)

        self.menu_italic = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_italic, label="Italic")
        self.menu_italic.add_command(label="Add", command=self.italic_add)
        self.menu_italic.add_command(label="Remove", command=self.italic_remove)

        self.menu_quote = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_quote, label="Quote")
        self.menu_quote.add_command(label="Add", command=self.quote_add)
        self.menu_quote.add_command(label="Remove", command=self.quote_remove)

        self.menu_status = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_status, label="Status")
        self.status_var = tk.StringVar() # Also referred to by 'info_setup'.
        for status in constants.STATUSES:
            self.menu_status.add_radiobutton(label=status,
                                             variable=self.status_var,
                                             command=self.set_status)
        self.menu_link = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_link, label="Link")
        self.menu_link.add_command(label="Add", command=self.link_add)
        self.menu_link.add_command(label="Remove", command=self.link_remove)

        self.menu_footnote = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_footnote, label="Footnote")
        self.menu_footnote.add_command(label="Add", command=self.footnote_add)
        self.menu_footnote.add_command(label="Remove", command=self.footnote_remove)

        self.menu_indexed = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_indexed, label="Indexed")
        self.menu_indexed.add_command(label="Add", command=self.indexed_add)
        self.menu_indexed.add_command(label="Remove", command=self.indexed_remove)

        self.menu_reference = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_reference, label="Reference")
        self.menu_reference.add_command(label="Add", command=self.reference_add)
        self.menu_reference.add_command(label="Remove", command=self.reference_remove)

    def text_bind_keys(self, text=None):
        super().text_bind_keys(text=text)
        self.text.bind("<<Modified>>", self.handle_modified)
        self.text.bind("<Button-3>", self.popup_menu)

    def info_setup(self):
        self.info_frame = ttk.Frame(self.frame, padding=2)
        self.info_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        self.frame.rowconfigure(1, minsize=22)

        self.chars_var = tk.StringVar()
        chars_label = ttk.Label(self.info_frame)
        chars_label.grid(row=0, column=0, padx=4, sticky=tk.W)
        self.info_frame.columnconfigure(0, weight=1)
        chars_label["textvariable"] = self.chars_var

        status_label = ttk.Label(self.info_frame)
        status_label.grid(row=0, column=1, padx=4, sticky=tk.E)
        status_label["textvariable"] = self.status_var # Defined above in 'menu_status'.
        self.info_frame.columnconfigure(1, weight=1)

    @property
    def character_count(self):
        return len(self.text.get("1.0", tk.END))

    def cursor_offset(self, sign=None):
        "Return the offset to convert the cursor position to the one to use."
        return ""

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
        self.chars_var.set(f"{self.character_count} characters")

    def popup_menu(self, event):
        menu = tk.Menu(self.text)
        any_item = False
        try:
            first, last = self.get_selection(check_no_boundary=False)
        except ValueError:
            if self.main.paste_buffer:
                menu.add_command(label="Paste", command=self.buffer_paste)
                any_item = True
            tags = self.text.tag_names(tk.CURRENT)
            if constants.LINK in tags:
                menu.add_command(label="Remove link", command=self.link_remove)
                any_item = True
            if constants.BOLD in tags:
                menu.add_command(label="Remove bold", command=self.bold_remove)
                any_item = True
            if constants.ITALIC in tags:
                menu.add_command(label="Remove italic", command=self.italic_remove)
                any_item = True
            if constants.QUOTE in tags:
                menu.add_command(label="Remove quote", command=self.quote_remove)
                any_item = True
        else:
            if not self.selection_contains_boundary(first, last, show=False):
                menu.add_command(label="Link", command=self.link_add)
                menu.add_command(label="Bold", command=self.bold_add)
                menu.add_command(label="Italic", command=self.italic_add)
                menu.add_command(label="Quote", command=self.quote_add)
                menu.add_separator()
                menu.add_command(label="Copy", command=self.buffer_copy)
                menu.add_command(label="Cut", command=self.buffer_cut)
                any_item = True
        if any_item:
            menu.tk_popup(event.x_root, event.y_root)

    @property
    def is_modified(self):
        return self.text.edit_modified()

    def handle_modified(self, event=None):
        if self.ignore_modified_event:
            self.ignore_modified_event = False
        if not self.is_modified:
            return
        self.original_menubar_background = self.menubar.cget("background")
        self.menubar.configure(background=constants.MODIFIED_COLOR)
        self.main.set_treeview_info(self.filepath)

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

    def bold_add(self):
        try:
            first, last = self.get_selection(adjust=True)
        except ValueError:
            return
        self.text.tag_add(constants.BOLD, first, last)
        self.ignore_modified_event = True
        self.text.edit_modified(True)

    def bold_remove(self):
        current = self.text.index(tk.INSERT)
        if constants.BOLD in self.text.tag_names(current):
            region = self.text.tag_prevrange(constants.BOLD, current)
            if region:
                self.text.tag_remove(constants.BOLD, *region)
                self.ignore_modified_event = True
                self.text.edit_modified(True)

    def italic_add(self):
        try:
            first, last = self.get_selection(adjust=True)
        except ValueError:
            return
        self.text.tag_add(constants.ITALIC, first, last)
        self.ignore_modified_event = True
        self.text.edit_modified(True)

    def italic_remove(self):
        current = self.text.index(tk.INSERT)
        if constants.ITALIC in self.text.tag_names(current):
            region = self.text.tag_prevrange(constants.ITALIC, current)
            if region:
                self.text.tag_remove(constants.ITALIC, *region)
                self.ignore_modified_event = True
                self.text.edit_modified(True)

    def quote_add(self):
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

    def quote_remove(self):
        current = self.text.index(tk.INSERT)
        if constants.QUOTE in self.text.tag_names(current):
            region = self.text.tag_prevrange(constants.QUOTE, current)
            if region:
                self.text.tag_remove(constants.QUOTE, *region)
                self.ignore_modified_event = True
                self.text.edit_modified(True)

    def link_action(self, event):
        "Allow viewing, editing and opening the link."
        link = self.get_link()
        if not link:
            return
        edit = LinkEdit(self.text, link)
        if edit.result:
            if edit.result["url"]:
                link["url"] = edit.result["url"]
                link["title"] = edit.result["title"]
            else:
                region = self.text.tag_nextrange(link["tag"], "1.0")
                self.text.tag_remove(constants.LINK, *region)
                self.text.tag_delete(link["tag"])
                # Do not remove entry from 'links': the count must be preserved.
            self.ignore_modified_event = True
            self.text.edit_modified(True)

    def link_add(self):
        try:
            first, last = self.get_selection()
        except ValueError:
            return
        url = tk_simpledialog.askstring(
            parent=self.text,
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
        self.link_create(url, title, first, last)
        self.text.tag_remove(tk.SEL, first, last)
        self.ignore_modified_event = True
        self.text.edit_modified(True)

    def link_remove(self):
        link = self.get_link()
        if not link:
            return
        if not tk_messagebox.askokcancel(
                parent=self.text,
                title="Remove link?",
                message=f"Really remove link?"):
            return
        first, last = self.text.tag_nextrange(link["tag"], "1.0")
        self.text.tag_delete(link["tag"])
        self.text.tag_remove(constants.LINK, first, last)
        self.ignore_modified_event = True
        self.text.edit_modified(True)
        # Links are not removed from 'links' during a session.
        # The link count must remain strictly increasing.

    def reference_add(self):
        raise NotImplementedError

    def reference_remove(self):
        raise NotImplementedError

    def indexed_add(self):
        raise NotImplementedError

    def indexed_remove(self):
        raise NotImplementedError

    def footnote_add(self):
        try:
            first, last = self.get_selection()
        except ValueError:
            return
        label = self.get_new_footnote_label()
        tag = constants.FOOTNOTE_DEF_PREFIX + label
        self.text.tag_configure(tag, elide=True)
        self.text.tag_add(constants.FOOTNOTE_DEF, first, last)
        self.text.tag_add(tag, first, last)
        self.text.insert(self.text.tag_nextrange(tag, "1.0")[0], "\n", (tag, ))
        tag = constants.FOOTNOTE_REF_PREFIX + label
        self.footnotes[label] = dict(label=label, tag=tag)
        self.text.insert(first, f"^{label}", (constants.FOOTNOTE_REF, (tag, )))
        self.text.tag_bind(tag, "<Button-1>", self.footnote_toggle)

    def get_new_footnote_label(self):
        try:
            return str(max([int(label) for label in self.footnotes]) + 1)
        except ValueError:
            return "1"

    def footnote_remove(self):
        current = self.text.index(tk.INSERT)
        tags = self.text.tag_names(current)
        if constants.FOOTNOTE_REF in tags or constants.FOOTNOTE_DEF in tags:
            for tag in tags:
                if tag.startswith(constants.FOOTNOTE_REF_PREFIX):
                    label = tag[len(constants.FOOTNOTE_REF_PREFIX):]
                    break
                elif tag.startswith(constants.FOOTNOTE_DEF_PREFIX):
                    label = tag[len(constants.FOOTNOTE_DEF_PREFIX):]
                    break
            else:
                return
        tag = constants.FOOTNOTE_REF_PREFIX + label
        region = self.text.tag_nextrange(tag, "1.0")
        self.text.tag_remove(constants.FOOTNOTE_REF, *region)
        self.text.tag_delete(tag)
        self.text.delete(*region)
        tag = constants.FOOTNOTE_DEF_PREFIX + label
        region = self.text.tag_nextrange(tag, "1.0")
        self.text.tag_remove(constants.FOOTNOTE_DEF, *region)
        self.text.tag_delete(tag)
        self.text.tag_add(tk.SEL, *region)

    def buffer_copy(self):
        "Copy the current selection into the paste buffer."
        try:
            first, last = self.get_selection()
        except ValueError:
            return
        self.main.paste_buffer = self.dump_clean(first, last)

    def buffer_cut(self):
        "Cut the current selection into the paste buffer."
        try:
            first, last = self.get_selection()
        except ValueError:
            return
        self.main.paste_buffer = self.dump_clean(first, last)
        self.text.delete(first, last)

    def buffer_paste(self):
        "Paste in contents from the paste buffer."
        first = self.text.index(tk.INSERT)
        self.undump(self.main.paste_buffer)
        self.text.tag_remove(tk.SEL, first, tk.INSERT)

    def dump_clean(self, first, last):
        "Get the dump of the contents, cleanup and preprocess."
        # Get rid of irrelevant marks.
        dump = [e for e in self.text.dump(first, last)
                if not (e[0] == "mark" and (e[1] in (tk.INSERT, tk.CURRENT) or
                                            e[1].startswith("tk::")))]
        # Get rid of tag SEL.
        dump = [e for e in dump if not (e[0] == "tagon" and e[1] == tk.SEL)]
        # Get link data to make a copy. Loose the position.
        result = []
        for kind, value, pos in dump:
            if kind == "tagoff" and value.startswith(constants.LINK_PREFIX):
                link = self.get_link(value)
                result.append((kind, value, link["url"], link["title"]))
            else:
                result.append((kind, value))
        return result

    def undump(self, dump):
        tags = dict()
        self.skip_text = False
        for entry in dump:
            try:
                method = getattr(self, f"undump_{entry[0]}")
            except AttributeError:
                ic("Could not undump", entry)
            else:
                method(entry, tags)

    def undump_text(self, entry, tags):
        if self.skip_text:
            return
        self.text.insert(tk.INSERT, entry[1])

    def undump_tagon(self, entry, tags):
        if entry[1].startswith(constants.FOOTNOTE_REF_PREFIX):
            label = self.get_new_footnote_label()
            tags[entry[1]] = dict(label=label,
                                  first=self.text.index(tk.INSERT))
            self.skip_text = True
        elif entry[1].startswith(constants.FOOTNOTE_DEF_PREFIX):
            ref_tag = constants.FOOTNOTE_REF_PREFIX + entry[1][len(constants.FOOTNOTE_DEF_PREFIX):]
            tags[entry[1]] = dict(label=tags[ref_tag]["label"],
                                  first=self.text.index(tk.INSERT))
        else:
            tags[entry[1]] = dict(first=self.text.index(tk.INSERT))

    def undump_tagoff(self, entry, tags):
        try:
            data = tags[entry[1]]
        except KeyError:
            ic("No tagon for", entry)
        else:
            if entry[1].startswith(constants.LINK_PREFIX):
                self.link_create(entry[2],
                                 entry[3],
                                 data["first"], 
                                 self.text.index(tk.INSERT))
            elif entry[1].startswith(constants.FOOTNOTE_REF_PREFIX):
                label = data["label"]
                tag = constants.FOOTNOTE_REF_PREFIX + label
                self.text.insert(tk.INSERT, f"^{label}", (constants.FOOTNOTE_REF, tag))
                self.text.tag_bind(tag, "<Button-1>", self.footnote_toggle)
                self.skip_text = False
                self.footnotes[label] = dict(label=label, tag=tag)
            elif entry[1].startswith(constants.FOOTNOTE_DEF_PREFIX):
                tag = constants.FOOTNOTE_DEF_PREFIX + data["label"]
                self.text.tag_configure(tag, elide=True)
                self.text.tag_add(tag, data["first"], tk.INSERT)
            else:
                self.text.tag_add(entry[1], data["first"], self.text.index(tk.INSERT))

    def undump_mark(self, entry, tags):
        self.text.mark_set(entry[1], tk.INSERT)

    def rename(self):
        "Rename the text file."
        self.main.rename_text(parent=self.toplevel, oldpath=self.filepath)
        self.main.refresh_treeview_info()

    def copy(self, event=None, parent=None):
        "Make a copy of the current contents."
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
        self.main.refresh_treeview_info()

    def save(self, event=None):
        """Save the current contents to the text file.
        Get the main window to refresh the contents of the text view.
        """
        if not self.is_modified:
            return
        self.main.move_file_to_archive(self.filepath)
        self.save_file(self.absfilepath)
        self.menubar.configure(background=self.original_menubar_background)
        self.ignore_modified_event = True
        self.text.edit_modified(False)
        self.main.text_rerender(self.filepath, cursor=self.cursor_normalized())
        self.main.set_treeview_info(self.filepath)

    def delete(self):
        "Delete the text file and this window."
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
        self.main.set_treeview_info(self.filepath)
        self.main.texts[self.filepath].pop("editor")
        self.toplevel.destroy()

    def save_file(self, filepath):
        """Save the contents of the window as Markdown file.
        Also used for making a copy of the file.
        """
        with open(filepath, "w") as outfile:
            self.set_outfile(outfile)
            self.outfile.write("---\n")
            self.frontmatter["status"] = repr(self.status)
            self.outfile.write(yaml.dump(self.frontmatter))
            self.outfile.write("---\n")
            self.markdown()
            self.set_outfile()

    @property
    def outfile(self):
        return self.outfile_stack[-1]

    def set_outfile(self, outfile=None):
        if outfile is None:
            self.outfile_stack = []
        else:
            self.outfile_stack = [outfile]

    def markdown(self):
        self.current_link_tag = None
        self.line_indents = []
        self.line_indented = False
        self.skip_text = False
        # Only used from this method.
        self.referred_footnotes = dict()
        # This does not need the cleaned dump.
        for item in self.text.dump("1.0", tk.END):
            try:
                method = getattr(self, f"markdown_{item[0]}")
            except AttributeError:
                ic("Could not markdown item", item)
            else:
                method(item)
        footnotes = list(self.referred_footnotes.values())
        footnotes.sort(key=lambda f: int(f["new_label"]))
        for footnote in footnotes:
            self.outfile.write("\n")
            self.outfile.write(f"[^{footnote['new_label']}]: ")
            lines = footnote["outfile"].getvalue().split("\n")
            self.outfile.write(lines[0])
            self.outfile.write("\n")
            for line in lines[1:]:
                self.outfile.write("  ")
                self.outfile.write(line)
                self.outfile.write("\n")
        del self.referred_footnotes

    def output_line_indent(self, force=False):
        if self.line_indented and not force:
            return
        self.outfile.write("".join(self.line_indents))
        self.line_indented = True

    def output_characters(self, characters):
        if not characters:
            return
        segments = characters.split("\n")
        if len(segments) == 1:
            self.output_line_indent()
            self.outfile.write(segments[0])
        else:
            for segment in segments[:-1]:
                self.output_line_indent()
                self.outfile.write(segment)
                self.outfile.write("\n")
                self.line_indented = False
            if segments[-1]:
                self.output_line_indent()
                self.outfile.write(segments[-1])
                self.outfile.write("\n")
                self.line_indented = False

    def markdown_text(self, item):
        if self.skip_text:
            return
        self.output_characters(item[1])

    def markdown_mark(self, item):
        pass

    def markdown_tagon(self, item):
        tag = item[1]
        try:
            method = getattr(self, f"markdown_tagon_{tag}")
        except AttributeError:
            pass
        else:
            method(item)

    def markdown_tagoff(self, item):
        try:
            method = getattr(self, f"markdown_tagoff_{item[1]}")
        except AttributeError:
            pass
        else:
            method(item)

    def markdown_tagon_italic(self, item):
        self.output_characters("*")

    def markdown_tagoff_italic(self, item):
        self.output_characters("*")

    def markdown_tagon_bold(self, item):
        self.output_characters("**")

    def markdown_tagoff_bold(self, item):
        self.output_characters("**")

    def markdown_tagon_link(self, item):
        for tag in self.text.tag_names(item[2]):
            if tag.startswith(constants.LINK_PREFIX):
                self.current_link_tag = tag
                self.output_characters("[")
                return

    def markdown_tagoff_link(self, item):
        link = self.get_link(self.current_link_tag)
        if link["title"]:
            self.output_characters(f"""]({link['url']} "{link['title']}")""")
        else:
            self.output_characters(f"]({link['url']})")
        self.current_link_tag = None

    def markdown_tagon_quote(self, item):
        self.line_indents.append("> ")

    def markdown_tagoff_quote(self, item):
        self.line_indents.pop()

    def markdown_tagon_thematic_break(self, item):
        self.output_skip_text = True

    def markdown_tagoff_thematic_break(self, item):
        self.output_characters("---")
        self.output_line_indent(force=True)
        self.outfile.write("\n")
        self.skip_text = False

    def markdown_tagon_footnote_ref(self, item):
        for tag in self.text.tag_names(item[2]):
            if tag.startswith(constants.FOOTNOTE_REF_PREFIX):
                old_label = tag[len(constants.FOOTNOTE_REF_PREFIX):]
                footnote = self.footnotes[old_label]
                new_label = str(len(self.referred_footnotes) + 1)
                footnote["new_label"] = new_label
                self.referred_footnotes[old_label] = footnote
                break
        self.output_characters(f"[^{new_label}]")
        self.skip_text = True

    def markdown_tagoff_footnote_ref(self, item):
        pass

    def markdown_tagon_footnote_def(self, item):
        for tag in self.text.tag_names(item[2]):
            if tag.startswith(constants.FOOTNOTE_DEF_PREFIX):
                old_label = tag[len(constants.FOOTNOTE_DEF_PREFIX):]
        footnote = self.referred_footnotes[old_label]
        footnote["outfile"] = io.StringIO()
        self.outfile_stack.append(footnote["outfile"])
        self.skip_text = False

    def markdown_tagoff_footnote_def(self, item):
        self.outfile_stack.pop()

    def markdown_tagon_indexed(self, item):
        self.output_characters("[#")

    def markdown_tagoff_indexed(self, item):
        self.output_characters("]")

    def markdown_tagon_reference(self, item):
        self.output_characters("[@")

    def markdown_tagoff_reference(self, item):
        self.output_characters("]")


class LinkEdit(tk_simpledialog.Dialog):
    "Simple dialog window for editing the URL and title for a link."

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
