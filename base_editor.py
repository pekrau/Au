"Base editor window."

from icecream import ic

import functools
import io
import webbrowser

import tkinter as tk
import tkinter.ttk
import tkinter.simpledialog
import tkinter.messagebox

import constants
import utils

from utils import Tr
from text_viewer import TextViewer


class BaseEditor(TextViewer):
    "Base editor class."

    def toplevel_setup(self):
        self.toplevel = tk.Toplevel(self.main.root)
        self.toplevel.title(f"{Tr('Edit')}: {self.text.fullname}")
        self.toplevel.bind("<Control-s>", self.save)
        self.toplevel.bind("<Control-S>", self.save)
        self.toplevel.bind("<Control-q>", self.close)
        self.toplevel.bind("<Control-Q>", self.close)
        self.toplevel.protocol("WM_DELETE_WINDOW", self.close)

    def menubar_setup(self):
        self.menubar = tk.Menu(self.toplevel, background="gold")
        self.original_menubar_background = self.menubar.cget("background")
        self.menubar_selection_change = set()
        self.toplevel["menu"] = self.menubar
        self.menubar.add_command(
            label="Au",
            font=constants.FONT_LARGE_BOLD,
            background="gold",
            command=self.main.root.lift,
        )

        self.menu_file = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_file, label=Tr("File"))
        self.menubar_file_setup()

        self.menu_edit = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_edit, label=Tr("Edit"))
        self.menu_edit.add_command(label=Tr("Copy"), command=self.clipboard_copy)
        self.menu_edit.add_command(label=Tr("Cut"), command=self.clipboard_cut)
        self.menu_edit.add_command(label=Tr("Paste"), command=self.clipboard_paste)

        self.menu_format = tk.Menu(self.menubar)
        self.menubar.add_cascade(
            menu=self.menu_format, label=Tr("Format"), state=tk.DISABLED
        )
        self.menubar_selection_change.add(self.menubar.index(tk.END))
        self.menu_format.add_command(label=Tr("Bold"), command=self.bold_add)
        self.menu_format.add_command(label=Tr("Italic"), command=self.italic_add)
        self.menu_format.add_command(label=Tr("Quote"), command=self.quote_add)

        # self.menu_list = tk.Menu(self.menubar)
        # self.menubar.add_cascade(menu=self.menu_list, label=Tr("List"))
        # self.menu_list.add_command(label=Tr("Ordered"),
        #                            command=functools.partial(self.list_add,
        #                                                      ordered=True))
        # self.menu_list.add_command(label=Tr("Unordered"),
        #                            command=functools.partial(self.list_add,
        #                                                      ordered=False))

        self.menubar.add_command(
            label=Tr("Link"), command=self.link_add, state=tk.DISABLED
        )
        self.menubar_selection_change.add(self.menubar.index(tk.END))

    def menubar_file_setup(self):
        self.menu_file.add_command(
            label=Tr("Save"), command=self.save, accelerator="Ctrl-S"
        )
        self.menu_file.add_command(
            label=Tr("Close"), command=self.close, accelerator="Ctrl-Q"
        )

    def view_bind_tags(self, view=None):
        "Configure the tag bindings used in the 'tk.Text' instance."
        view = view or self.view
        super().view_bind_tags(view=view)
        view.tag_bind(constants.BOLD, "<Button-1>", self.bold_remove)
        view.tag_bind(constants.ITALIC, "<Button-1>", self.italic_remove)
        view.tag_bind(constants.QUOTE, "<Button-1>", self.quote_remove)

    def view_bind_keys(self, view=None):
        view = view or self.view
        super().view_bind_keys(view=view)
        view.bind("<Control-x>", self.clipboard_cut)
        view.bind("<Control-X>", self.clipboard_cut)
        view.bind("<Control-v>", self.clipboard_paste)
        view.bind("<Control-V>", self.clipboard_paste)
        view.bind("<<Modified>>", self.handle_modified)
        view.bind("<Button-3>", self.popup_menu)
        view.bind("<<Selection>>", self.selection_change)

    def key_press(self, event):
        "Forbid some key press actions."
        tags = set(self.view.tag_names(tk.INSERT))
        if event.char:
            # For 'Backspace', check the position before.
            if event.keysym == "BackSpace":
                tags = self.view.tag_names(tk.INSERT + "-1c")
            # # Do not allow 'Return' when in list; temporary solution.
            # elif event.keysym == "Return":
            #     for tag in tags:
            #         if tag.startswith(constants.LIST_PREFIX):
            #             return "break"
            # # Do not allow modifying keys from modifying a list item bullet.
            # if constants.LIST_BULLET in tags:
            #     return "break"
            # Do not allow modifying keys from modifying a reference.
            if constants.REFERENCE in tags:
                return "break"
            # Do not allow modifying keys from modifying a footnote reference.
            # XXX This should not be here, since BaseEditor does not handle footnotes.
            if constants.FOOTNOTE_REF in tags:
                return "break"

    def display_title(self):
        "Do not display the title in the text edit area."
        pass

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

    ignore_modified_event = property(
        get_ignore_modified_event, set_ignore_modified_event
    )

    @property
    def is_modified(self):
        return self.view.edit_modified()

    def set_modified(self, event=None):
        self.ignore_modified_event = True
        self.view.edit_modified(True)

    def handle_modified(self, event=None):
        "Return False if no work to be done; else True."
        if self.ignore_modified_event:
            self.ignore_modified_event = False
            return False
        if not self.is_modified:
            return False
        self.menubar.configure(background=constants.MODIFIED_COLOR)
        return True

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
            title=f"{Tr('Remove')} {Tr('bold')}?",
            message=f"{Tr('Really')} {Tr('remove')} {Tr('bold')}?",
        ):
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
            title=f"{Tr('Remove')} {Tr('italic')}?)",
            message=f"{Tr('Really')} {Tr('remove')} {Tr('italic')}?)",
        ):
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
            title=f"{Tr('Remove')} {Tr('quote')}?)",
            message=f"{Tr('Really')} {Tr('remove')} {Tr('quote')}?)",
        ):
            return
        self.view.tag_remove(constants.QUOTE, first, last)
        self.set_modified()

    # def list_add(self, ordered):
    #     data = self.list_create_entry(ordered, 1, True)
    #     if ordered:
    #         data["bullet"] = f"{data['count']}."
    #         data["depth"] = 1
    #     else:
    #         # XXX actual depth needed
    #         data["depth"] = 0
    #         data["bullet"] = constants.LIST_BULLETS[data["depth"]]
    #         data["depth"] += 1
    #     self.view.insert(tk.INSERT, "\n")
    #     first = self.view.index(tk.INSERT)
    #     self.view.insert(tk.INSERT, data["bullet"] + " ", (constants.LIST_BULLET, ))
    #     tag = f"{constants.LIST_ITEM_PREFIX}{data['number']}-{data['count']}"
    #     self.view.tag_configure(tag,
    #                             lmargin1=data["depth"]*constants.LIST_INDENT,
    #                             lmargin2=(data["depth"]+0.5)*constants.LIST_INDENT)
    #     self.view.tag_add(tag, first, tk.INSERT)
    #     self.view.tag_add(data["tag"], first, tk.INSERT)
    #     data["count"] += 1

    # def list_item_add(self, tags):
    #     # XXX item is not added to the correct place, if another has been
    #     # added before in in the same edit session.
    #     depth = 0
    #     for t in tags:
    #         if t.startswith(constants.LIST_ITEM_PREFIX):
    #             n, c = t[len(constants.LIST_ITEM_PREFIX):].split("-")
    #             d = self.lists_lookup[n]
    #             if d["depth"] > depth:
    #                 data = d
    #                 depth = d["depth"]
    #                 count = int(c)
    #     first, last = self.view.tag_nextrange(data["tag"], "1.0")
    #     tags = set(tags)
    #     tags.remove(data["tag"])
    #     self.view.mark_set(tk.INSERT, last)
    #     self.view.insert(tk.INSERT, "\n")
    #     if not data["tight"]:
    #         self.view.insert(tk.INSERT, "\n")
    #     if data["ordered"]:
    #         data["bullet"] = f"{count+1}."
    #     else:
    #         data["bullet"] = data["bullet"]
    #     first = self.view.index(tk.INSERT)
    #     self.view.insert(tk.INSERT, data["bullet"] + " ", (constants.LIST_BULLET, ))
    #     data["count"] += 1
    #     tag = f"{constants.LIST_ITEM_PREFIX}{data['number']}-{data['count']}"
    #     self.view.tag_configure(tag,
    #                             lmargin1=data["depth"]*constants.LIST_INDENT,
    #                             lmargin2=(data["depth"]+0.5)*constants.LIST_INDENT)
    #     # Kludge to make insert point be placed within list tags.
    #     self.view.insert(tk.INSERT, " ")
    #     self.view.tag_add(tag, first, tk.INSERT)
    #     tag = f"{constants.LIST_PREFIX}{data['number']}"
    #     self.view.tag_add(tag, first, tk.INSERT)
    #     for tag in tags:
    #         self.view.tag_add(tag, first, tk.INSERT)
    #     # Kludge to make insert point be placed within list tags.
    #     self.view.mark_set(tk.INSERT, self.view.index(tk.INSERT + "-1c"))

    # def list_item_remove(self, tags):
    #     depth = 0
    #     for t in tags:
    #         if t.startswith(constants.LIST_ITEM_PREFIX):
    #             n, c = t[len(constants.LIST_ITEM_PREFIX):].split("-")
    #             d = self.lists_lookup[n]
    #             d = self.lists_lookup[n]
    #             if d["depth"] > depth:
    #                 tag = t
    #                 data = d
    #                 depth = d["depth"]
    #                 count = int(c)
    #     first, last = self.view.tag_nextrange(tag, "1.0")
    #     # Also remove the newline after the previous line.
    #     first = self.view.index(first + "-1c")
    #     self.view.delete(first, last)

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
            parent=self.toplevel, title="Link URL?", prompt="Give URL for link:"
        )
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

    def clipboard_cut(self, event=None):
        """Cut the current selection into the clipboard.
        Two variants: with formatting for intra-Au use,
        and as characters-only for cross-application use.
        """
        try:
            first, last = self.get_selection()
        except ValueError:
            return
        self.main.clipboard = self.get_dump(first, last)
        self.main.clipboard_chars = self.view.get(first, last)
        self.view.clipboard_clear()
        self.view.clipboard_append(self.main.clipboard_chars)
        self.view.delete(first, last)
        return "break"  # When called by keyboard event.

    def clipboard_paste(self, event=None):
        """Paste in contents from the clipboard.
        If the system clipboard text is the same as that stored in
        as characters only in this app, then use the intra-Au clipboard,
        which contains formatting.
        Otherwise the system clipboard text.
        """
        chars = self.view.clipboard_get()
        if chars == self.main.clipboard_chars:
            first = self.view.index(tk.INSERT)
            tags = {}
            self.skip_text = False
            for entry in self.main.clipboard:
                try:
                    method = getattr(self, f"undump_{entry[0]}")
                except AttributeError:
                    ic("Could not undump", entry)
                    raise
                method(entry, tags)
            self.view.tag_remove(tk.SEL, first, tk.INSERT)
        else:
            self.view.insert(tk.INSERT, chars)
        return "break"  # When called by keyboard event.

    def undump_text(self, entry, tags):
        if self.skip_text:
            return
        self.view.insert(tk.INSERT, entry[1])

    def undump_tagon(self, entry, tags):
        tags[entry[1]] = dict(first=self.view.index(tk.INSERT))

    def undump_tagoff(self, entry, tags):
        try:
            data = tags[entry[1]]
        except KeyError:
            ic("No tagon for", entry)
            raise
        if entry[1].startswith(constants.LINK_PREFIX):
            self.link_create(
                entry[2], entry[3], data["first"], self.view.index(tk.INSERT)
            )
        # XXX This should not be here, since BaseEditor does not handle footnotes.
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

    def popup_menu(self, event):
        "Display a popup menu according to the current state."
        menu = tk.Menu(self.view)
        try:
            first, last = self.get_selection(allow_boundary=True)
        except ValueError:  # No current selection.
            menu.add_command(label=Tr("Paste"), command=self.clipboard_paste)
            # tags = self.view.tag_names(tk.INSERT + "-1c")
            # for tag in tags:
            #     if tag.startswith(constants.LIST_ITEM_PREFIX):
            #         menu.add_command(label=Tr("Add list item"),
            #                          command=functools.partial(self.list_item_add,
            #                                                    tags=tags))
            #         menu.add_command(label=Tr("Remove list item"),
            #                          command=functools.partial(self.list_item_remove,
            #                                                    tags=tags))
            #         break
            # menu.add_command(label=Tr("Add ordered list"),
            #                  command=functools.partial(self.list_add, ordered=True))
            # menu.add_command(label=Tr("Add unordered list"),
            #                  command=functools.partial(self.list_add, ordered=False))
        else:  # There is current selection.
            if not self.selection_contains_boundary(first, last, complain=False):
                menu.add_command(label=Tr("Copy"), command=self.clipboard_copy)
                menu.add_command(label=Tr("Cut"), command=self.clipboard_cut)
                menu.add_separator()
                menu.add_command(label=Tr("Bold"), command=self.bold_add)
                menu.add_command(label=Tr("Italic"), command=self.italic_add)
                menu.add_command(label=Tr("Quote"), command=self.quote_add)
                menu.add_separator()
                menu.add_command(label=Tr("Link"), command=self.link_add)
                self.popup_menu_add_selected(menu)
        menu.tk_popup(event.x_root, event.y_root)

    def popup_menu_add_selected(self, menu):
        "Add items to the popup menu for when text is selected."
        pass

    def save(self, event=None):
        """Save the current contents to the text file.
        Get the main window to refresh the contents of the text view.
        """
        if not self.is_modified:
            return
        self.save_prepare()
        for item in self.view.dump("1.0", tk.END):
            try:
                method = getattr(self, f"markdown_{item[0]}")
            except AttributeError:
                ic("Could not markdown item", item)
            else:
                method(item)
        self.save_postdump()
        self.text.write(self.outfile.getvalue())
        self.menubar.configure(background=self.original_menubar_background)
        self.ignore_modified_event = True
        self.view.edit_modified(False)
        self.save_finalize()

    def save_prepare(self):
        "Prepare for saving; before doing dump-to-Markdown."
        self.outfile_stack = [io.StringIO()]
        self.line_indents = []
        self.line_indented = False
        self.skip_text = False
        # self.list_stack = []

    def save_postdump(self):
        "Perform save operations after having done dump-to-Markdown."
        pass

    def save_finalize(self):
        "Perform final save operations."
        pass

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
            # if item[1].startswith(constants.LIST_PREFIX):
            #     self.markdown_start_list(item[1])
            pass
        else:
            method(item)

    def markdown_tagoff(self, item):
        try:
            method = getattr(self, f"markdown_tagoff_{item[1]}")
        except AttributeError:
            # if item[1].startswith(constants.LIST_PREFIX):
            #     self.markdown_finish_list(item[1])
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

    def markdown_tagon_thematic_break(self, item):
        self.skip_text = True

    def markdown_tagoff_thematic_break(self, item):
        self.save_characters("---")
        self.save_line_indent(force=True)
        self.outfile.write("\n")
        self.skip_text = False

    # def markdown_start_list(self, tag):
    #     data = self.lists_lookup[tag]
    #     data["count"] = data["start"]
    #     if len(self.list_stack):
    #         self.line_indents.append("    ")
    #     self.list_stack.append(data)

    # def markdown_finish_list(self, tag):
    #     self.list_stack.pop()
    #     if len(self.list_stack):
    #         self.line_indents.pop()

    # def markdown_tagon_list_bullet(self, item):
    #     data = self.list_stack[-1]
    #     if data["ordered"]:
    #         self.save_characters(f"{data['count']}. ")
    #         data["count"] += 1
    #     else:
    #         self.save_characters("- ")
    #     self.skip_text = True

    # def markdown_tagoff_list_bullet(self, item):
    #     self.skip_text = False

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

    def close(self, event=None, force=False):
        if self.is_modified and not force:
            if not tk.messagebox.askokcancel(
                parent=self.toplevel,
                title=Tr("Close?"),
                message=f"{Tr('Modifications will not be saved.')} {Tr('Really')} {Tr('close?')}",
            ):
                return "break"  # When called by keyboard event.
        self.ignore_modified_event = True
        self.view.edit_modified(False)
        self.close_finalize()
        self.toplevel.destroy()
        return "break"  # When called by keyboard event.

    def close_finalize(self):
        "Perform action at window closing time."
        pass


class LinkEdit(tk.simpledialog.Dialog):
    "Dialog window for editing the URL and title for a link."

    def __init__(self, toplevel, link):
        self.link = link
        self.result = None
        super().__init__(toplevel, title=Tr("Edit link"))

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
        self.result = dict(url=self.url_entry.get(), title=self.title_entry.get())

    def buttonbox(self):
        box = tk.Frame(self)
        w = tk.ttk.Button(
            box, text=Tr("OK"), width=10, command=self.ok, default=tk.ACTIVE
        )
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
