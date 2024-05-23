"Editor window for text Markdown file."

import io

import tkinter as tk
import tkinter.ttk
import tkinter.simpledialog
import tkinter.messagebox

import constants
import utils

from utils import Tr
from editor import Editor

from icecream import ic


class TextEditor(Editor):
    "Editor for source text Markdown file."

    TEXT_COLOR = constants.EDIT_COLOR

    def menubar_create(self):
        super().menubar_create()
        self.menubar.add_command(
            label=Tr("Index"), command=self.indexed_add, state=tk.DISABLED
        )
        self.menubar_changed_by_selection.add(self.menubar.index(tk.END))
        self.menubar.add_command(label=Tr("Reference"), command=self.reference_add)
        self.menubar.add_command(
            label=Tr("Footnote"), command=self.footnote_add, state=tk.DISABLED
        )
        self.menubar_changed_by_selection.add(self.menubar.index(tk.END))

        self.menu_status = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_status, label=Tr("Status"))
        self.status_var = tk.StringVar(value=str(self.text.status))
        for status in constants.STATUSES:
            self.menu_status.add_radiobutton(
                label=Tr(str(status)),
                value=str(status),
                variable=self.status_var,
                command=self.set_status,
            )

    def popup_menu_add_selected(self, menu):
        "Add items to the popup menu for when text is selected."
        menu.add_command(label=Tr("Index"), command=self.indexed_add)
        menu.add_command(label=Tr("Footnote"), command=self.footnote_add)

    def get_cursor(self):
        "Get the position of cursor in absolute number of characters."
        return len(self.view.get("1.0", tk.INSERT))

    def set_cursor(self, position):
        "Set the position of the cursor by the absolute number of characters."
        self.view.mark_set(tk.INSERT, self.view.index("1.0" + f"+{position}c"))
        self.view.see(tk.INSERT)

    cursor = property(get_cursor, set_cursor)

    def handle_modified(self, event=None):
        super().handle_modified(event=event)
        self.main.treeview_set_info(self.text, modified=self.modified)

    def set_status(self):
        try:
            old_status = self.text.status
        except AttributeError:
            old_status = None
        new_status = constants.Status.lookup(self.status_var.get().lower())
        self.view.edit_modified(new_status != old_status)

    def save_prepare(self):
        "Prepare for saving; before doing dump-to-Markdown."
        super().save_prepare()
        self.text.status = constants.Status.lookup(self.status_var.get().lower())
        self.markdown_footnotes = {}

    def save_after_dump(self):
        "Perform save operations after having done dump-to-Markdown; footnotes."
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

    def save_finalize(self):
        "Main updates following text save."
        self.main.save_text_editor(self)

    def close_finalize(self):
        "Main updates following editor close."
        self.main.close_text_editor(self)
