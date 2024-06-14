"Base text editor."

from icecream import ic

import functools
import io
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


class Editor(TextViewer):
    "Base text editor class."

    def __init__(self, main, text):
        self.toplevel_create(main, text)
        super().__init__(self.toplevel, main, text)
        self.menubar_create()

    def toplevel_create(self, main, text):
        self.toplevel = tk.Toplevel(main.root)
        self.toplevel.title(f"{Tr('Edit')}: {text.fullname}")
        self.toplevel.bind("<Control-s>", self.save)
        self.toplevel.bind("<Control-S>", self.save)
        self.toplevel.bind("<Control-q>", self.close)
        self.toplevel.bind("<Control-Q>", self.close)
        self.toplevel.protocol("WM_DELETE_WINDOW", self.close)

    def menubar_create(self):
        self.menubar = tk.Menu(self.toplevel, background="gold")
        self.toplevel["menu"] = self.menubar
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
        self.menu_file.add_command(
            label=Tr("Save"), command=self.save, accelerator="Ctrl-S"
        )
        self.menu_file.add_command(
            label=Tr("Close"), command=self.close, accelerator="Ctrl-Q"
        )

        self.menu_edit = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_edit, label=Tr("Edit"))
        self.menu_edit.add_command(label=Tr("Copy"), command=self.clipboard_copy)
        self.menu_edit.add_command(label=Tr("Cut"), command=self.clipboard_cut)
        self.menu_edit.add_command(label=Tr("Paste"), command=self.clipboard_paste)
        self.menu_edit.add_separator()
        self.menu_edit.add_command(
            label=Tr("New ordered list"), command=self.list_ordered_add
        )
        self.menu_edit.add_command(
            label=Tr("New unordered list"), command=self.list_unordered_add
        )

        self.menu_format = tk.Menu(self.menubar)
        self.menubar.add_cascade(
            menu=self.menu_format, label=Tr("Format"), state=tk.DISABLED
        )
        self.menubar_changed_by_selection.add(self.menubar.index(tk.END))
        self.menu_format.add_command(label=Tr("Bold"), command=self.bold_add)
        self.menu_format.add_command(label=Tr("Italic"), command=self.italic_add)
        self.menu_format.add_command(label=Tr("Code"), command=self.code_span_add)
        self.menu_format.add_separator()
        self.menu_format.add_command(label=Tr("Quote"), command=self.quote_add)
        self.menu_format.add_command(
            label=Tr("Code block"), command=self.code_block_add
        )
        self.menu_format.add_command(
            label=Tr("Fenced code"), command=self.fenced_code_add
        )

        self.menubar.add_command(
            label=Tr("Link"), command=self.link_add, state=tk.DISABLED
        )
        self.menubar_changed_by_selection.add(self.menubar.index(tk.END))

    def bind_events(self):
        super().bind_events()
        self.view.bind("<Control-x>", self.clipboard_cut)
        self.view.bind("<Control-X>", self.clipboard_cut)
        self.view.bind("<Control-v>", self.clipboard_paste)
        self.view.bind("<Control-V>", self.clipboard_paste)
        self.view.bind("<Control-space>", self.select)
        self.view.bind("<<Modified>>", self.handle_modified)
        self.view.bind("<<Selection>>", self.selection_changed)

    def key_press(self, event):
        "Special actions for some keys."
        if not event.char:
            return
        # For 'Backspace', check the position before.
        if event.keysym == "BackSpace":
            tags = self.view.tag_names(tk.INSERT + "-1c")
        else:
            tags = set(self.view.tag_names(tk.INSERT))
        # Do not encroach on reference or footnote reference.
        if constants.REFERENCE in tags:
            return "break"
        if constants.FOOTNOTE_REF in tags:
            return "break"
        # Special 'Return' handling, unless used with 'Control'.
        if (event.keysym == "Return" and
            not (event.state & constants.EVENT_STATE_CONTROL)):
            # Add list item if 'Return' within list.
            list_item_tag = self.get_list_item_tag()
            if list_item_tag:
                self.list_item_add(list_item_tag=list_item_tag)
                return "break"

    def display_heading(self):
        "Do not display the heading in the text edit area."
        pass

    def get_modified(self):
        return self.view.edit_modified()

    def set_modified(self, yes):
        if not isinstance(yes, bool):
            raise ValueError("invalid value for 'modified'; must be bool")
        self.view.edit_modified(yes)

    modified = property(get_modified, set_modified)

    def handle_modified(self, event=None):
        if self.view.edit_modified():
            self.menubar.configure(background=constants.MODIFIED_COLOR)
        else:
            self.menubar.configure(background=self.original_menubar_background)

    def get_popup_menu(self, event=None):
        "Create a popup menu according to the current state."
        menu = tk.Menu(self.view)
        try:
            first, last = self.get_selection()
        except ValueError:  # No current selection.
            tags = self.view.tag_names(tk.CURRENT)
            if constants.BOLD in tags:
                menu.add_command(label=Tr("Remove bold"),
                                 command=self.bold_remove)
            if constants.ITALIC in tags:
                menu.add_command(label=Tr("Remove italic"),
                                 command=self.italic_remove)
            if constants.QUOTE in tags:
                menu.add_command(label=Tr("Remove quote"),
                                 command=self.quote_remove)
            if constants.CODE_SPAN in tags:
                menu.add_command(label=Tr("Remove code span"),
                                 command=self.code_span_remove)
            if constants.QUOTE in tags:
                menu.add_command(label=Tr("Remove quote"),
                                 command=self.quote_remove)
            if constants.CODE_BLOCK in tags:
                menu.add_command(label=Tr("Remove code block"),
                                 command=self.code_block_remove)
            if constants.FENCED_CODE in tags:
                menu.add_command(label=Tr("Remove fenced code"),
                                 command=self.fenced_code_remove)
            term = self.get_indexed()
            if term:
                menu.add_command(label=f"{Tr('Remove indexed')} '{term}'",
                                 command=self.indexed_remove)
            for tag in tags:
                if tag.startswith(constants.FOOTNOTE_REF_PREFIX):
                    menu.add_command(label=Tr("Remove footnote"),
                                     command=self.footnote_remove)
                    break
            reference = self.get_reference()
            if reference:
                menu.add_command(label=Tr("Remove reference"),
                                 command=self.reference_remove)

            if menu.index(tk.END) is not None:
                menu.add_separator()
            list_item_tag = self.get_list_item_tag()
            if list_item_tag:
                menu.add_command(
                    label=Tr("Add list item"),
                    command=functools.partial(
                        self.list_item_add, list_item_tag=list_item_tag
                    ),
                )
                menu.add_command(
                    label=Tr("Remove list item"),
                    command=functools.partial(
                        self.list_item_remove, list_item_tag=list_item_tag
                    ),
                )
            menu.add_command(
                label=Tr("New ordered list"), command=self.list_ordered_add
            )
            menu.add_command(
                label=Tr("New unordered list"), command=self.list_unordered_add
            )
            menu.add_separator()
            menu.add_command(label=Tr("Paste"), command=self.clipboard_paste)
        else:  # There is current selection.
            try:
                self.check_broken_selection(first, last)
            except ValueError:
                pass
            else:
                menu.add_command(label=Tr("Copy"), command=self.clipboard_copy)
                menu.add_command(label=Tr("Cut"), command=self.clipboard_cut)
                menu.add_separator()
                menu.add_command(label=Tr("Bold"), command=self.bold_add)
                menu.add_command(label=Tr("Italic"), command=self.italic_add)
                menu.add_command(label=Tr("Code"), command=self.code_span_add)
                menu.add_separator()
                menu.add_command(label=Tr("Quote"), command=self.quote_add)
                menu.add_command(label=Tr("Code block"), command=self.code_block_add)
                menu.add_command(label=Tr("Fenced code"), command=self.fenced_code_add)
                menu.add_separator()
                menu.add_command(label=Tr("Link"), command=self.link_add)
        return menu

    def clipboard_cut(self, event=None):
        pass

    def clipboard_paste(self, event=None):
        pass

    def bold_add(self):
        try:
            first, last = self.get_selection()
            self.check_broken_selection(first, last, showerror=True)
        except ValueError:
            return
        first, last = self.selection_strip_whitespace(first, last)
        self.view.tag_add(constants.BOLD, first, last)
        self.modified = True

    def bold_remove(self):
        try:
            first, last = self.view.tag_prevrange(constants.BOLD, tk.CURRENT)
        except ValueError:
            first, last = self.view.tag_nextrange(constants.BOLD, tk.CURRENT)
        self.view.tag_remove(constants.BOLD, first, last)
        self.modified = True

    def italic_add(self):
        try:
            first, last = self.get_selection()
            self.check_broken_selection(first, last, showerror=True)
        except ValueError:
            return
        first, last = self.selection_strip_whitespace(first, last)
        self.view.tag_add(constants.ITALIC, first, last)
        self.modified = True

    def italic_remove(self):
        try:
            first, last = self.view.tag_prevrange(constants.ITALIC, tk.CURRENT)
        except ValueError:
            first, last = self.view.tag_nextrange(constants.ITALIC, tk.CURRENT)
        self.view.tag_remove(constants.ITALIC, first, last)
        self.modified = True

    def code_span_add(self):
        try:
            first, last = self.get_selection()
            self.check_broken_selection(first, last, showerror=True)
        except ValueError:
            return
        self.view.tag_add(constants.CODE_SPAN, first, last)
        self.modified = True

    def code_span_remove(self):
        try:
            first, last = self.view.tag_prevrange(constants.CODE_SPAN, tk.CURRENT)
        except ValueError:
            first, last = self.view.tag_nextrange(constants.CODE_SPAN, tk.CURRENT)
        self.view.tag_remove(constants.CODE_SPAN, first, last)
        self.modified = True

    def quote_add(self):
        try:
            first, last = self.get_selection()
            self.check_broken_selection(first, last, showerror=True)
        except ValueError:
            return
        self.view.tag_add(constants.QUOTE, first, last)
        self.make_paragraph(first, last)
        self.modified = True

    def make_paragraph(self, first, last):
        "Make the selected region into a proper paragraph, if not already."
        if "\n\n" not in self.view.get(last, last + "+2c"):
            self.view.insert(last, "\n\n")
        if "\n\n" not in self.view.get(first + "-2c", first):
            self.view.insert(first, "\n\n")

    def quote_remove(self):
        try:
            first, last = self.view.tag_prevrange(constants.QUOTE, tk.CURRENT)
        except ValueError:
            first, last = self.view.tag_nextrange(constants.QUOTE, tk.CURRENT)
        self.view.tag_remove(constants.QUOTE, first, last)
        self.modified = True

    def code_block_add(self):
        try:
            first, last = self.get_selection()
            self.check_broken_selection(first, last, showerror=True)
        except ValueError:
            return
        self.view.tag_add(constants.CODE_BLOCK, first, last)
        self.make_paragraph(first, last)
        self.modified = True

    def code_block_remove(self):
        try:
            first, last = self.view.tag_prevrange(constants.CODE_BLOCK, tk.CURRENT)
        except ValueError:
            first, last = self.view.tag_nextrange(constants.CODE_BLOCK, tk.CURRENT)
        self.view.tag_remove(constants.CODE_BLOCK, first, last)
        self.modified = True

    def fenced_code_add(self):
        try:
            first, last = self.get_selection()
            self.check_broken_selection(first, last, showerror=True)
        except ValueError:
            return
        self.view.tag_add(constants.FENCED_CODE, first, last)
        self.make_paragraph(first, last)
        self.modified = True

    def fenced_code_remove(self):
        try:
            first, last = self.view.tag_prevrange(constants.FENCED_CODE, tk.CURRENT)
        except ValueError:
            first, last = self.view.tag_nextrange(constants.FENCED_CODE, tk.CURRENT)
        self.view.tag_remove(constants.FENCED_CODE, first, last)
        self.modified = True

    def list_ordered_add(self, event=None):
        raise NotImplementedError

    def list_unordered_add(self, event=None):
        raise NotImplementedError

    def list_item_add(self, event=None, list_item_tag=None):
        data = self.list_lookup[list_item_tag]
        data["count"] += 1
        self.view.mark_set(
            tk.INSERT, self.view.tag_prevrange(list_item_tag, tk.CURRENT)[1]
        )
        outer_tags = [
            t
            for t in self.view.tag_names(tk.INSERT + "-1c")
            if int(t.split("-")[1]) != data["number"]
        ]
        tags = [data["bullet_tag"], data["list_tag"]]
        if data["ordered"]:
            self.view.insert(
                tk.INSERT, f"{data['start'] + data['count'] - 1}. ", tags + outer_tags
            )
        else:
            self.view.insert(tk.INSERT, f"{data['bullet']}  ", tags + outer_tags)
        item_tag = f"{data['item_tag_prefix']}{data['count']}"
        self.list_lookup[item_tag] = data
        indent = constants.LIST_INDENT * len(self.list_stack)
        self.view.tag_configure(item_tag, lmargin1=indent, lmargin2=indent)
        first = self.view.index(tk.INSERT)
        self.view.insert(tk.INSERT, " \n", (item_tag,))
        if not data["tight"]:
            self.view.insert(tk.INSERT, "\n", (item_tag,))
        self.view.tag_add(item_tag, first, tk.INSERT)
        self.view.tag_add(data["list_tag"], first, tk.INSERT)
        for tag in outer_tags:
            self.view.tag_add(tag, first, tk.INSERT)
        self.view.mark_set(tk.INSERT, first)

    def list_item_remove(self, event=None, list_item_tag=None):
        if not tk.messagebox.askokcancel(
            parent=self.toplevel,
            title=f"{Tr('Remove list item?')}",
            message=f"{Tr('Really remove list item and all its contents?')}",
        ):
            return
        data = self.list_lookup[list_item_tag]
        first = self.view.tag_prevrange(data["bullet_tag"], tk.CURRENT)[0]
        try:
            last = self.view.tag_prevrange(list_item_tag, tk.CURRENT)[1]
        except IndexError:  # Not sure why this is needed.
            last = self.view.tag_nextrange(list_item_tag, tk.CURRENT)[1]
        self.view.delete(first, last)

    def link_add(self):
        try:
            first, last = self.get_selection()
            self.check_broken_selection(first, last, showerror=True)
        except ValueError:
            return
        first, last = self.selection_strip_whitespace(first, last)
        for entry in self.get_dump(first, last):
            if entry[0] in ("tagon", "tagoff"):
                tk.messagebox.showerror(
                    parent=self.toplevel,
                    title=Tr("Formatting disallowed"),
                    message=Tr("Formatting not allowed within link text."),
                )
                return
        url = tk.simpledialog.askstring(
            parent=self.toplevel, title=Tr("Link URL?"), prompt=Tr("Give URL for link:")
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
        self.modified = True

    def link_action(self, event):
        "Allow viewing, editing and opening the link."
        link = self.get_link()
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
        self.modified = True

    def indexed_add(self):
        try:
            first, last = self.get_selection()
            self.check_broken_selection(first, last, showerror=True)
        except ValueError:
            return
        first, last = self.selection_strip_whitespace(first, last)
        term = self.view.get(first, last)
        canonical = tk.simpledialog.askstring(
            parent=self.toplevel,
            title=Tr("Canonical?"),
            prompt=Tr("Give canonical term:"),
            initialvalue=term,
        )
        if canonical is None:
            return
        canonical = canonical.strip()
        if not canonical:
            canonical = term
        self.view.tag_add(constants.INDEXED, first, last)
        self.view.tag_add(constants.INDEXED_PREFIX + canonical, first, last)
        self.modified = True

    def indexed_remove(self):
        term = self.get_indexed()
        if not term:
            return
        first, last = self.view.tag_prevrange(constants.INDEXED, tk.CURRENT)
        self.view.tag_remove(constants.INDEXED, first, last)
        self.view.tag_remove(f"{constants.INDEXED_PREFIX}{term}", first, last)
        self.modified = True

    def indexed_action(self, event):
        "Edit the indexing of the term."
        term = self.get_indexed()
        if not term:
            return
        tag = constants.INDEXED_PREFIX + term
        first, last = self.view.tag_prevrange(tag, tk.CURRENT)
        edit = EditIndexed(self.main, self.view, term)
        if edit.result is None or edit.result == term:
            return
        self.view.tag_remove(tag, first, last)
        if edit.result:
            self.view.tag_add(constants.INDEXED_PREFIX + edit.result, first, last)
        else:
            self.view.tag_remove(constants.INDEXED, first, last)
        self.modified = True

    def reference_add(self):
        add = AddReference(self.view, self.main.references_viewer.reference_texts)
        if not add.result:
            return
        tag = (constants.REFERENCE_PREFIX + add.result).replace(" ", "_")
        tags = (constants.REFERENCE, tag) + self.view.tag_names(tk.INSERT)
        self.view.insert(tk.INSERT, add.result, tags)

    def reference_remove(self):
        reference = self.get_reference()
        if not reference:
            return
        tag = f"{constants.REFERENCE_PREFIX}{reference}".replace(" ", "_")
        first, last = self.view.tag_prevrange(tag, tk.CURRENT)
        self.view.delete(first, last)
        self.modified = True

    def footnote_toggle(self, event=None):
        pass

    def footnote_add(self):
        try:
            first, last = self.get_selection()
            self.check_broken_selection(first, last, showerror=True)
        except ValueError:
            return
        label = self.get_new_footnote_label()
        tag = constants.FOOTNOTE_DEF_PREFIX + label
        self.tag_elide(tag)
        if (
            self.view.get(last + "-1c", last) != "\n"
            and self.view.get(last, last + "+1c") != "\n"
        ):
            self.view.insert(last, "\n")
            last = self.view.index(last + "+1c")
        self.view.tag_add(constants.FOOTNOTE_DEF, first, last)
        self.view.tag_add(tag, first, last)
        tag = constants.FOOTNOTE_REF_PREFIX + label
        self.footnotes[label] = dict(label=label, tag=tag)
        self.view.insert(first, f"^{label}", (constants.FOOTNOTE_REF, (tag,)))

    def get_new_footnote_label(self):
        "Return the label (str) to use for a new footnote."
        try:
            return str(max([int(label) for label in self.footnotes]) + 1)
        except ValueError:
            return "1"

    def footnote_remove(self):
        tags = self.view.tag_names(tk.CURRENT)
        for tag in tags:
            if tag.startswith(constants.FOOTNOTE_REF_PREFIX):
                label = tag[len(constants.FOOTNOTE_REF_PREFIX) :]
                break
        else:
            return
        tag = constants.FOOTNOTE_REF_PREFIX + label
        first, last = self.view.tag_nextrange(tag, "1.0")
        self.view.tag_remove(constants.FOOTNOTE_REF, first, last)
        self.view.tag_delete(tag)
        self.view.delete(first, last)
        tag = constants.FOOTNOTE_DEF_PREFIX + label
        first, last = self.view.tag_nextrange(tag, "1.0")
        self.view.tag_remove(constants.FOOTNOTE_DEF, first, last)
        self.view.tag_delete(tag)
        self.view.tag_add(tk.SEL, first, last)

    def tag_elide(self, tag):
        pass

    def tag_not_elide(self, tag):
        pass

    def clipboard_cut(self, event=None):
        """Cut the current selection into the clipboard.
        Two variants: dump containing formatting for intra-Au use,
        and as characters-only for cross-application use.
        """
        try:
            first, last = self.get_selection()
            self.check_broken_selection(first, last, showerror=True)
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

    def select(self, event):
        pos = self.view.index(tk.INSERT)
        first = pos
        while True:
            prev = self.view.index(first + "-1c")
            if self.view.get(prev) in string.whitespace:
                break
            first = prev
        last = pos
        while True:
            next = self.view.index(last + "+1c")
            char = self.view.get(next)
            last = next
            if char in string.whitespace or char == ".":
                break
        self.view.tag_add(tk.SEL, first, last)

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
            self.tag_elide(tag)
            self.view.tag_add(tag, data["first"], tk.INSERT)
        else:
            self.view.tag_add(entry[1], data["first"], self.view.index(tk.INSERT))

    def undump_mark(self, entry, tags):
        self.view.mark_set(entry[1], tk.INSERT)

    def save(self, event=None):
        """Save the current contents to the text file.
        Get the main window to refresh the contents of the text view.
        """
        if not self.modified:
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
        self.modified = False
        self.save_finalize()

    def save_prepare(self):
        "Prepare for saving; before doing dump-to-Markdown."
        self.outfile_stack = [io.StringIO()]
        self.line_indents = []
        self.line_indented = False
        self.skip_text = False

    def save_after_dump(self):
        "Perform save operations after having done dump-to-Markdown."
        pass

    def save_finalize(self):
        "Perform final save operations."
        pass

    @property
    def outfile(self):
        return self.outfile_stack[-1]

    def write_line_indent(self, force=False):
        if self.line_indented and not force:
            return
        self.outfile.write("".join(self.line_indents))
        self.line_indented = True

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
                self.line_indented = False
            if segments[-1]:
                self.write_line_indent()
                self.outfile.write(segments[-1])
                self.outfile.write("\n")
                self.line_indented = False

    def markdown_text(self, item):
        if self.skip_text:
            return
        self.write_characters(item[1])

    def markdown_mark(self, item):
        pass

    def markdown_tagon(self, item):
        try:
            method = getattr(self, f"markdown_tagon_{item[1]}")
        except AttributeError:
            if item[1].startswith(constants.LIST_ITEM_PREFIX):
                data = self.list_lookup[item[1]]
                self.line_indents.append(data["level"] * "   ")
                self.line_indented = True
        else:
            method(item)

    def markdown_tagoff(self, item):
        try:
            method = getattr(self, f"markdown_tagoff_{item[1]}")
        except AttributeError:
            if item[1].startswith(constants.LIST_ITEM_PREFIX):
                self.line_indents.pop()
        else:
            method(item)

    def markdown_tagon_italic(self, item):
        self.write_characters("*")

    def markdown_tagoff_italic(self, item):
        self.write_characters("*")

    def markdown_tagon_bold(self, item):
        self.write_characters("**")

    def markdown_tagoff_bold(self, item):
        self.write_characters("**")

    def markdown_tagon_code_span(self, item):
        self.write_characters("`")

    def markdown_tagoff_code_span(self, item):
        self.write_characters("`")

    def markdown_tagon_quote(self, item):
        self.line_indents.append("> ")

    def markdown_tagoff_quote(self, item):
        self.line_indents.pop()

    def markdown_tagon_code_block(self, item):
        self.line_indents.append("    ")

    def markdown_tagoff_code_block(self, item):
        self.line_indents.pop()

    def markdown_tagon_fenced_code(self, item):
        self.write_characters("```\n")

    def markdown_tagoff_fenced_code(self, item):
        self.outfile.write("\n")
        self.line_indented = False
        self.write_characters("```")

    def markdown_tagon_thematic_break(self, item):
        self.skip_text = True

    def markdown_tagoff_thematic_break(self, item):
        self.write_characters("---")
        self.write_line_indent(force=True)
        self.outfile.write("\n")
        self.skip_text = False

    def markdown_tagon_link(self, item):
        for tag in self.view.tag_names(item[2]):
            if tag.startswith(constants.LINK_PREFIX):
                self.current_link_tag = tag
                break
        self.write_characters("[")

    def markdown_tagoff_link(self, item):
        link = self.get_link(self.current_link_tag)
        if link["title"]:
            self.write_characters(f"""]({link['url']} "{link['title']}")""")
        else:
            self.write_characters(f"]({link['url']})")
        self.current_link_tag = None

    def markdown_tagon_indexed(self, item):
        for tag in self.view.tag_names(item[2]):
            if tag.startswith(constants.INDEXED_PREFIX):
                first, last = self.view.tag_nextrange(tag, item[2])
                self.current_indexed_term = self.view.get(first, last)
                self.current_indexed_tag = tag
                break
        self.write_characters("[#")

    def markdown_tagoff_indexed(self, item):
        canonical = self.current_indexed_tag[len(constants.INDEXED_PREFIX) :]
        if self.current_indexed_term == canonical:
            self.write_characters("]")
        else:
            self.write_characters(f"|{canonical}]")

    def markdown_tagon_reference(self, item):
        self.write_characters("[@")

    def markdown_tagoff_reference(self, item):
        self.write_characters("]")

    def markdown_tagon_footnote_ref(self, item):
        for tag in self.view.tag_names(item[2]):
            if tag.startswith(constants.FOOTNOTE_REF_PREFIX):
                old_label = tag[len(constants.FOOTNOTE_REF_PREFIX) :]
                footnote = self.footnotes[old_label]
                new_label = str(len(self.markdown_footnotes) + 1)
                footnote["new_label"] = new_label
                self.markdown_footnotes[old_label] = footnote
                break
        self.write_characters(f"[^{new_label}]")
        self.skip_text = True

    def markdown_tagoff_footnote_ref(self, item):
        pass

    def markdown_tagon_footnote_def(self, item):
        for tag in self.view.tag_names(item[2]):
            if tag.startswith(constants.FOOTNOTE_DEF_PREFIX):
                old_label = tag[len(constants.FOOTNOTE_DEF_PREFIX) :]
        footnote = self.markdown_footnotes[old_label]
        footnote["outfile"] = io.StringIO()
        self.outfile_stack.append(footnote["outfile"])
        self.skip_text = False

    def markdown_tagoff_footnote_def(self, item):
        self.outfile_stack.pop()

    def close(self, event=None, force=False):
        if self.modified and not force:
            if not tk.messagebox.askokcancel(
                parent=self.toplevel,
                title=Tr("Close?"),
                message=f"{Tr('Modifications will not be saved')}. {Tr('Really close?')}",
            ):
                return "break"  # When called by keyboard event.
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
        """Remove the link in the text. Do not remove from 'links'.
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


class EditIndexed(tk.simpledialog.Dialog):
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
        w = tk.ttk.Button(
            box, text=Tr("OK"), width=10, command=self.ok, default=tk.ACTIVE
        )
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


class AddReference(tk.simpledialog.Dialog):
    "Dialog window for selecting a reference to add."

    def __init__(self, toplevel, references):
        self.result = None
        self.selected = None
        self.references = references
        super().__init__(toplevel, title=Tr("Add reference"))

    def body(self, body):
        body.rowconfigure(0, weight=1)
        body.columnconfigure(0, weight=1)
        self.treeview = tk.ttk.Treeview(
            body,
            height=min(20, len(self.references)),
            columns=("title",),
            selectmode="browse",
        )
        self.treeview.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.treeview.heading("#0", text=Tr("Reference id"))
        self.treeview.column(
            "#0",
            anchor=tk.W,
            minwidth=10 * constants.FONT_NORMAL_SIZE,
            width=20 * constants.FONT_NORMAL_SIZE,
        )
        self.treeview.heading("title", text=Tr("Title"), anchor=tk.W)
        self.treeview.column(
            "title",
            anchor=tk.W,
            minwidth=20 * constants.FONT_NORMAL_SIZE,
            width=40 * constants.FONT_NORMAL_SIZE,
            stretch=True,
        )
        self.treeview_scroll_y = tk.ttk.Scrollbar(
            body, orient=tk.VERTICAL, command=self.treeview.yview
        )
        self.treeview_scroll_y.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.treeview.configure(yscrollcommand=self.treeview_scroll_y.set)

        self.treeview.bind("<<TreeviewSelect>>", self.select)
        for reference in self.references:
            self.treeview.insert(
                "",
                tk.END,
                reference["id"],
                text=str(reference),
                values=(reference["title"],),
            )
        return self.treeview

    def select(self, event):
        self.selected = self.treeview.selection()[0]

    def apply(self):
        self.result = self.selected
