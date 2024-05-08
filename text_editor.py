"Editor window for Markdown text file."

from icecream import ic

import functools
import io
import os.path
import string
import webbrowser

import tkinter as tk
import tkinter.ttk
import tkinter.simpledialog
import tkinter.messagebox

import constants
import utils

from utils import Tr
from text_viewer import TextViewer


class TextEditor(TextViewer):
    "Editor window for Markdown text file."

    TEXT_COLOR = constants.EDIT_COLOR

    def __init__(self, main, text):
        super().__init__(main.root, main, text)

        self.toplevel = tk.Toplevel(self.main.root)
        self.toplevel.title(f"Edit: {text.fullname}")
        self.toplevel.bind("<Control-s>", self.save)
        self.toplevel.bind("<Control-q>", self.close)
        self.toplevel.protocol("WM_DELETE_WINDOW", self.close)
        try:
            self.toplevel.geometry(self.text["geometry"])
        except KeyError:
            pass

        self.menubar_setup()
        self.view_create(self.toplevel)
        self.view_configure_tags()
        self.view_configure_tag_bindings()
        self.view_bind_keys()
        self.render(self.text.ast)
        self.info_setup()
        self.view.edit_modified(False)

    def display_title(self):
        "Do not display the title in the text edit area."
        pass

    def menubar_setup(self):
        self.menubar = tk.Menu(self.toplevel, background="gold")
        self.menubar_selection_change = set()
        self.toplevel["menu"] = self.menubar
        self.menubar.add_command(label="Au",
                                 font=constants.FONT_LARGE_BOLD,
                                 background="gold",
                                 command=self.main.root.lift)

        self.menu_file = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_file, label=Tr("File"))
        self.menu_file.add_command(label=Tr("Save"),
                                   command=self.save,
                                   accelerator="Ctrl-S")
        self.menu_file.add_command(label=Tr("Close"),
                                   command=self.close,
                                   accelerator="Ctrl-Q")

        self.menu_edit = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_edit, label=Tr("Edit"))
        self.menu_edit.add_command(label=Tr("Copy"), command=self.buffer_copy)
        self.menu_edit.add_command(label=Tr("Cut"), command=self.buffer_cut)
        self.menu_edit.add_command(label=Tr("Paste"), command=self.buffer_paste)

        self.menu_format = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_format,
                                 label=Tr("Format"),
                                 state=tk.DISABLED)
        self.menubar_selection_change.add(self.menubar.index(tk.END))
        self.menu_format.add_command(label=Tr("Bold"), command=self.bold_add)
        self.menu_format.add_command(label=Tr("Italic"), command=self.italic_add)
        self.menu_format.add_command(label=Tr("Quote"), command=self.quote_add)
        for level in range(1, constants.MAX_H_LEVEL + 1):
            self.menu_format.add_command(label=f"{Tr('Heading')} {level}",
                                         command=functools.partial(self.heading_add,
                                                                   level=level))

        self.menu_list = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_list, label=Tr("List"))
        self.menu_list.add_command(label=Tr("Ordered"),
                                   command=functools.partial(self.list_add,
                                                             ordered=True))
        self.menu_list.add_command(label=Tr("Unordered"),
                                   command=functools.partial(self.list_add,
                                                             ordered=False))

        self.menubar.add_command(label=Tr("Reference"), command=self.reference_add)
        self.menubar.add_command(label=Tr("Link"),
                                 command=self.link_add,
                                 state=tk.DISABLED)
        self.menubar_selection_change.add(self.menubar.index(tk.END))
        self.menubar.add_command(label=Tr("Indexed"),
                                 command=self.indexed_add,
                                 state=tk.DISABLED)
        self.menubar_selection_change.add(self.menubar.index(tk.END))
        self.menubar.add_command(label=Tr("Footnote"),
                                 command=self.footnote_add,
                                 state=tk.DISABLED)
        self.menubar_selection_change.add(self.menubar.index(tk.END))

        self.menu_status = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_status, label=Tr("Status"))
        self.status_var = tk.StringVar() # Also referred to by 'info_setup'.
        for status in constants.STATUSES:
            self.menu_status.add_radiobutton(label=Tr(str(status)),
                                             value=str(status),
                                             variable=self.status_var,
                                             command=self.set_status)

    def view_configure_tag_bindings(self, view=None):
        "Configure the tag bindings used in the 'tk.Text' instance."
        if view is None:
            view = self.view
        super().view_configure_tag_bindings(view=view)
        view.tag_bind(constants.BOLD, "<Button-1>", self.bold_remove)
        view.tag_bind(constants.ITALIC, "<Button-1>", self.italic_remove)
        view.tag_bind(constants.QUOTE, "<Button-1>", self.quote_remove)
        for tag in constants.H_LOOKUP.values():
            view.tag_bind(tag, "<Button-1>", self.heading_remove)
        view.tag_bind(constants.FOOTNOTE_REF, "<Button-1>", self.footnote_remove)

    def view_bind_keys(self, view=None):
        super().view_bind_keys(view=view)
        self.view.bind("<<Modified>>", self.handle_modified)
        self.view.bind("<Button-3>", self.popup_menu)
        self.view.bind("<<Selection>>", self.selection_change)

    def info_setup(self):
        self.info_frame = tk.ttk.Frame(self.frame, padding=2)
        self.info_frame.grid(row=1, column=0, sticky=(tk.W, tk.E))
        self.frame.rowconfigure(1, minsize=22)

        self.chars_var = tk.StringVar()
        chars_label = tk.ttk.Label(self.info_frame)
        chars_label.grid(row=0, column=0, padx=4, sticky=tk.W)
        self.info_frame.columnconfigure(0, weight=1)
        chars_label["textvariable"] = self.chars_var
        self.chars_var.set(f"{self.character_count} characters")

        status_label = tk.ttk.Label(self.info_frame)
        status_label.grid(row=0, column=1, padx=4, sticky=tk.E)
        status_label["textvariable"] = self.status_var # Defined above in 'menu_status'.
        self.status_var.set(Tr(str(self.text.status)))
        self.info_frame.columnconfigure(1, weight=1)

    @property
    def character_count(self):
        return len(self.view.get("1.0", tk.END))

    def key_press(self, event):
        "Forbid some key press actions."
        tags = set(self.view.tag_names(tk.INSERT))
        if event.char:
            # For 'Backspace', check the position before.
            if event.keysym == "BackSpace":
                tags =self.view.tag_names(tk.INSERT + "-1c")
            # Do not allow 'Return' when in list; temporary solution.
            elif event.keysym == "Return":
                for tag in tags:
                    if tag.startswith(constants.LIST_PREFIX):
                        return "break"
            # Do not allow modifying keys from modifying a list item bullet.
            if constants.LIST_BULLET in tags:
                return "break"
            # Do not allow modifying keys from modifying a reference.
            if constants.REFERENCE in tags:
                return "break"
            # Do not allow modifying keys from modifying a footnote reference.
            if constants.FOOTNOTE_REF in tags:
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
                menu.add_command(label=Tr("Paste"), command=self.buffer_paste)
                any_item = True
            tags = self.view.tag_names(tk.INSERT + "-1c")
            if any_item:
                menu.add_separator()
            for tag in tags:
                if tag.startswith(constants.LIST_ITEM_PREFIX):
                    menu.add_command(label=Tr("Add list item"),
                                     command=functools.partial(self.list_item_add,
                                                               tags=tags))
                    menu.add_command(label=Tr("Remove list item"),
                                     command=functools.partial(self.list_item_remove,
                                                               tags=tags))
                    break
            menu.add_command(label=Tr("Add ordered list"),
                             command=functools.partial(self.list_add, ordered=True))
            menu.add_command(label=Tr("Add unordered list"),
                             command=functools.partial(self.list_add, ordered=False))
            any_item = True
        else:                   # There is current selection.
            if not self.selection_contains_boundary(first, last, complain=False):
                menu.add_command(label=Tr("Copy"), command=self.buffer_copy)
                menu.add_command(label=Tr("Cut"), command=self.buffer_cut)
                menu.add_separator()
                menu.add_command(label=Tr("Bold"), command=self.bold_add)
                menu.add_command(label=Tr("Italic"), command=self.italic_add)
                menu.add_command(label=Tr("Quote"), command=self.quote_add)
                menu.add_separator()
                menu.add_command(label=Tr("Link"), command=self.link_add)
                menu.add_command(label=Tr("Indexed"), command=self.indexed_add)
                any_item = True
        if any_item:
            menu.tk_popup(event.x_root, event.y_root)

    def selection_change(self, event):
        try:
            self.view.index(tk.SEL_FIRST)
        except tk.TclError:
            for pos in self.menubar_selection_change:
                self.menubar.entryconfigure(pos, state=tk.DISABLED)
        else:
            for pos in self.menubar_selection_change:
                self.menubar.entryconfigure(pos, state=tk.NORMAL)

    def get_ignore_modified_event(self):
        "Always True first time accessed."
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

    def bold_remove(self, event):
        if constants.BOLD not in self.view.tag_names(tk.CURRENT):
            return
        if not tk.messagebox.askokcancel(
                parent=self.toplevel,
                title="Remove bold?",
                message="Really remove bold?"):
            return
        first, last = self.view.tag_prevrange(constants.BOLD, tk.CURRENT)
        self.view.tag_remove(constants.BOLD, first, last)
        self.set_modified()

    def italic_add(self):
        try:
            first, last = self.get_selection(strip=True)
        except ValueError:
            return
        self.view.tag_add(constants.ITALIC, first, last)
        self.set_modified()

    def italic_remove(self, event):
        if constants.ITALIC not in self.view.tag_names(tk.CURRENT):
            return
        first, last = self.view.tag_prevrange(constants.ITALIC, tk.CURRENT)
        if not tk.messagebox.askokcancel(
                parent=self.toplevel,
                title="Remove italic?",
                message="Really remove italic?"):
            return
        self.view.tag_remove(constants.ITALIC, first, last)
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

    def quote_remove(self, event):
        if constants.QUOTE not in self.view.tag_names(tk.CURRENT):
            return
        first, last = self.view.tag_prevrange(constants.QUOTE, tk.CURRENT)
        if not tk.messagebox.askokcancel(
                parent=self.toplevel,
                title="Remove quote?",
                message=f"Really remove quote?"):
            return
        self.view.tag_remove(constants.QUOTE, first, last)
        self.set_modified()

    def heading_add(self, level):
        try:
            first, last = self.get_selection()
        except ValueError:
            return
        self.view.tag_add(constants.H_LOOKUP[level], first, last)
        if "\n\n" not in self.view.get(last, last + "+2c"):
            self.view.insert(last, "\n\n")
        if "\n\n" not in self.view.get(first + "-2c", first):
            self.view.insert(first, "\n\n")
        self.set_modified()

    def heading_remove(self, event):
        tags = self.view.tag_names(tk.CURRENT)
        for tag in constants.H_LOOKUP.values():
            if tag in tags:
                break
        else:
            return
        first, last = self.view.tag_prevrange(tag, tk.CURRENT)
        if not tk.messagebox.askokcancel(
                parent=self.toplevel,
                title="Remove heading?",
                message=f"Really remove heading?"):
            return
        self.view.tag_remove(tag, first, last)
        self.set_modified()

    def list_add(self, ordered):
        data = self.list_create_entry(ordered, 1, True)
        if ordered:
            data["bullet"] = f"{data['count']}."
            data["depth"] = 1
        else:
            # XXX actual depth needed
            data["depth"] = 0
            data["bullet"] = constants.LIST_BULLETS[data["depth"]]
            data["depth"] += 1
        self.view.insert(tk.INSERT, "\n")
        first = self.view.index(tk.INSERT)
        self.view.insert(tk.INSERT, data["bullet"] + " ", (constants.LIST_BULLET, ))
        tag = f"{constants.LIST_ITEM_PREFIX}{data['number']}-{data['count']}"
        self.view.tag_configure(tag,
                                lmargin1=data["depth"]*constants.LIST_INDENT,
                                lmargin2=(data["depth"]+0.5)*constants.LIST_INDENT)
        self.view.tag_add(tag, first, tk.INSERT)
        self.view.tag_add(data["tag"], first, tk.INSERT)
        data["count"] += 1

    def list_item_add(self, tags):
        # XXX item is not added to the correct place, if another has been
        # added before in in the same edit session.
        depth = 0
        for t in tags:
            if t.startswith(constants.LIST_ITEM_PREFIX):
                n, c = t[len(constants.LIST_ITEM_PREFIX):].split("-")
                d = self.lists_lookup[n]
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
            data["bullet"] = f"{count+1}."
        else:
            data["bullet"] = data["bullet"]
        first = self.view.index(tk.INSERT)
        self.view.insert(tk.INSERT, data["bullet"] + " ", (constants.LIST_BULLET, ))
        data["count"] += 1
        tag = f"{constants.LIST_ITEM_PREFIX}{data['number']}-{data['count']}"
        self.view.tag_configure(tag,
                                lmargin1=data["depth"]*constants.LIST_INDENT,
                                lmargin2=(data["depth"]+0.5)*constants.LIST_INDENT)
        # Kludge to make insert point be placed within list tags.
        self.view.insert(tk.INSERT, " ")
        self.view.tag_add(tag, first, tk.INSERT)
        tag = f"{constants.LIST_PREFIX}{data['number']}"
        self.view.tag_add(tag, first, tk.INSERT)
        for tag in tags:
            self.view.tag_add(tag, first, tk.INSERT)
        # Kludge to make insert point be placed within list tags.
        self.view.mark_set(tk.INSERT, self.view.index(tk.INSERT + "-1c"))

    def list_item_remove(self, tags):
        depth = 0
        for t in tags:
            if t.startswith(constants.LIST_ITEM_PREFIX):
                n, c = t[len(constants.LIST_ITEM_PREFIX):].split("-")
                d = self.lists_lookup[n]
                d = self.lists_lookup[n]
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
        if not edit.result:
            return
        if edit.result["url"]:
            link["url"] = edit.result["url"]
            link["title"] = edit.result["title"]
        else:
            first, last = self.view.tag_nextrange(link["tag"], "1.0")
            self.view.tag_remove(constants.LINK, first, last)
            self.view.tag_delete(link["tag"])
            # Do not remove entry from 'links': the count must be preserved.
        self.set_modified()

    def link_add(self):
        try:
            first, last = self.get_selection()
        except ValueError:
            return
        url = tk.simpledialog.askstring(
            parent=self.toplevel,
            title="Link URL?",
            prompt="URL for link")
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

    def indexed_add(self):
        try:
            first, last = self.get_selection()
        except ValueError:
            return
        term = self.view.get(first, last)
        canonical = tk.simpledialog.askstring(
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

    def indexed_remove(self, event):
        term = self.get_indexed()
        if not term:
            return
        if not tk.messagebox.askokcancel(
                parent=self.toplevel,
                title="Remove indexed?",
                message=f"Really remove indexing for '{term}'?"):
            return
        first, last = self.view.tag_prevrange(constants.INDEXED, tk.CURRENT)
        self.view.tag_remove(constants.INDEXED, first, last)
        self.view.tag_remove(f"{constants.INDEXED_PREFIX}{term}", first, last)
        self.set_modified()

    def indexed_action(self, event):
        term = self.get_indexed()
        if not term:
            return
        tag = constants.INDEXED_PREFIX + term
        first, last = self.view.tag_prevrange(tag, tk.CURRENT)
        edit = IndexedEdit(self.main, self.view, term)
        if edit.result is None or edit.result == term:
            return
        self.view.tag_remove(tag, first, last)
        if edit.result:
            self.view.tag_add(constants.INDEXED_PREFIX + edit.result, first, last)
        else:
            self.view.tag_remove(constants.INDEXED, first, last)
        self.set_modified()

    def reference_add(self):
        add = ReferenceAdd(self.view, self.main.references_viewer.references)
        if not add.result:
            return
        tag = constants.REFERENCE_PREFIX + add.result
        self.view.insert(tk.INSERT, add.result, (constants.REFERENCE, tag))

    def reference_action(self, event):
        reference = self.get_reference()
        if not reference:
            return
        if not tk.messagebox.askokcancel(
                parent=self.toplevel,
                title="Remove reference?",
                message=f"Really remove reference '{reference}'?"):
            return
        tag = f"{constants.REFERENCE_PREFIX}{reference}"
        first, last = self.view.tag_prevrange(tag, tk.CURRENT)
        self.view.delete(first, last)
        self.set_modified()

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
        "Return the label (str) to use for a new footnote."
        try:
            return str(max([int(label) for label in self.footnotes]) + 1)
        except ValueError:
            return "1"

    def footnote_remove(self, event):
        tags = self.view.tag_names(tk.CURRENT)
        for tag in tags:
            if tag.startswith(constants.FOOTNOTE_REF_PREFIX):
                label = tag[len(constants.FOOTNOTE_REF_PREFIX):]
                break
        else:
            return
        tag = constants.FOOTNOTE_REF_PREFIX + label
        first, last = self.view.tag_nextrange(tag, "1.0")
        if not tk.messagebox.askokcancel(
                parent=self.toplevel,
                title="Remove footnote?",
                message=f"Really remove footnote (text will remain)?"):
            return
        self.view.tag_remove(constants.FOOTNOTE_REF, first, last)
        self.view.tag_delete(tag)
        self.view.delete(first, self.view.index(last + "+1c")) # Remove newline.
        tag = constants.FOOTNOTE_DEF_PREFIX + label
        first, last = self.view.tag_nextrange(tag, "1.0")
        self.view.tag_remove(constants.FOOTNOTE_DEF, first, last)
        self.view.tag_delete(tag)
        self.view.tag_add(tk.SEL, first, last)

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
        "Read a dump, adding to the content of the view."
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
            tags[entry[1]] = dict(label=label, first=self.view.index(tk.INSERT))
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
        self.outfile_stack = [io.StringIO()]
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
        self.text.write(self.outfile.getvalue())
        self.outfile_stack = []
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

    def save_line_indent(self, force=False):
        if self.line_indented and not force:
            return
        self.outfile.write("".join(self.line_indents))
        self.line_indented = True

    def save_characters(self, characters):
        if not characters:
            return
        segments = characters.split("\n")
        if len(segments) == 1:
            self.save_line_indent()
            self.outfile.write(segments[0])
        else:
            for segment in segments[:-1]:
                self.save_line_indent()
                self.outfile.write(segment)
                self.outfile.write("\n")
                self.line_indented = False
            if segments[-1]:
                self.save_line_indent()
                self.outfile.write(segments[-1])
                self.outfile.write("\n")
                self.line_indented = False

    def markdown_text(self, item):
        if self.skip_text:
            return
        self.save_characters(item[1])

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
        self.save_characters("*")

    def markdown_tagoff_italic(self, item):
        self.save_characters("*")

    def markdown_tagon_bold(self, item):
        self.save_characters("**")

    def markdown_tagoff_bold(self, item):
        self.save_characters("**")

    def markdown_tagon_quote(self, item):
        self.line_indents.append("> ")

    def markdown_tagoff_quote(self, item):
        self.line_indents.pop()

    def markdown_tagon_h1(self, item):
        self.save_characters("# ")

    def markdown_tagoff_h1(self, item):
        pass

    def markdown_tagon_h2(self, item):
        self.save_characters("## ")

    def markdown_tagoff_h2(self, item):
        pass

    def markdown_tagon_h3(self, item):
        self.save_characters("### ")

    def markdown_tagoff_h3(self, item):
        pass

    def markdown_tagon_h4(self, item):
        self.save_characters("#### ")

    def markdown_tagoff_h4(self, item):
        pass

    def markdown_tagon_thematic_break(self, item):
        self.skip_text = True

    def markdown_tagoff_thematic_break(self, item):
        self.save_characters("---")
        self.save_line_indent(force=True)
        self.outfile.write("\n")
        self.skip_text = False

    def markdown_start_list(self, tag):
        data = self.lists_lookup[tag]
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
            self.save_characters(f"{data['count']}. ")
            data["count"] += 1
        else:
            self.save_characters("- ")
        self.skip_text = True

    def markdown_tagoff_list_bullet(self, item):
        self.skip_text = False

    def markdown_tagon_link(self, item):
        for tag in self.view.tag_names(item[2]):
            if tag.startswith(constants.LINK_PREFIX):
                self.current_link_tag = tag
                break
        self.save_characters("[")

    def markdown_tagoff_link(self, item):
        link = self.get_link(self.current_link_tag)
        if link["title"]:
            self.save_characters(f"""]({link['url']} "{link['title']}")""")
        else:
            self.save_characters(f"]({link['url']})")
        self.current_link_tag = None

    def markdown_tagon_indexed(self, item):
        for tag in self.view.tag_names(item[2]):
            if tag.startswith(constants.INDEXED_PREFIX):
                first, last = self.view.tag_nextrange(tag, item[2])
                self.current_indexed_term = self.view.get(first, last)
                self.current_indexed_tag = tag
                break
        self.save_characters("[#")

    def markdown_tagoff_indexed(self, item):
        canonical = self.current_indexed_tag[len(constants.INDEXED_PREFIX):]
        if self.current_indexed_term == canonical:
            self.save_characters("]")
        else:
            self.save_characters(f"|{canonical}]")

    def markdown_tagon_reference(self, item):
        self.save_characters("[@")

    def markdown_tagoff_reference(self, item):
        self.save_characters("]")

    def markdown_tagon_footnote_ref(self, item):
        for tag in self.view.tag_names(item[2]):
            if tag.startswith(constants.FOOTNOTE_REF_PREFIX):
                old_label = tag[len(constants.FOOTNOTE_REF_PREFIX):]
                footnote = self.footnotes[old_label]
                new_label = str(len(self.markdown_footnotes) + 1)
                footnote["new_label"] = new_label
                self.markdown_footnotes[old_label] = footnote
                break
        self.save_characters(f"[^{new_label}]")
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
            if not tk.messagebox.askokcancel(
                    parent=self.toplevel,
                    title="Close?",
                    message="Modifications will not be saved. Really close?"):
                return
        self.ignore_modified_event = True
        self.view.edit_modified(False)
        self.main.close_editor(self.text)
        self.toplevel.destroy()


class IndexedEdit(tk.simpledialog.Dialog):
    "Dialog window for editing the canonical term for an indexed term."

    def __init__(self, main, toplevel, canonical):
        self.main = main
        self.canonical = canonical
        self.result = None
        super().__init__(toplevel, title="Edit indexed")

    def body(self, body):
        label = tk.ttk.Label(body, text=Tr("Canonical"))
        label.grid(row=0, column=0, padx=4, sticky=tk.E)
        self.canonical_entry = tk.Entry(body, width=50)
        self.canonical_entry.insert(0, self.canonical)
        self.canonical_entry.grid(row=0, column=1)
        return self.canonical_entry

    def remove(self):
        "Remove the indexed entry."
        self.canonical_entry.delete(0, tk.END)
        try:
            self.apply()
        finally:
            self.cancel()

    def apply(self):
        self.result = self.canonical_entry.get()

    def buttonbox(self):
        box = tk.Frame(self)
        w = tk.ttk.Button(box, text=Tr("OK"), width=10,
                          command=self.ok, default=tk.ACTIVE)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        w = tk.ttk.Button(box, text=Tr("Show"), width=10, command=self.show)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        w = tk.ttk.Button(box, text=Tr("Remove"), width=10, command=self.remove)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        w = tk.ttk.Button(box, text=Tr("Cancel"), width=10, command=self.cancel)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)
        box.pack()

    def show(self):
        self.main.indexed_viewer.highlight(self.canonical)


class LinkEdit(tk.simpledialog.Dialog):
    "Dialog window for editing the URL and title for a link."

    def __init__(self, toplevel, link):
        self.link = link
        self.result = None
        super().__init__(toplevel, title="Edit link")

    def body(self, body):
        label = tk.ttk.Label(body, text=Tr("URL"))
        label.grid(row=0, column=0, padx=4, sticky=tk.E)
        self.url_entry = tk.Entry(body, width=50)
        if self.link["url"]:
            self.url_entry.insert(0, self.link["url"])
        self.url_entry.grid(row=0, column=1)

        label = tk.ttk.Label(body, text=Tr("Title"))
        label.grid(row=1, column=0, padx=4, sticky=tk.E)
        self.title_entry = tk.Entry(body, width=50)
        if self.link["title"]:
            self.title_entry.insert(0, self.link["title"])
        self.title_entry.grid(row=1, column=1)
        return self.url_entry

    def remove(self):
        """Remove the link in the text. Do not remove from 'viewer.links'.
        The link count must remain strictly increasing.
        """
        self.url_entry.delete(0, tk.END)
        try:
            self.apply()
        finally:
            self.cancel()

    def apply(self):
        self.result = dict(url=self.url_entry.get(),
                           title=self.title_entry.get())

    def buttonbox(self):
        box = tk.Frame(self)
        w = tk.ttk.Button(box, text=Tr("OK"), width=10,
                          command=self.ok, default=tk.ACTIVE)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        w = tk.ttk.Button(box, text=Tr("Visit"), width=10, command=self.visit)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        w = tk.ttk.Button(box, text=Tr("Remove"), width=10, command=self.remove)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        w = tk.ttk.Button(box, text=Tr("Cancel"), width=10, command=self.cancel)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)
        box.pack()

    def visit(self):
        webbrowser.open_new_tab(self.url_entry.get())


class ReferenceAdd(tk.simpledialog.Dialog):
    "Dialog window for selecting a reference to add."

    def __init__(self, toplevel, references):
        self.result = None
        self.selected = None
        self.references = references
        super().__init__(toplevel, title="Add reference")

    def body(self, body):
        body.rowconfigure(0, weight=1)
        body.columnconfigure(0, weight=1)
        self.treeview = tk.ttk.Treeview(body,
                                        height=min(20, len(self.references)),
                                        columns=("title", ),
                                        selectmode="browse")
        self.treeview.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.treeview.heading("#0", text=Tr("Reference id"))
        self.treeview.column("#0",
                             anchor=tk.W,
                             minwidth=8*constants.FONT_NORMAL_SIZE,
                             width=12*constants.FONT_NORMAL_SIZE)
        self.treeview.heading("title", text=Tr("Title"), anchor=tk.W)
        self.treeview.column("title",
                             minwidth=16*constants.FONT_NORMAL_SIZE,
                             width=20*constants.FONT_NORMAL_SIZE,
                             anchor=tk.W,
                             stretch=True)
        self.treeview_scroll_y = tk.ttk.Scrollbar(body,
                                                  orient=tk.VERTICAL,
                                                  command=self.treeview.yview)
        self.treeview_scroll_y.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.treeview.configure(yscrollcommand=self.treeview_scroll_y.set)

        self.treeview.bind("<<TreeviewSelect>>", self.select)
        for reference in self.references:
            self.treeview.insert("",
                                 tk.END,
                                 reference["id"],
                                 text=str(reference),
                                 values=(reference["title"],))
        return self.treeview

    def select(self, event):
        self.selected = self.treeview.selection()[0]

    def apply(self):
        self.result = self.selected
