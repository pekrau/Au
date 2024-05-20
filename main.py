"""Authoring editor tool based on Tkinter.

Class hierarchy:

RenderMixin
  # Mixin class containing methods to render Marko AST to tk.Text instance.
  # Assumes an attribute '.view'; instance of tk.Text.

BaseViewer 
  # Base class with methods for viewer using a 'tk.Text' instance.

TextViewer
  # Viewer class for text with Markdown rendering methods and bindings.
  > RenderMixin
  > BaseViewer

BaseEditor
  # Base editor class.
  > TextViewer
    > RenderMixin
    > BaseViewer

TextEditor
  # Editor window for Markdown text file.
  > BaseEditor
    > TextViewer
      > RenderMixin
      > BaseViewer

TitleViewer
  # View of the title page setup.
  > BaseViewer

ReferencesViewer
  # Viewer for the references.
  > BaseViewer

ReferenceEditor
  # Edit a reference.
  > BaseEditor
    > TextViewer
      > RenderMixin
      > BaseViewer

IndexedViewer
  # Viewer for the list of indexed terms.
  > BaseViewer

SearchViewer
  # Viewer for the search feature and resulting list.
  > BaseViewer

HelpViewer(BaseTextViewer)
  # View of the help file Markdown contents.
  > RenderMixin
  > BaseViewer
"""

from icecream import ic

import functools
import json
import os
import shutil

import tkinter as tk
import tkinter.messagebox
import tkinter.simpledialog
import tkinter.ttk
import tkinter.font

import constants
import utils
import docx_export

from utils import Tr
from source import Source
from text_viewer import TextViewer
from text_editor import TextEditor
from title_viewer import TitleViewer
from references_viewer import ReferencesViewer
from reference_editor import ReferenceEditor
from indexed_viewer import IndexedViewer
from search_viewer import SearchViewer
from help_viewer import HelpViewer


class Main:
    """Main window containing three panes:
    1) The tree of sections and texts.
    2) The notebook containing tabs for all top-level texts.
    3) The notebook with references, indexed and help.
    """

    def __init__(self, absdirpath):
        self.absdirpath = absdirpath

        # Create hard-wired directories, if not done.
        archivedirpath = os.path.join(self.absdirpath, constants.ARCHIVE_DIRNAME)
        if not os.path.exists(archivedirpath):
            os.mkdir(archivedirpath)
        referencesdirpath = os.path.join(self.absdirpath, constants.REFERENCES_DIRNAME)
        if not os.path.exists(referencesdirpath):
            os.mkdir(referencesdirpath)

        self.help_source = Source(os.path.join(os.path.dirname(__file__), "help"))
        self.source = Source(self.absdirpath)
        self.config_read()

        self.root = tk.Tk()
        font_families = set(tk.font.families())
        assert constants.FONT in font_families
        assert constants.QUOTE_FONT in font_families

        self.root.geometry(
            self.config["main"].get("geometry", constants.DEFAULT_ROOT_GEOMETRY)
        )
        self.root.option_add("*tearOff", tk.FALSE)
        self.root.minsize(600, 600)
        self.au64 = tk.PhotoImage(data=constants.AU64)
        self.root.iconphoto(False, self.au64, self.au64)
        self.root.protocol("WM_DELETE_WINDOW", self.quit)
        self.root.bind("<Configure>", self.root_resized)
        self.root.bind("<Control-q>", self.quit)
        self.root.bind("<Control-Q>", self.quit)
        self.root.after(constants.AGES_UPDATE_DELAY, self.treeview_update_ages)

        self.title = self.config["main"].get("title") or str(self.source)
        self.subtitle = self.config["main"].get("subtitle") or ""
        self.authors = self.config["main"].get("authors") or []
        self.clipboard = []
        self.clipboard_chars = ""
        self.source.apply_config(self.config["source"])
        self.text_editors = {}  # Key: fullname; value: TextEditor instance
        self.reference_editors = {}  # Key: fullname; value: ReferenceEditor instance
        self.panedwindow = tk.ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.panedwindow.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.menubar_setup()
        self.treeview_create()
        self.texts_notebook_create()
        self.meta_notebook_create()

        # Set the sizes of the panes.
        try:
            sash = self.config["main"]["sash"]
        except KeyError:
            pass
        else:
            self.panedwindow.sashpos(0, sash[0])
            self.panedwindow.sashpos(1, sash[1])

        self.treeview_populate()
        self.texts_notebook_populate()
        self.meta_notebook_populate()

    @property
    def configpath(self):
        return os.path.join(self.absdirpath, constants.CONFIG_FILENAME)

    def get_title(self):
        return self._title

    def set_title(self, title):
        self._title = title
        self.root.title(title)

    title = property(get_title, set_title)

    def config_read(self):
        "Read the configuration file."
        try:
            with open(self.configpath) as infile:
                self.config = json.load(infile)
            if "main" not in self.config:
                raise ValueError  # Invalid JSON content.
        except (OSError, json.JSONDecodeError, ValueError):
            self.config = dict(main={}, meta={}, source={}, export={})

    def config_save(self):
        "Save the current config. Get current state from the respective widgets."
        config = {}
        config["main"] = dict(
            title=self.title,
            subtitle=self.subtitle,
            authors=self.authors,
            geometry=self.root.geometry(),
            sash=[self.panedwindow.sashpos(0), self.panedwindow.sashpos(1)],
        )

        config["meta"] = dict(
            selected=str(self.meta_notebook_lookup[self.meta_notebook.select()])
        )
        config["source"] = self.source.get_config()

        # Currently selected text, and cursor locations in all viewers.
        config["source"]["selected"] = self.treeview.focus()
        config["source"]["cursor"] = dict(
            [(t.fullname, t.viewer.cursor) for t in self.source.all_texts]
        )

        config["export"] = self.config.get("export", {})

        with open(self.configpath, "w") as outfile:
            json.dump(config, outfile, indent=2)
        self.config = config

    def root_resized(self, event):
        "Save configuration after root window resize."
        if event.widget != self.root:
            return
        if getattr(self, "_after_id", None):
            self.root.after_cancel(self._after_id)
        self._after_id = self.root.after(
            constants.CONFIG_UPDATE_DELAY, self.config_save
        )

    def menubar_setup(self):
        self.menubar = tk.Menu(self.root, background="gold")
        self.root["menu"] = self.menubar
        self.menubar.add_command(label="Au", font=constants.FONT_LARGE_BOLD)

        self.menu_file = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_file, label=Tr("File"))
        self.menu_file.add_command(label=Tr("Archive"), command=self.archive)
        self.menu_file.add_command(
            label=Tr("Quit"), command=self.quit, accelerator="Ctrl-Q"
        )

        self.menu_edit = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_edit, label=Tr("Edit"))
        # The order here affects 'set_menubar_state'.
        self.menu_edit.add_command(label=Tr("Create text"), command=self.create_text)
        self.menu_edit.add_command(
            label=Tr("Create section"), command=self.create_section
        )
        self.menu_edit.add_command(label=Tr("Rename"), command=self.rename)
        self.menu_edit.add_command(label=Tr("Copy"), command=self.copy)
        self.menu_edit.add_command(label=Tr("Delete"), command=self.delete)

        self.menu_move = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_move, label=Tr("Rearrange"))
        # The order here affects 'set_menubar_state'.
        self.menu_move.add_command(
            label=Tr("Move up"), command=self.move_item_up, accelerator="Ctrl-Up"
        )
        self.menu_move.add_command(
            label=Tr("Move down"), command=self.move_item_down, accelerator="Ctrl-Down"
        )
        self.menu_move.add_command(
            label=Tr("Into section"),
            command=self.move_item_into_section,
            accelerator="Ctrl-Left",
        )
        self.menu_move.add_command(
            label=Tr("Out of section"),
            command=self.move_item_out_of_section,
            accelerator="Ctrl-Right",
        )

        self.menu_export = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_export, label=Tr("Export"))
        self.menu_export.add_command(label="DOCX", command=self.export_docx)
        self.menu_export.add_command(label="PDF", command=self.export_pdf)
        self.menu_export.add_command(label="EPUB", command=self.export_epub)
        self.menu_export.add_command(label="HTML", command=self.export_html)

        self.menu_popup = tk.Menu(self.root)
        self.menu_popup.add_command(label=Tr("Create text"), command=self.create_text)
        self.menu_popup.add_command(
            label=Tr("Create section"), command=self.create_section
        )
        self.menu_popup.add_command(label=Tr("Rename"), command=self.rename)
        self.menu_popup.add_command(label=Tr("Copy"), command=self.copy)
        self.menu_popup.add_command(label=Tr("Delete"), command=self.delete)
        self.menu_popup.add_separator()
        self.menu_popup.add_command(label=Tr("Move up"), command=self.move_item_up)
        self.menu_popup.add_command(label=Tr("Move down"), command=self.move_item_down)
        self.menu_popup.add_command(
            label=Tr("Into section"), command=self.move_item_into_section
        )
        self.menu_popup.add_command(
            label=Tr("Out of section"), command=self.move_item_out_of_section
        )

    def set_menubar_state(self):
        """To avoid potential problems, some menu items are restricted
        while any text editors are open.
        """
        state = self.text_editors and tk.DISABLED or tk.NORMAL
        self.menu_edit.entryconfigure(2, state=state)  # Edit: Rename
        self.menu_edit.entryconfigure(3, state=state)  # Edit: Copy
        self.menu_edit.entryconfigure(4, state=state)  # Edit: Delete
        self.menu_move.entryconfigure(2, state=state)  # Move: Into section
        self.menu_move.entryconfigure(3, state=state)  # Move: Out of section

    def treeview_create(self):
        "Create the treeview framework."
        self.treeview_frame = tk.ttk.Frame(self.panedwindow)
        self.panedwindow.add(self.treeview_frame)
        self.treeview_frame.rowconfigure(0, weight=1)
        self.treeview_frame.columnconfigure(0, weight=1)
        self.treeview = tk.ttk.Treeview(
            self.treeview_frame, columns=("status", "chars", "age"), selectmode="browse"
        )
        self.treeview.tag_configure("section", background=constants.SECTION_COLOR)
        self.treeview.tag_configure("modified", background=constants.MODIFIED_COLOR)
        self.treeview.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.treeview.heading("#0", text=Tr("Item"))
        self.treeview.heading("status", text=Tr("Status"))
        self.treeview.heading("chars", text=Tr("Chars"))
        self.treeview.heading("age", text=Tr("Age"))
        self.treeview.column(
            "status",
            anchor=tk.E,
            minwidth=3 * constants.FONT_NORMAL_SIZE,
            width=6 * constants.FONT_NORMAL_SIZE,
        )
        self.treeview.column(
            "chars",
            anchor=tk.E,
            minwidth=3 * constants.FONT_NORMAL_SIZE,
            width=6 * constants.FONT_NORMAL_SIZE,
        )
        self.treeview.column(
            "age",
            anchor=tk.E,
            minwidth=2 * constants.FONT_NORMAL_SIZE,
            width=6 * constants.FONT_NORMAL_SIZE,
        )
        self.treeview_scroll_y = tk.ttk.Scrollbar(
            self.treeview_frame, orient=tk.VERTICAL, command=self.treeview.yview
        )
        self.treeview_scroll_y.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.treeview.configure(yscrollcommand=self.treeview_scroll_y.set)

        self.treeview.bind("<Control-Up>", self.move_item_up)
        self.treeview.bind("<Control-Down>", self.move_item_down)
        self.treeview.bind("<Control-Right>", self.move_item_into_section)
        self.treeview.bind("<Control-Left>", self.move_item_out_of_section)

        self.treeview.bind("<Button-3>", self.popup_menu)
        self.treeview.bind("<Double-Button-1>", self.open_text_editor)
        self.treeview.bind("<<TreeviewSelect>>", self.treeview_selected)
        self.treeview.bind("<<TreeviewOpen>>", self.treeview_open)
        self.treeview.bind("<<TreeviewClose>>", self.treeview_close)
        self.treeview.focus_set()

    def treeview_populate(self):
        for child in self.treeview.get_children():
            self.treeview.delete(child)
        for item in self.source.all_items:
            self.add_treeview_entry(item)

    def add_treeview_entry(self, item, index=None):
        if item.is_text:
            self.treeview.insert(
                item.parentpath, index or tk.END, iid=item.fullname, text=item.name
            )
        elif item.is_section:
            self.treeview.insert(
                item.parentpath,
                index or tk.END,
                iid=item.fullname,
                text=item.name,
                open=item.open,
                tags=(constants.SECTION,),
            )

    def treeview_selected(self, event):
        "Synchronize text tab with selected in the treeview."
        try:
            item = self.source[self.treeview.focus()]
        except KeyError:
            pass
        else:
            if item.is_text:
                self.texts_notebook.select(item.tabid)
                item.viewer.view.focus_set()

    def treeview_open(self, event=None):
        fullname = self.treeview.focus()
        item = self.source[fullname]
        assert item.is_section
        item.open = True
        for item in item.all_items:
            if item.is_text:
                self.texts_notebook.add(item.tabid)
            elif item.is_section:
                item.open = True

    def treeview_close(self, event=None):
        fullname = self.treeview.focus()
        item = self.source[fullname]
        assert item.is_section
        item.open = False
        for text in item.all_texts:
            self.texts_notebook.hide(text.tabid)

    def treeview_set_info(self, text, modified=None):
        if modified is None:
            try:
                modified = self.text_editors[text.fullname].is_modified
            except KeyError:
                modified = False
        tags = set(self.treeview.item(text.fullname, "tags"))
        tags = set()
        if modified:
            tags.add("modified")
        else:
            tags.discard("modified")
        self.treeview.item(text.fullname, tags=tuple(tags))
        self.treeview.set(text.fullname, "status", Tr(str(text.status)))
        self.treeview.set(text.fullname, "chars", text.viewer.character_count)
        self.treeview.set(text.fullname, "age", text.age)

    def treeview_update_ages(self):
        for text in self.source.all_texts:
            self.treeview.set(text.fullname, "age", text.age)
        self.root.after(constants.AGES_UPDATE_DELAY, self.treeview_update_ages)

    def texts_notebook_create(self):
        "Create the texts notebook framework."
        self.texts_notebook = tk.ttk.Notebook(self.panedwindow)
        self.panedwindow.add(self.texts_notebook)
        # Key: tabid; value: instance
        self.texts_notebook_lookup = {}

    def texts_notebook_populate(self):
        """Create views for tabs in the texts notebook.
        Also updates the text information in the treeview.
        """
        # First delete any existing text views.
        while self.texts_notebook_lookup:
            self.texts_notebook.forget(self.texts_notebook_lookup.popitem()[0])

        # Create the text views.
        for text in self.source.all_texts:
            text.viewer = viewer = TextViewer(self.texts_notebook, self, text)
            self.texts_notebook.add(
                viewer.frame,
                text=viewer.name,
                state=text.shown and tk.NORMAL or tk.HIDDEN,
            )
            tabs = self.texts_notebook.tabs()
            text.tabid = tabs[-1]
            self.texts_notebook_lookup[text.tabid] = text
            opener = functools.partial(self.open_text_editor, text=text)
            viewer.view.bind("<Double-Button-1>", opener)
            viewer.view.bind("<Return>", opener)
            viewer.view.bind("<Control-q>", self.quit)
            viewer.view.bind("<Control-Q>", self.quit)
            self.treeview_set_info(text)
            # Place the cursor in the text view.
            try:
                text.viewer.cursor = self.config["source"]["cursor"][text.fullname]
            except KeyError:
                pass
        self.update_statistics()

        # Set selected text tab in notebook.
        try:
            text = self.source[self.config["source"]["selected"]]
        except KeyError:
            pass
        else:
            self.treeview.selection_set(text.fullname)
            self.treeview.see(text.fullname)
            self.treeview.focus(text.fullname)
            self.treeview.update()
        self.texts_notebook.bind(
            "<<NotebookTabChanged>>", self.texts_notebook_tab_changed
        )

    def texts_notebook_tab_changed(self, event):
        "Synchronize selected in treeview with tab change."
        text = self.texts_notebook_lookup[self.texts_notebook.select()]
        self.treeview.selection_set(text.fullname)
        self.treeview.focus(text.fullname)

    def meta_notebook_create(self):
        "Create the meta notebook framework."
        self.meta_notebook = tk.ttk.Notebook(self.panedwindow)
        self.panedwindow.add(self.meta_notebook)

        # key: tabid; value: instance
        self.meta_notebook_lookup = {}

        self.title_viewer = TitleViewer(self.meta_notebook, self)
        self.meta_notebook.add(self.title_viewer.frame, text=Tr("Title"))
        self.title_viewer.tabid = self.meta_notebook.tabs()[-1]
        self.title_viewer.view.bind("<Control-q>", self.quit)
        self.title_viewer.view.bind("<Control-Q>", self.quit)
        self.meta_notebook_lookup[self.title_viewer.tabid] = self.title_viewer

        self.references_viewer = ReferencesViewer(self.meta_notebook, self)
        self.meta_notebook.add(self.references_viewer.frame, text=Tr("References"))
        self.references_viewer.tabid = self.meta_notebook.tabs()[-1]
        self.references_viewer.view.bind("<Control-q>", self.quit)
        self.references_viewer.view.bind("<Control-Q>", self.quit)
        self.meta_notebook_lookup[self.references_viewer.tabid] = self.references_viewer

        self.indexed_viewer = IndexedViewer(self.meta_notebook, self)
        self.meta_notebook.add(self.indexed_viewer.frame, text=Tr("Index"))
        self.indexed_viewer.tabid = self.meta_notebook.tabs()[-1]
        self.indexed_viewer.view.bind("<Control-q>", self.quit)
        self.indexed_viewer.view.bind("<Control-Q>", self.quit)
        self.meta_notebook_lookup[self.indexed_viewer.tabid] = self.indexed_viewer

        self.search_viewer = SearchViewer(self.meta_notebook, self)
        self.meta_notebook.add(self.search_viewer.frame, text=Tr("Search"))
        self.search_viewer.tabid = self.meta_notebook.tabs()[-1]
        self.search_viewer.view.bind("<Control-q>", self.quit)
        self.search_viewer.view.bind("<Control-Q>", self.quit)
        self.meta_notebook_lookup[self.search_viewer.tabid] = self.search_viewer

        self.help_viewer = HelpViewer(self.meta_notebook, self)
        self.meta_notebook.add(self.help_viewer.frame, text=Tr("Help"))
        self.help_viewer.tabid = self.meta_notebook.tabs()[-1]
        self.help_viewer.view.bind("<Control-q>", self.quit)
        self.help_viewer.view.bind("<Control-Q>", self.quit)
        self.meta_notebook_lookup[self.help_viewer.tabid] = self.help_viewer

        # Set selected meta tab in notebook.
        selected = self.config["meta"].get("selected")
        for viewer in self.meta_notebook_lookup.values():
            if str(viewer) == selected:
                try:
                    self.meta_notebook.select(viewer.tabid)
                except tk.TclError:
                    pass
                break

    def meta_notebook_populate(self):
        "Populate the meta notebook with contents; help panel does not change."
        self.title_viewer.display()
        self.references_viewer.display()
        self.indexed_viewer.display()
        self.search_viewer.display()

    def update_statistics(self):
        self.title_viewer.chapters_var.set(len(self.source.items))
        self.title_viewer.texts_var.set(len(self.source.all_texts))
        self.title_viewer.characters_var.set(
            sum([t.viewer.character_count for t in self.source.all_texts])
        )

    def archive(self):
        try:
            count = self.source.archive(sources=self.references_viewer.source)
        except OSError as error:
            tk.messagebox.showerror(
                title="Error", message=f"Could not write .tgz file: {error}"
            )
        else:
            tk.messagebox.showinfo(
                title=Tr("Archive file written"),
                message=f"{count} {Tr('items written to archive file')}.",
            )

    def export_docx(self):
        config = self.config["export"].get("docx") or {}
        if "title" not in config:
            config["title"] = self.title
        answer = docx_export.Dialog(self.root, config)
        if not answer.result:
            return
        filepath = os.path.join(answer.result["dirpath"], answer.result["filename"])
        exporter = docx_export.Exporter(self.source, answer.result)
        exporter.write(filepath)
        tk.messagebox.showinfo(
            title=Tr("DOCX file written"),
            message=f"DOCX {Tr('file')} '{filepath}' {Tr('written')}.",
        )
        self.config["export"]["docx"] = answer.result

    def export_pdf(self):
        raise NotImplementedError

    def export_epub(self):
        raise NotImplementedError

    def export_html(self):
        raise NotImplementedError

    def quit(self, event=None):
        modified = [e.is_modified for e in self.text_editors.values()] + [
            e.is_modified for e in self.reference_editors.values()
        ]
        if modified:
            modified = functools.reduce(lambda a, b: a or b, modified)
        if modified and not tk.messagebox.askokcancel(
            parent=self.root,
            title=Tr("Quit"),
            message=Tr("All unsaved changes will be lost. Really quit?"),
        ):
            return
        self.config_save()
        self.root.destroy()

    def move_item_up(self, event=None):
        "Move the currently selected item up within its level of the treeview."
        try:
            fullname = self.treeview.selection()[0]
        except IndexError:
            return "break"
        item = self.source[fullname]
        parentfullname = item.parent.fullname
        index = self.treeview.index(fullname)
        try:
            item.move_up()
        except ValueError:
            return "break"
        self.treeview.move(fullname, parentfullname, index - 1)
        self.texts_notebook_reorder_tabs(item)
        self.source.check_integrity()
        self.config_save()
        return "break"

    def move_item_down(self, event=None):
        "Move the currently selected item down within its level of the treeview."
        try:
            fullname = self.treeview.selection()[0]
        except IndexError:
            return "break"
        item = self.source[fullname]
        parentfullname = item.parent.fullname
        index = self.treeview.index(fullname)
        try:
            item.move_down()
        except ValueError:
            return "break"
        self.treeview.move(fullname, parentfullname, index + 1)
        self.texts_notebook_reorder_tabs(item)
        self.source.check_integrity()
        self.config_save()
        return "break"

    def texts_notebook_reorder_tabs(self, item):
        "Reorder all tabs according to current order in source."
        for index, text in enumerate(self.source.all_texts):
            self.texts_notebook.insert(index, text.tabid)

    def move_item_into_section(self, event=None):
        """Move the currently selected item down one level in hierarchy
        into the section immediately above it at the same level.
        """
        try:
            fullname = self.treeview.selection()[0]
        except IndexError:
            return "break"
        item = self.source[fullname]
        try:
            item.move_to_section(item.prev)
        except ValueError:
            return "break"
        self.treeview_populate()  # XXX Optimize!
        self.treeview.update()
        self.texts_notebook_populate()  # XXX Optimize!
        self.texts_notebook.update()
        self.treeview.selection_set(item.fullname)
        self.treeview.see(item.fullname)
        self.treeview.focus(item.fullname)
        self.config_save()
        return "break"

    def move_item_out_of_section(self, event=None):
        "Move the currently selected item up one level in the hierachy."
        try:
            fullname = self.treeview.selection()[0]
        except IndexError:
            return "break"
        item = self.source[fullname]
        try:
            item.move_to_parent()
        except ValueError:
            return "break"
        self.treeview_populate()  # XXX Optimize!
        self.treeview.update()
        self.texts_notebook_populate()  # XXX Optimize!
        self.texts_notebook.update()
        self.treeview.selection_set(item.fullname)
        self.treeview.focus(item.fullname)
        self.config_save()
        return "break"

    def rename(self):
        "Rename the currently selected item."
        try:
            fullname = self.treeview.selection()[0]
        except IndexError:
            return
        item = self.source[fullname]
        newname = tk.simpledialog.askstring(
            parent=self.root,
            title=Tr("New name"),
            prompt=Tr("Give the new name for the item") + ":",
            initialvalue=item.name,
        )
        if not newname:
            return
        if newname == item.name:
            return
        try:
            item.rename(newname)
        except ValueError as error:
            tk.messagebox.showerror(
                parent=self.treeview, title="Error", message=str(error)
            )
            return
        if item.is_text:
            index = self.treeview.index(fullname)
            self.treeview.delete(fullname)
            self.add_treeview_entry(item, index=index)
            self.texts_notebook.tab(item.tabid, text=item.name)
            item.viewer.display()
        elif item.is_section:
            self.treeview_populate()  # XXX Optimize!
            self.treeview.update()
            self.texts_notebook_populate()  # XXX Optimize!
            self.texts_notebook.update()
        self.treeview.selection_set(item.fullname)
        self.treeview.focus(item.fullname)
        self.config_save()

    def copy(self):
        "Make a copy of the currently selected item."
        try:
            fullname = self.treeview.selection()[0]
        except IndexError:
            return
        item = self.source[fullname]
        newname = f"Copy of {item.name}"
        for i in range(2, 10):
            try:
                newitem = item.copy(newname)
            except ValueError:
                newname = f"Copy {i} of {item.name}"
            else:
                break
        else:
            tk.messagebox.showerror(
                parent=self.treeview,
                title="Error",
                message="Could not generate a unique name for the copy.",
            )
            return
        self.treeview_populate()  # XXX Optimize!
        self.treeview.update()
        self.texts_notebook_populate()  # XXX Optimize!
        self.texts_notebook.update()
        self.treeview.selection_set(newitem.fullname)
        self.treeview.focus(newitem.fullname)
        self.source.check_integrity()
        self.config_save()

    def delete(self):
        try:
            fullname = self.treeview.selection()[0]
        except IndexError:
            return
        item = self.source[fullname]
        if item.is_text:
            if not tk.messagebox.askokcancel(
                parent=self.treeview,
                title=Tr("Delete text"),
                message=f"{Tr('Really delete text')} '{item.fullname}'?",
            ):
                return
        elif item.is_section:
            if not tk.messagebox.askokcancel(
                parent=self.treeview,
                title=Tr("Delete section"),
                message=f"{Tr('Really delete section')} '{item.fullname}' {Tr('and all its contents?')}",
            ):
                return
        if item.is_text:
            self.treeview.delete(fullname)
            self.texts_notebook.forget(item.tabid)
            self.texts_notebook_lookup.pop(item.tabid)
            item.delete()
        else:
            item.delete()
            self.treeview_populate()  # XXX Optimize!
            self.treeview.update()
            self.texts_notebook_populate()  # XXX Optimize!
            self.texts_notebook.update()
        self.source.check_integrity()
        self.config_save()

    def open_text_editor(self, event=None, text=None):
        if text is None:
            try:
                fullname = self.treeview.selection()[0]
            except IndexError:
                return "break"
            text = self.source[fullname]
            if not text.is_text:
                return "break"
        try:
            editor = self.text_editors[text.fullname]
        except KeyError:
            editor = TextEditor(self, text)
            editor.cursor = text.viewer.cursor
            self.text_editors[text.fullname] = editor
        else:
            editor.toplevel.lift()
        self.set_menubar_state()
        editor.view.update()
        editor.view.focus_set()
        return "break"

    def open_reference_editor(self, viewer, reference, event=None):
        try:
            editor = self.reference_editors[reference.fullname]
        except KeyError:
            editor = ReferenceEditor(self, viewer, reference)
            self.reference_editors[reference.fullname] = editor
        else:
            editor.toplevel.lift()
        editor.view.update()
        editor.view.focus_set()
        return "break"

    def create_text(self):
        try:
            anchor = self.source[self.treeview.selection()[0]]
        except IndexError:
            anchor = None
        name = tk.simpledialog.askstring(
            parent=self.treeview,
            title=Tr("New text"),
            prompt=Tr("Give name of the new text") + ":",
        )
        if not name:
            return
        try:
            text = self.source.create_text(name, anchor)
        except ValueError as error:
            tk.messagebox.showerror(
                parent=self.treeview, title="Error", message=str(error)
            )
            return
        self.treeview_populate()  # XXX Optimize!
        self.treeview.update()
        self.texts_notebook_populate()  # XXX Optimize!
        self.texts_notebook.update()
        self.treeview.selection_set(text.fullname)
        self.treeview.see(text.fullname)
        self.treeview.focus(text.fullname)
        self.source.check_integrity()
        self.config_save()

    def create_section(self):
        try:
            fullname = self.treeview.selection()[0]
        except IndexError:
            return
        anchor = self.source[fullname]
        name = tk.simpledialog.askstring(
            parent=self.treeview,
            title=Tr("New section"),
            prompt=Tr("Give name of the new section") + ":",
        )
        if not name:
            return
        try:
            section = self.source.create_section(anchor, name)
        except ValueError as error:
            tk.messagebox.showerror(
                parent=self.treeview, title="Error", message=str(error)
            )
            return
        self.treeview_populate()  # XXX Optimize!
        self.treeview.update()
        self.texts_notebook_populate()  # XXX Optimize!
        self.texts_notebook.update()
        self.treeview.selection_set(section.fullname)
        self.treeview.see(section.fullname)
        self.treeview.focus(section.fullname)
        self.source.check_integrity()
        self.config_save()

    def popup_menu(self, event):
        fullname = self.treeview.identify_row(event.y)
        if not fullname:
            return
        self.treeview.selection_set(fullname)
        self.treeview.focus(fullname)
        self.menu_popup.tk_popup(event.x_root, event.y_root)

    def mainloop(self):
        self.root.mainloop()


if __name__ == "__main__":
    import sys

    if len(sys.argv) == 2:
        dirpath = sys.argv[1]
        if not os.path.isabs(dirpath):
            absdirpath = os.path.normpath(os.path.join(os.getcwd(), dirpath))
            if not os.path.exists(absdirpath):
                sys.exit(f"{Tr('Error')}: '{absdirpath}' does not exist.")
            if not os.path.isdir(absdirpath):
                sys.exit(f"{Tr('Error')}: '{absdirpath}' is not a directory.")
    elif len(sys.argv) == 1:
        absdirpath = os.getcwd()
    else:
        sys.exit(f"{Tr('Error')}: at most one directory path can be provided.")
    main = Main(absdirpath)
    main.mainloop()
