"Base text editor."

from icecream import ic

import io
import webbrowser

import tkinter as tk
import tkinter.ttk
import tkinter.simpledialog
import tkinter.messagebox

import constants
import utils

from utils import Tr

from renderer import Renderer
from text_viewer import TextViewer


class EditorRenderer(Renderer):
    "Rendering for the base text editor."

    def bind_tags(self):
        super().bind_tags()
        self.view.tag_bind(constants.BOLD, "<Button-1>", self.bold_remove)
        self.view.tag_bind(constants.ITALIC, "<Button-1>", self.italic_remove)
        self.view.tag_bind(constants.QUOTE, "<Button-1>", self.quote_remove)
        self.view.tag_bind(constants.FOOTNOTE_REF, "<Button-1>", self.footnote_remove)

    def bind_events(self):
        super().bind_events()
        self.view.bind("<Control-x>", self.clipboard_cut)
        self.view.bind("<Control-X>", self.clipboard_cut)
        self.view.bind("<Control-v>", self.clipboard_paste)
        self.view.bind("<Control-V>", self.clipboard_paste)
        self.view.bind("<<Modified>>", self.handle_modified)
        self.view.bind("<Button-3>", self.popup_menu)
        self.view.bind("<<Selection>>", self.viewer.selection_changed)

    def key_press(self, event):
        "Forbid some key press actions."
        if not event.char:
            return
        tags = set(self.view.tag_names(tk.INSERT))
        # For 'Backspace', check the position before.
        if event.keysym == "BackSpace":
            tags = self.view.tag_names(tk.INSERT + "-1c")
        # Do not encroach on reference or footnote reference.
        if constants.REFERENCE in tags:
            return "break"
        if constants.FOOTNOTE_REF in tags:
            return "break"

    def display_initialize(self):
        super().display_initialize()
        self.ignore_modified_event = True

    def display_title(self):
        "Do not display the title in the text edit area."
        pass

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
        self.viewer.menubar.configure(background=constants.MODIFIED_COLOR)
        return True

    def popup_menu(self, event):
        "Display a popup menu according to the current state."
        menu = tk.Menu(self.view)
        try:
            first, last = self.get_selection(allow_boundary=True)
        except ValueError:  # No current selection.
            menu.add_command(label=Tr("Paste"), command=self.clipboard_paste)
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

    def clipboard_cut(self, event=None):
        pass

    def clipboard_paste(self, event=None):
        pass

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

    def link_action(self, event):
        "Allow viewing, editing and opening the link."
        link = self.renderer.get_link()
        if not link:
            return
        edit = EditLink(self.view, link)
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

    def indexed_add(self):
        try:
            first, last = self.get_selection()
        except ValueError:
            return
        term = self.view.get(first, last)
        canonical = tk.simpledialog.askstring(
            parent=self.toplevel,
            title="Canonical?",
            prompt="Give canonical term:",
            initialvalue=term,
        )
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
            message=f"Really remove indexing for '{term}'?",
        ):
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
        refid = self.get_refid()
        if not refid:
            return
        if not tk.messagebox.askokcancel(
            parent=self.toplevel,
            title="Remove reference?",
            message=f"Really remove reference '{refid}'?",
        ):
            return
        tag = f"{constants.REFERENCE_PREFIX}{refid}"
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
        self.view.insert(self.view.tag_nextrange(tag, "1.0")[0], "\n", (tag,))
        tag = constants.FOOTNOTE_REF_PREFIX + label
        self.footnotes[label] = dict(label=label, tag=tag)
        self.view.insert(first, f"^{label}", (constants.FOOTNOTE_REF, (tag,)))

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
                label = tag[len(constants.FOOTNOTE_REF_PREFIX) :]
                break
        else:
            return
        tag = constants.FOOTNOTE_REF_PREFIX + label
        first, last = self.view.tag_nextrange(tag, "1.0")
        if not tk.messagebox.askokcancel(
            parent=self.toplevel,
            title="Remove footnote?",
            message=f"Really remove footnote (text will remain)?",
        ):
            return
        self.view.tag_remove(constants.FOOTNOTE_REF, first, last)
        self.view.tag_delete(tag)
        self.view.delete(first, self.view.index(last + "+1c"))  # Remove newline.
        tag = constants.FOOTNOTE_DEF_PREFIX + label
        first, last = self.view.tag_nextrange(tag, "1.0")
        self.view.tag_remove(constants.FOOTNOTE_DEF, first, last)
        self.view.tag_delete(tag)
        self.view.tag_add(tk.SEL, first, last)

    def clipboard_cut(self, event=None):
        """Cut the current selection into the clipboard.
        Two variants: dump containing formatting for intra-Au use,
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
        The Au clipboard dump contains formatting, while the system clipboard
        only has characters. If the character contents of the two is the same,
        then use the Au clipboard, otherwise the system clipboard.
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


class Editor(TextViewer):
    "Base text editor class."

    def __init__(self, main, text):
        self.main = main
        self.text = text
        self.toplevel = tk.Toplevel(self.main.root)
        self.toplevel.title(f"{Tr('Edit')}: {self.text.fullname}")
        self.toplevel.bind("<Control-s>", self.save)
        self.toplevel.bind("<Control-S>", self.save)
        self.toplevel.bind("<Control-q>", self.close)
        self.toplevel.bind("<Control-Q>", self.close)
        self.toplevel.protocol("WM_DELETE_WINDOW", self.close)
        self.menubar = tk.Menu(self.toplevel, background="gold")
        self.toplevel["menu"] = self.menubar
        self.view_create(self.toplevel)
        self.renderer = EditorRenderer(main, self, self.view)
        self.menubar_setup()

    def menubar_setup(self):
        self.original_menubar_background = self.menubar.cget("background")
        self.menubar_changed_by_selection = set()
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
        self.menu_edit.add_command(
            label=Tr("Copy"), command=self.renderer.clipboard_copy
        )
        self.menu_edit.add_command(
            label=Tr("Cut"), command=self.renderer.clipboard_cut
        )
        self.menu_edit.add_command(
            label=Tr("Paste"), command=self.renderer.clipboard_paste
        )

        self.menu_format = tk.Menu(self.menubar)
        self.menubar.add_cascade(
            menu=self.menu_format, label=Tr("Format"), state=tk.DISABLED
        )
        self.menubar_changed_by_selection.add(self.menubar.index(tk.END))
        self.menu_format.add_command(label=Tr("Bold"), command=self.renderer.bold_add)
        self.menu_format.add_command(
            label=Tr("Italic"), command=self.renderer.italic_add
        )
        self.menu_format.add_command(label=Tr("Quote"), command=self.renderer.quote_add)

        self.menubar.add_command(
            label=Tr("Link"), command=self.renderer.link_add, state=tk.DISABLED
        )
        self.menubar_changed_by_selection.add(self.menubar.index(tk.END))

    def menubar_file_setup(self):
        self.menu_file.add_command(
            label=Tr("Save"), command=self.save, accelerator="Ctrl-S"
        )
        self.menu_file.add_command(
            label=Tr("Close"), command=self.close, accelerator="Ctrl-Q"
        )

    def selection_changed(self, event):
        "Selection changed; normalize or disable menu items accordingly."
        try:
            self.view.index(tk.SEL_FIRST)
        except tk.TclError:
            for pos in self.menubar_changed_by_selection:
                self.menubar.entryconfigure(pos, state=tk.DISABLED)
        else:
            for pos in self.menubar_changed_by_selection:
                self.menubar.entryconfigure(pos, state=tk.NORMAL)

    def undump_text(self, entry, tags):
        if self.skip_text:
            return
        self.view.insert(tk.INSERT, entry[1])

    def undump_tagon(self, entry, tags):
        tags[entry[1]] = dict(first=self.view.index(tk.INSERT))
        if entry[1].startswith(constants.FOOTNOTE_REF_PREFIX):

            tags[entry[1]]["label"] = self.get_new_footnote_label()
            self.skip_text = True
        elif entry[1].startswith(constants.FOOTNOTE_DEF_PREFIX):
            tag = (
                constants.FOOTNOTE_REF_PREFIX
                + entry[1][len(constants.FOOTNOTE_DEF_PREFIX) :]
            )
            tags[entry[1]]["label"] = tags[tag]["label"]

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
        elif entry[1].startswith(constants.FOOTNOTE_REF_PREFIX):
            label = data["label"]
            tag = constants.FOOTNOTE_REF_PREFIX + label
            self.view.insert(tk.INSERT, f"^{label}", (constants.FOOTNOTE_REF, tag))
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
        if not self.renderer.is_modified:
            return
        self.save_prepare()
        for item in self.view.dump("1.0", tk.END):
            try:
                method = getattr(self, f"markdown_{item[0]}")
            except AttributeError:
                ic("Could not markdown item", item)
            else:
                method(item)
        self.save_after_dump()
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

    def markdown_tagon_link(self, item):
        for tag in self.view.tag_names(item[2]):
            if tag.startswith(constants.LINK_PREFIX):
                self.current_link_tag = tag
                break
        self.save_characters("[")

    def markdown_tagoff_link(self, item):
        link = self.renderer.get_link(self.current_link_tag)
        if link["title"]:
            self.save_characters(f"""]({link['url']} "{link['title']}")""")
        else:
            self.save_characters(f"]({link['url']})")
        self.current_link_tag = None

    def close(self, event=None, force=False):
        if self.renderer.is_modified and not force:
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


class EditLink(tk.simpledialog.Dialog):
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
