"Editor window for Markdown text file."

from icecream import ic

import functools
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
from viewer import Viewer


class Editor(Viewer):
    "Editor window for Markdown text file."

    def __init__(self, main, text):
        super().__init__(main.root, main, text)

        self.toplevel = tk.Toplevel(self.main.root)
        self.toplevel.title(text.fullname)
        self.toplevel.bind("<Control-s>", self.save)
        self.toplevel.bind("<Control-q>", self.close)
        self.toplevel.protocol("WM_DELETE_WINDOW", self.close)
        geometry = self.text.frontmatter.get("geometry")
        if geometry:
            self.toplevel.geometry(geometry)

        self.menubar_setup()
        self.view_create(self.toplevel)
        self.view_configure_tags()
        self.view_configure_tag_bindings()
        self.view_bind_keys()
        # NOTE: Do not call 'render_title'.
        self.render(self.text.ast)
        self.info_setup()
        self.view.edit_modified(False)

    def menubar_setup(self):
        self.menubar = tk.Menu(self.toplevel, background="gold")
        self.toplevel["menu"] = self.menubar
        self.menubar.add_command(label="Au",
                                 font=constants.FONT_LARGE_BOLD,
                                 background="gold",
                                 command=self.main.root.lift)

        self.menu_file = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_file, label="File")
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

        self.menu_status = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_status, label="Status")
        self.status_var = tk.StringVar() # Also referred to by 'info_setup'.
        for status in constants.STATUSES:
            self.menu_status.add_radiobutton(label=str(status),
                                             variable=self.status_var,
                                             command=self.set_status)
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

        self.menu_link = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_link, label="Link")
        self.menu_link.add_command(label="Add", command=self.link_add)
        self.menu_link.add_command(label="Remove", command=self.link_remove)

        self.menu_indexed = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_indexed, label="Indexed")
        self.menu_indexed.add_command(label="Add", command=self.indexed_add)
        self.menu_indexed.add_command(label="Remove", command=self.indexed_remove)

        self.menu_reference = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_reference, label="Reference")
        self.menu_reference.add_command(label="Add", command=self.reference_add)
        self.menu_reference.add_command(label="Remove", command=self.reference_remove)

        self.menu_footnote = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_footnote, label="Footnote")
        self.menu_footnote.add_command(label="Add", command=self.footnote_add)
        self.menu_footnote.add_command(label="Remove", command=self.footnote_remove)

    def view_bind_keys(self, view=None):
        super().view_bind_keys(view=view)
        self.view.bind("<<Modified>>", self.handle_modified)
        self.view.bind("<Button-3>", self.popup_menu)

    def info_setup(self):
        self.info_frame = ttk.Frame(self.frame, padding=2)
        self.info_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        self.frame.rowconfigure(1, minsize=22)

        self.chars_var = tk.StringVar()
        chars_label = ttk.Label(self.info_frame)
        chars_label.grid(row=0, column=0, padx=4, sticky=tk.W)
        self.info_frame.columnconfigure(0, weight=1)
        chars_label["textvariable"] = self.chars_var
        self.chars_var.set(f"{self.character_count} characters")

        status_label = ttk.Label(self.info_frame)
        status_label.grid(row=0, column=1, padx=4, sticky=tk.E)
        status_label["textvariable"] = self.status_var # Defined above in 'menu_status'.
        self.status_var.set(str(self.text.status))
        self.info_frame.columnconfigure(1, weight=1)

    @property
    def character_count(self):
        return len(self.view.get("1.0", tk.END))

    def cursor_offset(self, sign=None):
        "Return the offset to convert the cursor position to the one to use."
        return ""

    def key_press(self, event):
        pos = self.view.index(tk.INSERT)
        tags = self.view.tag_names(pos)
        # Do not allow modifying keys from encroaching on a list item bullet.
        if constants.LIST_BULLET in tags and event.char:
            return "break"
        # Do not allow modifying keys from encroaching on a reference.
        if constants.REFERENCE in tags and event.char:
            return "break"
        # Do not allow modifying keys from encroaching on a footnote reference.
        if constants.FOOTNOTE_REF in tags and event.char:
            return "break"
        # Do not allow 'Return' when in list; for now.
        if event.keysym == "Return":
            for tag in tags:
                if tag.startswith(constants.LIST_PREFIX):
                    return "break"
        self.chars_var.set(f"{self.character_count} characters")

    def popup_menu(self, event):
        "Create a popup menu according to current state and display."
        menu = tk.Menu(self.view)
        any_item = False
        try:
            first, last = self.get_selection(check_no_boundary=False)
        except ValueError:
            if self.main.paste_buffer:
                menu.add_command(label="Paste", command=self.buffer_paste)
                any_item = True
            tags = self.view.tag_names(tk.INSERT + "-1c")
            if constants.LINK in tags:
                menu.add_command(label="Remove link", command=self.link_remove)
                any_item = True
            if constants.INDEXED in tags:
                menu.add_command(label="Remove indexed", command=self.indexed_remove)
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
            if any_item:
                menu.add_separator()
            menu.add_command(label="Add list", command=self.list_add)
            any_item = True
            for tag in tags:
                if tag.startswith(constants.LIST_ITEM_PREFIX):
                    menu.add_command(label="Add list item",
                                     command=functools.partial(self.list_item_add,
                                                               tags=tags))
                    menu.add_command(label="Remove list item",
                                     command=functools.partial(self.list_item_remove,
                                                               tags=tags))
                    break
        else:                   # There is current selection.
            if not self.selection_contains_boundary(first, last, show=False):
                menu.add_command(label="Link", command=self.link_add)
                menu.add_command(label="Index", command=self.indexed_add)
                menu.add_command(label="Bold", command=self.bold_add)
                menu.add_command(label="Italic", command=self.italic_add)
                menu.add_command(label="Quote", command=self.quote_add)
                menu.add_separator()
                menu.add_command(label="Copy", command=self.buffer_copy)
                menu.add_command(label="Cut", command=self.buffer_cut)
                any_item = True
        if any_item:
            menu.tk_popup(event.x_root, event.y_root)

    def get_ignore_modified_event(self):
        "Always Tru first time accessed."
        try:
            return self._ignore_modified_event
        except AttributeError:
            self._ignore_modified_event = True
            return self._ignore_modified_event

    def set_ignore_modified_event(self, value):
        self._ignore_modified_event = value

    ignore_modified_event = property(get_ignore_modified_event, 
                                     set_ignore_modified_event)

    @property
    def is_modified(self):
        return self.view.edit_modified()

    def set_modified(self):
        self.ignore_modified_event = True
        self.view.edit_modified(True)

    def handle_modified(self, event=None):
        if self.ignore_modified_event:
            self.ignore_modified_event = False
        if not self.is_modified:
            return
        self.original_menubar_background = self.menubar.cget("background")
        self.menubar.configure(background=constants.MODIFIED_COLOR)
        self.main.treeview_set_info(self.text, modified=True)

    def set_status(self):
        try:
            old_status = self.text.status
        except AttributeError:
            old_status =  None
        new_status = constants.Status.lookup(self.status_var.get().lower())
        self.view.edit_modified(new_status != old_status)

    def bold_add(self):
        try:
            first, last = self.get_selection(strip=True)
        except ValueError:
            return
        self.view.tag_add(constants.BOLD, first, last)
        self.set_modified()

    def bold_remove(self):
        current = self.view.index(tk.INSERT)
        if constants.BOLD in self.view.tag_names(current):
            region = self.view.tag_prevrange(constants.BOLD, current)
            if region:
                self.view.tag_remove(constants.BOLD, *region)
                self.set_modified()

    def italic_add(self):
        try:
            first, last = self.get_selection(strip=True)
        except ValueError:
            return
        self.view.tag_add(constants.ITALIC, first, last)
        self.set_modified()

    def italic_remove(self):
        current = self.view.index(tk.INSERT)
        if constants.ITALIC in self.view.tag_names(current):
            region = self.view.tag_prevrange(constants.ITALIC, current)
            if region:
                self.view.tag_remove(constants.ITALIC, *region)
                self.set_modified()

    def quote_add(self):
        try:
            first, last = self.get_selection()
        except ValueError:
            return
        self.view.tag_add(constants.QUOTE, first, last)
        if "\n\n" not in self.view.get(last, last + "+2c"):
            self.view.insert(last, "\n\n")
        if "\n\n" not in self.view.get(first + "-2c", first):
            self.view.insert(first, "\n\n")
        self.set_modified()

    def quote_remove(self):
        current = self.view.index(tk.INSERT)
        if constants.QUOTE in self.view.tag_names(current):
            region = self.view.tag_prevrange(constants.QUOTE, current)
            if region:
                self.view.tag_remove(constants.QUOTE, *region)
                self.set_modified()

    def list_add(self):
        raise NotImplementedError

    def list_item_add(self, tags):
        # XXX add item where cursor is, not at the end of the list.
        depth = 0
        for t in tags:
            if t.startswith(constants.LIST_ITEM_PREFIX):
                n, c = t[len(constants.LIST_ITEM_PREFIX):].split("-")
                d = self.list_lookup[n]
                if d["depth"] > depth:
                    data = d
                    depth = d["depth"]
                    count = int(c)
        first, last = self.view.tag_nextrange(data["tag"], "1.0")
        tags = set(tags)
        tags.remove(data["tag"])
        self.view.mark_set(tk.INSERT, last)
        self.view.insert(tk.INSERT, "\n")
        if not data["tight"]:
            self.view.insert(tk.INSERT, "\n")
        if data["ordered"]:
            bullet = f"{count+1}."
        else:
            bullet = data["bullet"] + " "
        first = self.view.index(tk.INSERT)
        self.view.insert(tk.INSERT, f"{bullet} ", (constants.LIST_BULLET, ))
        data["count"] += 1
        tag = f"{constants.LIST_ITEM_PREFIX}{data['number']}-{data['count']}"
        self.view.tag_configure(tag,
                                lmargin1=data["depth"]*constants.LIST_INDENT,
                                lmargin2=(data["depth"]+0.5)*constants.LIST_INDENT)
        self.view.tag_add(tag, first, tk.INSERT)
        tag = f"{constants.LIST_PREFIX}{data['number']}"
        self.view.tag_add(tag, first, tk.INSERT)
        for tag in tags:
            self.view.tag_add(tag, first, tk.INSERT)

    def list_item_remove(self, tags):
        depth = 0
        for t in tags:
            if t.startswith(constants.LIST_ITEM_PREFIX):
                n, c = t[len(constants.LIST_ITEM_PREFIX):].split("-")
                d = self.list_lookup[n]
                d = self.list_lookup[n]
                if d["depth"] > depth:
                    tag = t
                    data = d
                    depth = d["depth"]
                    count = int(c)
        first, last = self.view.tag_nextrange(tag, "1.0")
        # Also remove the newline after the previous line.
        first = self.view.index(first + "-1c")
        self.view.delete(first, last)

    def link_action(self, event):
        "Allow viewing, editing and opening the link."
        link = self.get_link()
        if not link:
            return
        edit = LinkEdit(self.view, link)
        if edit.result:
            if edit.result["url"]:
                link["url"] = edit.result["url"]
                link["title"] = edit.result["title"]
            else:
                region = self.view.tag_nextrange(link["tag"], "1.0")
                self.view.tag_remove(constants.LINK, *region)
                self.view.tag_delete(link["tag"])
                # Do not remove entry from 'links': the count must be preserved.
            self.set_modified()

    def link_add(self):
        try:
            first, last = self.get_selection()
        except ValueError:
            return
        url = tk_simpledialog.askstring(
            parent=self.toplevel,
            title="Link URL?",
            prompt="Give URL for link")
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
        self.view.tag_remove(tk.SEL, first, last)
        self.set_modified()

    def link_remove(self):
        link = self.get_link()
        if not link:
            return
        if not tk_messagebox.askokcancel(
                parent=self.toplevel,
                title="Remove link?",
                message=f"Really remove link?"):
            return
        first, last = self.view.tag_nextrange(link["tag"], "1.0")
        self.view.tag_delete(link["tag"])
        self.view.tag_remove(constants.LINK, first, last)
        self.set_modified()
        # Links are not removed from 'links' during a session.
        # The link count must remain strictly increasing.

    def indexed_add(self):
        try:
            first, last = self.get_selection()
        except ValueError:
            return
        term = self.view.get(first, last)
        canonical = tk_simpledialog.askstring(
            parent=self.toplevel,
            title="Canonical?",
            prompt="Give canonical term",
            initialvalue=term)
        if canonical is None:
            return
        if not canonical:
            canonical = term
        self.view.tag_add(constants.INDEXED, first, last)
        self.view.tag_add(constants.INDEXED_PREFIX + canonical, first, last)
        self.set_modified()

    def indexed_remove(self):
        for tag in self.view.tag_names(tk.CURRENT):
            if tag.startswith(constants.INDEXED_PREFIX):
                first, last = self.view.tag_nextrange(tag, "1.0")
                self.view.tag_remove(constants.INDEXED, first, last)
                self.view.tag_remove(tag, first, last)
        self.set_modified()

    def reference_add(self):
        raise NotImplementedError

    def reference_remove(self):
        raise NotImplementedError

    def footnote_add(self):
        try:
            first, last = self.get_selection()
        except ValueError:
            return
        label = self.get_new_footnote_label()
        tag = constants.FOOTNOTE_DEF_PREFIX + label
        self.tag_elide(tag)
        self.view.tag_add(constants.FOOTNOTE_DEF, first, last)
        self.view.tag_add(tag, first, last)
        self.view.insert(self.view.tag_nextrange(tag, "1.0")[0], "\n", (tag, ))
        tag = constants.FOOTNOTE_REF_PREFIX + label
        self.footnotes[label] = dict(label=label, tag=tag)
        self.view.insert(first, f"^{label}", (constants.FOOTNOTE_REF, (tag, )))
        self.view.tag_bind(tag, "<Button-1>", self.footnote_toggle)

    def get_new_footnote_label(self):
        try:
            return str(max([int(label) for label in self.footnotes]) + 1)
        except ValueError:
            return "1"

    def footnote_remove(self):
        current = self.view.index(tk.INSERT)
        tags = self.view.tag_names(current)
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
        region = self.view.tag_nextrange(tag, "1.0")
        self.view.tag_remove(constants.FOOTNOTE_REF, *region)
        self.view.tag_delete(tag)
        self.view.delete(*region)
        tag = constants.FOOTNOTE_DEF_PREFIX + label
        region = self.view.tag_nextrange(tag, "1.0")
        self.view.tag_remove(constants.FOOTNOTE_DEF, *region)
        self.view.tag_delete(tag)
        self.view.tag_add(tk.SEL, *region)

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
        self.view.delete(first, last)

    def buffer_paste(self):
        "Paste in contents from the paste buffer."
        first = self.view.index(tk.INSERT)
        self.undump(self.main.paste_buffer)
        self.view.tag_remove(tk.SEL, first, tk.INSERT)

    def dump_clean(self, first, last):
        "Get the dump of the contents, cleanup and preprocess."
        # Get rid of irrelevant marks.
        dump = [e for e in self.view.dump(first, last)
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
        self.view.insert(tk.INSERT, entry[1])

    def undump_tagon(self, entry, tags):
        if entry[1].startswith(constants.FOOTNOTE_REF_PREFIX):
            label = self.get_new_footnote_label()
            tags[entry[1]] = dict(label=label,
                                  first=self.view.index(tk.INSERT))
            self.skip_text = True
        elif entry[1].startswith(constants.FOOTNOTE_DEF_PREFIX):
            ref_tag = constants.FOOTNOTE_REF_PREFIX + entry[1][len(constants.FOOTNOTE_DEF_PREFIX):]
            tags[entry[1]] = dict(label=tags[ref_tag]["label"],
                                  first=self.view.index(tk.INSERT))
        else:
            tags[entry[1]] = dict(first=self.view.index(tk.INSERT))

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
                                 self.view.index(tk.INSERT))
            elif entry[1].startswith(constants.FOOTNOTE_REF_PREFIX):
                label = data["label"]
                tag = constants.FOOTNOTE_REF_PREFIX + label
                self.view.insert(tk.INSERT, f"^{label}", (constants.FOOTNOTE_REF, tag))
                self.view.tag_bind(tag, "<Button-1>", self.footnote_toggle)
                self.skip_text = False
                self.footnotes[label] = dict(label=label, tag=tag)
            elif entry[1].startswith(constants.FOOTNOTE_DEF_PREFIX):
                tag = constants.FOOTNOTE_DEF_PREFIX + data["label"]
                self.tag_configure_elide(tag)
                self.view.tag_add(tag, data["first"], tk.INSERT)
            else:
                self.view.tag_add(entry[1], data["first"], self.view.index(tk.INSERT))

    def undump_mark(self, entry, tags):
        self.view.mark_set(entry[1], tk.INSERT)

    def save(self, event=None):
        """Save the current contents to the text file.
        Get the main window to refresh the contents of the text view.
        """
        if not self.is_modified:
            return
        self.text.status = constants.Status.lookup(self.status_var.get().lower())
        self.set_outfile(io.StringIO())
        self.markdown()
        self.text.write(self.outfile.getvalue())
        self.set_outfile()
        self.menubar.configure(background=self.original_menubar_background)
        self.ignore_modified_event = True
        self.view.edit_modified(False)
        self.text.viewer.display()
        self.main.treeview_set_info(self.text)
        self.main.references_viewer.display() # XXX Optimize?
        self.main.indexed_viewer.display()    # XXX Optimize?
        self.main.search_viewer.clear()

    @property
    def outfile(self):
        return self.outfile_stack[-1]

    def set_outfile(self, outfile=None):
        if outfile is None:
            self.outfile_stack = []
        else:
            self.outfile_stack = [outfile]

    def markdown(self):
        self.line_indents = []
        self.line_indented = False
        self.skip_text = False
        self.list_stack = []
        self.markdown_footnotes = dict()
        # This does not need the cleaned dump.
        # There is no title here that needs to be taken into account.
        for item in self.view.dump("1.0", tk.END):
            try:
                method = getattr(self, f"markdown_{item[0]}")
            except AttributeError:
                ic("Could not markdown item", item)
            else:
                method(item)
        footnotes = list(self.markdown_footnotes.values())
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
        try:
            method = getattr(self, f"markdown_tagon_{item[1]}")
        except AttributeError:
            if item[1].startswith(constants.LIST_PREFIX):
                self.markdown_start_list(item[1])
        else:
            method(item)

    def markdown_tagoff(self, item):
        try:
            method = getattr(self, f"markdown_tagoff_{item[1]}")
        except AttributeError:
            if item[1].startswith(constants.LIST_PREFIX):
                self.markdown_finish_list(item[1])
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

    def markdown_tagon_quote(self, item):
        self.line_indents.append("> ")

    def markdown_tagoff_quote(self, item):
        self.line_indents.pop()

    def markdown_tagon_thematic_break(self, item):
        self.skip_text = True

    def markdown_tagoff_thematic_break(self, item):
        self.output_characters("---")
        self.output_line_indent(force=True)
        self.outfile.write("\n")
        self.skip_text = False

    def markdown_start_list(self, tag):
        data = self.list_lookup[tag]
        data["count"] = data["start"]
        if len(self.list_stack):
            self.line_indents.append("    ")
        self.list_stack.append(data)

    def markdown_finish_list(self, tag):
        self.list_stack.pop()
        if len(self.list_stack):
            self.line_indents.pop()

    def markdown_tagon_list_bullet(self, item):
        data = self.list_stack[-1]
        if data["ordered"]:
            self.output_characters(f"{data['count']}. ")
            data["count"] += 1
        else:
            self.output_characters("- ")
        self.skip_text = True

    def markdown_tagoff_list_bullet(self, item):
        self.skip_text = False

    def markdown_tagon_link(self, item):
        for tag in self.view.tag_names(item[2]):
            if tag.startswith(constants.LINK_PREFIX):
                self.current_link_tag = tag
                break
        self.output_characters("[")

    def markdown_tagoff_link(self, item):
        link = self.get_link(self.current_link_tag)
        if link["title"]:
            self.output_characters(f"""]({link['url']} "{link['title']}")""")
        else:
            self.output_characters(f"]({link['url']})")
        self.current_link_tag = None

    def markdown_tagon_indexed(self, item):
        for tag in self.view.tag_names(item[2]):
            if tag.startswith(constants.INDEXED_PREFIX):
                first, last = self.view.tag_nextrange(tag, item[2])
                self.current_indexed_term = self.view.get(first, last)
                self.current_indexed_tag = tag
                break
        self.output_characters("[#")

    def markdown_tagoff_indexed(self, item):
        canonical = self.current_indexed_tag[len(constants.INDEXED_PREFIX):]
        if self.current_indexed_term == canonical:
            self.output_characters("]")
        else:
            self.output_characters(f"|{canonical}]")

    def markdown_tagon_reference(self, item):
        self.output_characters("[@")

    def markdown_tagoff_reference(self, item):
        self.output_characters("]")

    def markdown_tagon_footnote_ref(self, item):
        for tag in self.view.tag_names(item[2]):
            if tag.startswith(constants.FOOTNOTE_REF_PREFIX):
                old_label = tag[len(constants.FOOTNOTE_REF_PREFIX):]
                footnote = self.footnotes[old_label]
                new_label = str(len(self.markdown_footnotes) + 1)
                footnote["new_label"] = new_label
                self.markdown_footnotes[old_label] = footnote
                break
        self.output_characters(f"[^{new_label}]")
        self.skip_text = True

    def markdown_tagoff_footnote_ref(self, item):
        pass

    def markdown_tagon_footnote_def(self, item):
        for tag in self.view.tag_names(item[2]):
            if tag.startswith(constants.FOOTNOTE_DEF_PREFIX):
                old_label = tag[len(constants.FOOTNOTE_DEF_PREFIX):]
        footnote = self.markdown_footnotes[old_label]
        footnote["outfile"] = io.StringIO()
        self.outfile_stack.append(footnote["outfile"])
        self.skip_text = False

    def markdown_tagoff_footnote_def(self, item):
        self.outfile_stack.pop()

    def close(self, event=None, force=False):
        if self.is_modified and not force:
            if not tk_messagebox.askokcancel(
                    parent=self.toplevel,
                    title="Close?",
                    message="Modifications will not be saved. Really close?"):
                return
        self.ignore_modified_event = True
        self.view.edit_modified(False)
        self.main.close_editor(self.text)
        self.toplevel.destroy()


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
