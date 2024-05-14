"Editor window for text Markdown file."

from icecream import ic

import io

import tkinter as tk
import tkinter.ttk
import tkinter.simpledialog
import tkinter.messagebox

import constants
import utils

from utils import Tr
from base_editor import BaseEditor


class TextEditor(BaseEditor):
    "Editor window for Markdown text file."

    TEXT_COLOR = constants.EDIT_COLOR

    def __init__(self, main, text):
        super().__init__(main.root, main, text)
        self.toplevel_setup()
        self.menubar_setup()
        self.view_create(self.toplevel)
        self.view_configure_tags()
        self.view_configure_tag_bindings()
        self.view_bind_keys()
        self.render(self.text.ast)
        self.view.edit_modified(False)

    def menubar_setup(self):
        super().menubar_setup()
        self.menubar.add_command(label=Tr("Reference"), command=self.reference_add)
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
        self.status_var = tk.StringVar(value=str(self.text.status))
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
        view.tag_bind(constants.FOOTNOTE_REF, "<Button-1>", self.footnote_remove)

    @property
    def character_count(self):
        return len(self.view.get("1.0", tk.END))

    def popup_menu_add(self, menu):
        "Add items to the popup menu."
        menu.add_command(label=Tr("Indexed"), command=self.indexed_add)

    def handle_modified(self, event=None):
        if super().handle_modified(event=event):
            self.main.treeview_set_info(self.text, modified=True)

    def set_status(self):
        try:
            old_status = self.text.status
        except AttributeError:
            old_status =  None
        new_status = constants.Status.lookup(self.status_var.get().lower())
        self.view.edit_modified(new_status != old_status)

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

    def undump_tagon(self, entry, tags):
        super().undump_tagon(entry, tags)
        if entry[1].startswith(constants.FOOTNOTE_REF_PREFIX):
            tags[entry[1]]["label"] = self.get_new_footnote_label()
            self.skip_text = True
        elif entry[1].startswith(constants.FOOTNOTE_DEF_PREFIX):
            tag = constants.FOOTNOTE_REF_PREFIX + entry[1][len(constants.FOOTNOTE_DEF_PREFIX):]
            tags[entry[1]]["label"] = tags[tag]["label"]

    def save_before_dump(self):
        "Perform save operations before doing dump-to-Markdown; status and footnotes."
        self.text.status = constants.Status.lookup(self.status_var.get().lower())
        self.markdown_footnotes = dict()

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
        "Perform final save operations; redisplaying text and setting info."
        self.text.viewer.display()
        self.main.treeview_set_info(self.text)
        self.text.viewer.cursor = self.cursor
        self.main.references_viewer.display() # XXX Optimize?
        self.main.indexed_viewer.display()    # XXX Optimize?
        self.main.search_viewer.clear()

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
