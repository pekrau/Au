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
            label=Tr("Indexed"), command=self.indexed_add, state=tk.DISABLED
        )
        self.menubar.add_command(
            label=Tr("Reference"), command=self.reference_add
        )
        self.menubar_changed_by_selection.add(self.menubar.index(tk.END))
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
        menu.add_command(label=Tr("Indexed"), command=self.indexed_add)

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
        "Perform final save operations; updating displays."
        self.text.read()
        self.text.viewer.display()
        self.main.treeview_set_info(self.text)
        self.main.title_viewer.update_statistics()
        self.text.viewer.cursor = self.cursor

    def markdown_tagon_indexed(self, item):
        for tag in self.view.tag_names(item[2]):
            if tag.startswith(constants.INDEXED_PREFIX):
                first, last = self.view.tag_nextrange(tag, item[2])
                self.current_indexed_term = self.view.get(first, last)
                self.current_indexed_tag = tag
                break
        self.save_characters("[#")

    def markdown_tagoff_indexed(self, item):
        canonical = self.current_indexed_tag[len(constants.INDEXED_PREFIX) :]
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
                old_label = tag[len(constants.FOOTNOTE_REF_PREFIX) :]
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
                old_label = tag[len(constants.FOOTNOTE_DEF_PREFIX) :]
        footnote = self.markdown_footnotes[old_label]
        footnote["outfile"] = io.StringIO()
        self.outfile_stack.append(footnote["outfile"])
        self.skip_text = False

    def markdown_tagoff_footnote_def(self, item):
        self.outfile_stack.pop()

    def close_finalize(self):
        "Perform action at window closing time; remove from main."
        self.main.text_editors.pop(self.text.fullname)
        self.main.set_menubar_state()


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


class ReferenceAdd(tk.simpledialog.Dialog):
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
            minwidth=8 * constants.FONT_NORMAL_SIZE,
            width=12 * constants.FONT_NORMAL_SIZE,
        )
        self.treeview.heading("title", text=Tr("Title"), anchor=tk.W)
        self.treeview.column(
            "title",
            minwidth=16 * constants.FONT_NORMAL_SIZE,
            width=20 * constants.FONT_NORMAL_SIZE,
            anchor=tk.W,
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
