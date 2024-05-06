"Authoring editor based on Tkinter."

from icecream import ic

import functools
import json
import os
import shutil

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox as tk_messagebox
from tkinter import simpledialog as tk_simpledialog
from tkinter import font as tk_font

import constants
import utils
from source import Source
from viewer import Viewer
from editor import Editor
from help_viewer import HelpViewer
from indexed_viewer import IndexedViewer
from search_viewer import SearchViewer
from meta_viewers import TitleViewer, ReferencesViewer, TodoViewer


class Main:
    """Main window containing three panes:
    1) The tree of sections and texts.
    2) The notebook containing tabs for all top-level texts.
    3) The notebook with references, indexed and help.
    """

    def __init__(self, absdirpath):
        self.absdirpath = absdirpath
        self.help_source = Source(os.path.join(os.path.dirname(__file__), "help"))
        self.source = Source(self.absdirpath)
        self.config_read()
        self.source.apply_config(self.config["source"])
        self.editors = dict()   # Key: fullname; value: Editor instance

        self.root = tk.Tk()
        constants.FONT_FAMILIES = frozenset(tk_font.families())
        assert constants.FONT_NORMAL_FAMILY in constants.FONT_FAMILIES

        self.root.title(os.path.basename(absdirpath))
        self.root.geometry(
            self.config["main"].get("geometry", constants.DEFAULT_ROOT_GEOMETRY))
        self.root.option_add("*tearOff", tk.FALSE)
        self.root.minsize(600, 600)
        self.au64 = tk.PhotoImage(data=constants.AU64)
        self.root.iconphoto(False, self.au64, self.au64)
        self.root.protocol("WM_DELETE_WINDOW", self.quit)
        self.root.bind("<Configure>", self.root_resized)
        self.root.after(constants.AGES_UPDATE_DELAY, self.treeview_update_ages)

        # Must be 'tk.PanedWindow', not 'ttk.PanedWindow',
        # since the 'paneconfigure' command is needed.
        self.panedwindow = tk.PanedWindow(self.root,
                                          background="gold",
                                          orient=tk.HORIZONTAL,
                                          sashwidth=5)
        self.panedwindow.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.menubar_setup()
        self.treeview_create()
        self.texts_notebook_create()
        self.meta_notebook_create()

        self.treeview_populate()
        self.texts_notebook_populate()
        self.meta_notebook_populate()
        self.config_apply()

    @property
    def configpath(self):
        return os.path.join(self.absdirpath, constants.CONFIG_FILENAME)

    def config_read(self):
        "Read the configuration file."
        try:
            with open(self.configpath) as infile:
                self.config = json.load(infile)
            if "main" not in self.config:
                raise ValueError # Invalid JSON content.
        except (OSError, json.JSONDecodeError, ValueError):
            self.config = dict(main=dict(), paste=[], items=[])

    def config_save(self):
        "Save the current config. Get current state from the respective widgets."
        config = dict(main=dict(geometry=self.root.geometry(),
                                sash=[self.panedwindow.sash("coord", 0)[0],
                                      self.panedwindow.sash("coord", 1)[0]]),
                      meta=dict(
                          selected=str(self.meta_notebook_lookup[self.meta_notebook.select()])),
                      source=self.source.get_config())
        config["source"]["selected"] = self.treeview.focus()

        # Save the current cut-and-paste buffer.
        config["paste"] = self.paste_buffer

        with open(self.configpath, "w") as outfile:            
            json.dump(config, outfile, indent=2)
        self.config = config

    def config_apply(self):
        "Apply configuration to windows and tabs."
        # The paste buffer is global to all editors, to facilitate cut-and-paste.
        self.paste_buffer = self.config.get("paste") or list()

        try:
            sash = self.config["main"]["sash"]
        except KeyError:
            pass
        else:
            self.panedwindow.update() # Has to be here for this to work.
            self.panedwindow.sash("place", 0, sash[0], 1)
            self.panedwindow.sash("place", 1, sash[1], 1)

        # Set selected text tab in notebook.
        try:
            text = self.source[self.config["source"]["selected"]]
        except KeyError:
            pass
        else:
            self.treeview.selection_set(text.fullname)
            self.treeview.see(text.fullname)
            self.treeview.focus(text.fullname)

        selected = self.config["meta"].get("selected")
        for viewer in self.meta_notebook_lookup.values():
            if str(viewer) == selected:
                try:
                    self.meta_notebook.select(viewer.tabid)
                except tk.TclError:
                    pass
                break

    def root_resized(self, event):
        "Save configuration after root window resize."
        if event.widget != self.root:
            return
        if getattr(self, "_after_id", None):
            self.root.after_cancel(self._after_id)
        self._after_id = self.root.after(constants.CONFIG_UPDATE_DELAY,self.config_save)

    def menubar_setup(self):
        self.menubar = tk.Menu(self.root, background="gold")
        self.root["menu"] = self.menubar
        self.menubar.add_command(label="Au", font=constants.FONT_LARGE_BOLD)

        self.menu_file = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_file, label="File")
        self.menu_file.add_command(label="Archive", command=self.archive)
        self.menu_file.add_command(label="Quit",
                                   command=self.quit,
                                   accelerator="Ctrl-Q")
        self.root.bind("<Control-q>", self.quit)

        self.menu_edit = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_edit, label="Edit")
        # The order here affects 'set_menubar_state'.
        self.menu_edit.add_command(label="Create text", command=self.create_text)
        self.menu_edit.add_command(label="Create section", command=self.create_section)
        self.menu_edit.add_command(label="Rename", command=self.rename)
        self.menu_edit.add_command(label="Copy", command=self.copy)
        self.menu_edit.add_command(label="Delete", command=self.delete)

        self.menu_move = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_move, label="Rearrange")
        # The order here affects 'set_menubar_state'.
        self.menu_move.add_command(label="Move up",
                                      command=self.move_item_up,
                                      accelerator="Ctrl-Up")
        self.menu_move.add_command(label="Move down",
                                      command=self.move_item_down,
                                      accelerator="Ctrl-Down")
        self.menu_move.add_command(label="Into section",
                                      command=self.move_item_into_section,
                                      accelerator="Ctrl-Left")
        self.menu_move.add_command(label="Out of section",
                                      command=self.move_item_out_of_section,
                                      accelerator="Ctrl-Right")

        self.menu_compile = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_compile, label="Compile")
        self.menu_compile.add_command(label="DOCX", command=self.source.compile_docx)
        self.menu_compile.add_command(label="PDF", command=self.source.compile_pdf)
        self.menu_compile.add_command(label="EPUB", command=self.source.compile_epub)
        self.menu_compile.add_command(label="HTML", command=self.source.compile_html)

        self.menu_popup = tk.Menu(self.root)
        self.menu_popup.add_command(label="Create text", command=self.create_text)
        self.menu_popup.add_command(label="Create section", command=self.create_section)
        self.menu_popup.add_command(label="Rename", command=self.rename)
        self.menu_popup.add_command(label="Copy", command=self.copy)
        self.menu_popup.add_command(label="Delete", command=self.delete)
        self.menu_popup.add_separator()
        self.menu_popup.add_command(label="Move up", command=self.move_item_up)
        self.menu_popup.add_command(label="Move down", command=self.move_item_down)
        self.menu_popup.add_command(label="Into section",
                                    command=self.move_item_into_section)
        self.menu_popup.add_command(label="Out of section",
                                    command=self.move_item_out_of_section)

    def set_menubar_state(self):
        "To avoid potential problems, some menu items require that no editors are open."
        state = self.editors and tk.DISABLED or tk.NORMAL
        self.menu_edit.entryconfigure(2, state=state) # Rename
        self.menu_edit.entryconfigure(3, state=state) # Copy
        self.menu_edit.entryconfigure(4, state=state) # Delete
        self.menu_move.entryconfigure(2, state=state) # Into section
        self.menu_move.entryconfigure(3, state=state) # Out of section

    def treeview_create(self):
        "Create the treeview framework."
        self.treeview_frame = ttk.Frame(self.panedwindow)
        self.panedwindow.add(self.treeview_frame,
                             width=constants.TREEVIEW_PANE_WIDTH,
                             minsize=constants.PANE_MINSIZE)

        self.treeview_frame.rowconfigure(0, weight=1)
        self.treeview_frame.columnconfigure(0, weight=1)
        self.treeview = ttk.Treeview(self.treeview_frame,
                                     columns=("status", "chars", "age"),
                                     selectmode="browse")
        self.treeview.tag_configure("section", background=constants.SECTION_COLOR)
        self.treeview.tag_configure("modified", background=constants.MODIFIED_COLOR)
        self.treeview.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.treeview.heading("#0", text="Item")
        self.treeview.heading("status", text="Status")
        self.treeview.heading("chars", text="Chars")
        self.treeview.heading("age", text="Age")
        self.treeview.column("status",
                             anchor=tk.E,
                             minwidth=3*constants.FONT_NORMAL_SIZE,
                             width=6*constants.FONT_NORMAL_SIZE)
        self.treeview.column("chars",
                             anchor=tk.E,
                             minwidth=3*constants.FONT_NORMAL_SIZE,
                             width=6*constants.FONT_NORMAL_SIZE)
        self.treeview.column("age",
                             anchor=tk.E,
                             minwidth=2*constants.FONT_NORMAL_SIZE,
                             width=6*constants.FONT_NORMAL_SIZE)
        self.treeview_scroll_y = ttk.Scrollbar(self.treeview_frame,
                                               orient=tk.VERTICAL,
                                               command=self.treeview.yview)
        self.treeview_scroll_y.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.treeview.configure(yscrollcommand=self.treeview_scroll_y.set)

        self.treeview.bind("<Control-Up>", self.move_item_up)
        self.treeview.bind("<Control-Down>", self.move_item_down)
        self.treeview.bind("<Control-Right>", self.move_item_into_section)
        self.treeview.bind("<Control-Left>", self.move_item_out_of_section)

        self.treeview.bind("<Button-3>", self.popup_menu)
        self.treeview.bind("<Double-Button-1>", self.open_editor)
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
            self.treeview.insert(item.parentpath,
                                 index or tk.END,
                                 iid=item.fullname,
                                 text=item.name)
        elif item.is_section:
            self.treeview.insert(item.parentpath,
                                 index or tk.END,
                                 iid=item.fullname,
                                 text=item.name,
                                 open=item.open,
                                 tags=(constants.SECTION, ))

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
                modified = self.editors[text.fullname].is_modified
            except KeyError:
                modified = False
        tags = set(self.treeview.item(text.fullname, "tags"))
        tags = set()
        if modified:
            tags.add("modified")
        else:
            tags.discard("modified")
        self.treeview.item(text.fullname, tags=tuple(tags))
        self.treeview.set(text.fullname, "status", str(text.status))
        self.treeview.set(text.fullname, "chars", text.viewer.character_count)
        self.treeview.set(text.fullname, "age", text.age)

    def treeview_update_ages(self):
        for text in self.source.all_texts:
            self.treeview.set(text.fullname, "age", text.age)
        self.root.after(constants.AGES_UPDATE_DELAY, self.treeview_update_ages)

    def texts_notebook_create(self):
        "Create the texts notebook framework."
        self.texts_notebook = ttk.Notebook(self.panedwindow)
        self.panedwindow.add(self.texts_notebook, minsize=constants.PANE_MINSIZE)
         # Key: tabid; value: instance
        self.texts_notebook_lookup = dict()
        self.texts_notebook.bind("<<NotebookTabChanged>>",
                                 self.texts_notebook_tab_changed)

    def texts_notebook_tab_changed(self, event):
        "Synchronize selected in treeview with tab change."
        text = self.texts_notebook_lookup[self.texts_notebook.select()]
        self.treeview.selection_set(text.fullname)
        self.treeview.focus(text.fullname)

    def texts_notebook_populate(self):
        """Display tabs for the texts notebook; first delete any existing tabs.
        Also updates the text information in the treeview.
        """
        while self.texts_notebook_lookup:
            self.texts_notebook.forget(self.texts_notebook_lookup.popitem()[0])
        for text in self.source.all_texts:
            text.viewer = viewer = Viewer(self.texts_notebook, self, text)
            # XXX
            # try:
            #     viewer.move_cursor(self.config["items"][filepath].get("cursor"))
            # except KeyError:
            #     pass
            self.texts_notebook.add(viewer.frame, text=viewer.name,
                                    state=text.shown and tk.NORMAL or tk.HIDDEN)
            tabs = self.texts_notebook.tabs()
            text.tabid = tabs[-1]
            self.texts_notebook_lookup[text.tabid] = text
            opener = functools.partial(self.open_editor, text=text)
            viewer.view.bind("<Double-Button-1>", opener)
            viewer.view.bind("<Return>", opener)
            self.treeview_set_info(text)

    def meta_notebook_create(self):
        "Create the meta notebook framework."
        self.meta_notebook = ttk.Notebook(self.panedwindow)
        self.panedwindow.add(self.meta_notebook, minsize=constants.PANE_MINSIZE)

         # key: tabid; value: instance
        self.meta_notebook_lookup = dict()

        self.title_viewer = TitleViewer(self.meta_notebook, self)
        self.meta_notebook.add(self.title_viewer.frame, text="Title")
        self.title_viewer.tabid = self.meta_notebook.tabs()[-1]
        self.meta_notebook_lookup[self.title_viewer.tabid] = self.title_viewer

        self.references_viewer = ReferencesViewer(self.meta_notebook, self)
        self.meta_notebook.add(self.references_viewer.frame, text="References")
        self.references_viewer.tabid = self.meta_notebook.tabs()[-1]
        self.meta_notebook_lookup[self.references_viewer.tabid] = self.references_viewer

        self.indexed_viewer = IndexedViewer(self.meta_notebook, self)
        self.meta_notebook.add(self.indexed_viewer.frame, text="Indexed")
        self.indexed_viewer.tabid = self.meta_notebook.tabs()[-1]
        self.meta_notebook_lookup[self.indexed_viewer.tabid] = self.indexed_viewer

        self.todo_viewer = TodoViewer(self.meta_notebook, self)
        self.meta_notebook.add(self.todo_viewer.frame, text="To do")
        self.todo_viewer.tabid = self.meta_notebook.tabs()[-1]
        self.meta_notebook_lookup[self.todo_viewer.tabid] = self.todo_viewer

        self.search_viewer = SearchViewer(self.meta_notebook, self)
        self.meta_notebook.add(self.search_viewer.frame, text="Search")
        self.search_viewer.tabid = self.meta_notebook.tabs()[-1]
        self.meta_notebook_lookup[self.search_viewer.tabid] = self.search_viewer

        self.help_viewer = HelpViewer(self.meta_notebook, self)
        self.meta_notebook.add(self.help_viewer.frame, text="Help")
        self.help_viewer.tabid = self.meta_notebook.tabs()[-1]
        self.meta_notebook_lookup[self.help_viewer.tabid] = self.help_viewer

    def meta_notebook_populate(self):
        "Populate the meta notebook with contents; help panel does not change."
        self.title_viewer.display()
        self.references_viewer.display()
        self.indexed_viewer.display()
        self.search_viewer.display()
        self.todo_viewer.display()

    def archive(self):
        count = self.source.archive()
        tk.messagebox.showinfo(title="Archive file written.",
                               message=f"{count} items written to archive file.")

    def quit(self, event=None):
        for editor in self.editors.values():
            try:
                if editor.is_modified:
                    if not tk_messagebox.askokcancel(
                            parent=self.root,
                            title="Quit?",
                            message="All unsaved changes will be lost. Really quit?"):
                        return
                    break
            except KeyError:
                pass
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
        self.treeview_populate()        # XXX Optimize!
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
        self.treeview_populate()        # XXX Optimize!
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
        newname = tk_simpledialog.askstring(
            parent=self.root,
            title="New name",
            prompt="Give the new name for the item",
            initialvalue=item.name)
        if not newname:
            return
        if newname == item.name:
            return
        try:
            item.rename(newname)
        except ValueError as error:
            tk_messagebox.showerror(
                parent=self.treeview,
                title="Error",
                message=str(error))
            return
        if item.is_text:
            index = self.treeview.index(fullname)
            self.treeview.delete(fullname)
            self.add_treeview_entry(item, index=index)
            self.texts_notebook.tab(item.tabid, text=item.name)
            item.viewer.redisplay()
        elif item.is_section:
            self.treeview_populate()        # XXX Optimize!
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
            tk_messagebox.showerror(
                parent=self.treeview,
                title="Error",
                message="Could not generate a unique name for the copy.")
            return
        self.treeview_populate()        # XXX Optimize!
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
            if not tk_messagebox.askokcancel(
                    parent=self.treeview,
                    title="Delete text?",
                    message=f"Really delete text '{item.fullname}'?"):
                return
        elif item.is_section:
            if not tk_messagebox.askokcancel(
                    parent=self.treeview,
                    title="Delete section?",
                    message=f"Really delete section '{item.fullname}' and all its contents?"):
                return
        if item.is_text:
            self.treeview.delete(fullname)
            self.texts_notebook.forget(item.tabid)
            self.texts_notebook_lookup.pop(item.tabid)
            item.delete()
        else:
            item.delete()
            self.treeview_populate()        # XXX Optimize!
            self.treeview.update()
            self.texts_notebook_populate()  # XXX Optimize!
            self.texts_notebook.update()
        self.source.check_integrity()
        self.config_save()

    def open_editor(self, event=None, text=None):
        if text is None:
            try:
                fullname = self.treeview.selection()[0]
            except IndexError:
                return "break"
            text = self.source[fullname]
            if not text.is_text:
                return "break"
        try:
            editor = self.editors[text.fullname]
        except KeyError:
            editor = Editor(self, text)
            self.editors[text.fullname] = editor
        else:
            editor.toplevel.lift()
        self.set_menubar_state()
        editor.view.focus_set()
        return "break"

    def close_editor(self, text):
        self.treeview_set_info(text)
        self.editors.pop(text.fullname)
        self.set_menubar_state()

    def disallow_open_editors(self):
        "If there are any open editors, then display error message and return True."

    def create_text(self):
        try:
            fullname = self.treeview.selection()[0]
        except IndexError:
            return
        anchor = self.source[fullname]
        name = tk_simpledialog.askstring(
            parent=self.treeview,
            title="New section",
            prompt="Give name of the new text")
        if not name:
            return
        try:
            text = self.source.create_text(anchor, name)
        except ValueError as error:
            tk_messagebox.showerror(
                parent=self.treeview,
                title="Error",
                message=str(error))
            return
        self.treeview_populate()        # XXX Optimize!
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
        name = tk_simpledialog.askstring(
            parent=self.treeview,
            title="New text",
            prompt="Give name of the new section")
        if not name:
            return
        try:
            section = self.source.create_section(anchor, name)
        except ValueError as error:
            tk_messagebox.showerror(
                parent=self.treeview,
                title="Error",
                message=str(error))
            return
        self.treeview_populate()        # XXX Optimize!
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
                sys.exit(f"Error: '{absdirpath}' does not exist.")
            if not os.path.isdir(absdirpath):
                sys.exit(f"Error: '{absdirpath}' is not a directory.")
    elif len(sys.argv) == 1:
        absdirpath = os.getcwd()
    else:
        sys.exit("Error: at most one directory path can be provided.")
    main = Main(absdirpath)
    main.mainloop()
