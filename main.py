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
import docx_interface
import utils
from text_viewer import TextViewer
from meta_viewers import ReferencesViewer, IndexedViewer, TodoViewer, HelpViewer
from text_editor import TextEditor


class Main:
    """Main window containing three panes:
    1) The tree of sections and texts.
    2) The notebook containing tabs for all top-level texts.
    3) The notebook with references, indexed and help.
    """

    def __init__(self, absdirpath):
        self.absdirpath = absdirpath
        self.config_read()
        self.items_setup()

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
        self.root.bind("<F12>", self.debug)

        # Must be 'tk.PanedWindow', since the 'paneconfigure' command is needed.
        self.panedwindow = tk.PanedWindow(self.root,
                                          background="gold",
                                          orient=tk.HORIZONTAL,
                                          sashwidth=5)
        self.panedwindow.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Create the graphics interface.
        self.menubar_setup()
        self.treeview_create()
        self.texts_notebook_create()
        self.meta_notebook_create()

        self.render()

    @property
    def configpath(self):
        return os.path.join(self.absdirpath, constants.CONFIG_FILENAME)

    def config_read(self):
        "Read the configuration file."
        try:
            with open(self.configpath) as infile:
                self.config = json.load(infile)
            if "main" not in self.config:
                raise ValueError # When invalid JSON.
        except (OSError, json.JSONDecodeError, ValueError):
            self.config = dict(main=dict(), texts=dict())

    def config_save(self):
        "Save the current config. Get current state from the respective widgets."
        config = dict(main=dict(
            geometry=self.root.geometry(),
            sash=[self.panedwindow.sash("coord", 0)[0],
                  self.panedwindow.sash("coord", 1)[0]],
            texts=dict(
                selected=self.texts_notebook_lookup[self.texts_notebook.select()]["filepath"]),
            meta=dict(
                selected=str(self.meta_notebook_lookup[self.meta_notebook.select()]))))

        # Save the current cut-and-paste buffer.
        config["paste_buffer"] = self.paste_buffer

        # Get current state for texts and sections.
        config["items"] = dict()
        for filepath in self.treeview_all_items():
            if filepath.endswith(constants.MARKDOWN_EXT):
                data = dict(cursor=item[filepath]["viewer"].cursor_normalized())
            else:
                data = dict(open=bool(self.treeview.item(filepath, "open")))
            config["items"][filepath] = data
        self.config["items"] = self.items

        with open(self.configpath, "w") as outfile:            
            json.dump(self.config, outfile, indent=2)

    def items_setup(self):
        """Read the items (texts and sections) from config, 
        correcting for which files and directories actually exist.
        """

        # Hard-wired special directories.
        archive_dirpath = os.path.join(self.absdirpath, constants.ARCHIVE_DIRNAME)
        todo_dirpath = os.path.join(self.absdirpath, constants.TODO_DIRNAME)
        references_dirpath = os.path.join(self.absdirpath, constants.REFERENCES_DIRNAME)

        # Collect directories and files that actually exist.
        # A dict is used since the set of existing files needs to be ordered.
        existing = dict()
        for absdirpath, dirnames, filenames in os.walk(self.absdirpath):
            # Skip special directories.
            if absdirpath.startswith(archive_dirpath):
                continue
            if absdirpath.startswith(references_dirpath):
                continue
            if absdirpath.startswith(todo_dirpath):
                continue
            dirpath = absdirpath[len(self.absdirpath)+1:]
            if dirpath:
                existing[dirpath] = None
            for filename in filenames:
                if filename.endswith(constants.CONFIG_FILENAME):
                    continue
                if filename.endswith(constants.HELP_FILENAME):
                    continue
                if not filename.endswith(constants.MARKDOWN_EXT):
                    continue
                existing[os.path.join(dirpath, filename)] = None

        # Use data from config that apply to existing files and directories.
        # This determines the order of the existing files and directories.
        # Items present in config but actually not existing will be ignored.
        self.items = dict()
        for filepath, item in self.config["items"].items():
            try:
                existing.pop(filepath)
            except KeyError:
                pass
            else:
                self.items[filepath] = item

        # Add actually existing files and directories not present in config.
        # These are appended to the end of the dict 'items'.
        for filepath in existing:
            self.items[filepath] = dict()

        # Setup the texts lookup.
        self.texts = dict()
        for filepath, item in self.items.items():
            if filepath.endswith(constants.MARKDOWN_EXT):
                self.texts[filepath] = item
                item["filepath"] = filepath

    def menubar_setup(self):
        self.menubar = tk.Menu(self.root, background="gold")
        self.root["menu"] = self.menubar
        self.menubar.add_command(label="Au", font=constants.FONT_LARGE_BOLD)

        self.menu_file = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_file, label="File")
        self.menu_file.add_command(label="Write DOCX", command=self.write_docx)
        self.menu_file.add_command(label="Write PDF", command=self.write_pdf)
        self.menu_file.add_command(label="Write EPUB", command=self.write_epub)
        self.menu_file.add_command(label="Write HTML", command=self.write_html)
        self.menu_file.add_separator()
        self.menu_file.add_command(label="Quit",
                                   command=self.quit,
                                   accelerator="Ctrl-Q")
        self.root.bind("<Control-q>", self.quit)

        self.menu_edit = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_edit, label="Edit")
        self.menu_edit.add_command(label="Move up",
                                   command=self.move_item_up,
                                   accelerator="Ctrl-Up")
        self.menu_edit.add_command(label="Move down",
                                   command=self.move_item_down,
                                   accelerator="Ctrl-Down")
        self.menu_edit.add_command(label="Move into section",
                                   command=self.move_item_into_section,
                                   accelerator="Ctrl-Left")
        self.menu_edit.add_command(label="Move out of section",
                                   command=self.move_item_out_of_section,
                                   accelerator="Ctrl-Right")

        self.section_menu = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.section_menu, label="Section")
        self.section_menu.add_command(label="Rename", command=self.section_rename)
        self.section_menu.add_command(label="Copy", command=self.section_copy)
        self.section_menu.add_command(label="Delete", command=self.section_delete)

        self.text_menu = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.text_menu, label="Text")
        self.text_menu.add_command(label="Edit", command=self.open_texteditor)
        self.text_menu.add_command(label="Rename", command=self.text_rename)
        self.text_menu.add_command(label="Copy", command=self.text_copy)
        self.text_menu.add_command(label="Delete", command=self.text_delete)

    def treeview_create(self):
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
        self.treeview.heading("#0", text="Text")
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

        self.treeview.bind("<Control-e>", self.open_texteditor)
        self.treeview.bind("<Control-n>", self.text_create)
        self.treeview.bind("<Control-Up>", self.move_item_up)
        self.treeview.bind("<Control-Down>", self.move_item_down)
        self.treeview.bind("<Control-Right>", self.move_item_into_section)
        self.treeview.bind("<Control-Left>", self.move_item_out_of_section)

        self.treeview.bind("<Button-3>", self.popup_menu)
        self.treeview.bind("<Return>", self.view_text_tab)
        self.treeview.bind("<<TreeviewOpen>>", self.treeview_open)
        self.treeview.bind("<<TreeviewClose>>", self.treeview_close)
        self.treeview.focus_set()

    def treeview_render(self):
        for child in self.treeview.get_children():
            self.treeview.delete(child)
        first = True
        for itempath, item in self.items.items():
            self.add_treeview_entry(itempath, 
                                    set_selection=first,
                                    open=item.get("open", False))
            first = False

    def add_treeview_entry(self, itempath, set_selection=False, index=None, open=False):
        dirpath, itemname = os.path.split(itempath)
        absitempath = os.path.join(self.absdirpath, itempath)
        name, ext = os.path.splitext(itemname)
        if ext == constants.MARKDOWN_EXT:
            self.treeview.insert(dirpath,
                                 index or tk.END,
                                 iid=itempath,
                                 text=name,
                                 tags=(itempath, ))
            self.treeview.tag_bind(itempath,
                                   "<Button-1>",
                                   functools.partial(self.view_text_tab,
                                                     filepath=itempath))
            self.treeview.tag_bind(itempath,
                                   "<Double-Button-1>",
                                   functools.partial(self.open_texteditor,
                                                     filepath=itempath))
        elif not ext:
            self.treeview.insert(dirpath,
                                 index or tk.END,
                                 iid=itempath,
                                 text=name,
                                 open=open,
                                 tags=("?", "section", itempath))
        if set_selection:
            self.treeview.see(itempath)
            self.treeview.selection_set(itempath)

    def treeview_open(self, event=None, section=None):
        if section is None:
            section = self.treeview.focus()
        filepaths = [f for f in self.texts if os.path.dirname(f) == section]
        for filepath in filepaths:
            self.texts_notebook.add(self.texts[filepath]["tabid"])
        for subsection in self.treeview.get_children(section):
            if self.treeview.item(subsection, "open"):
                self.treeview_open(section=subsection)

    def treeview_close(self, event=None, section=None):
        if section is None:
            section = self.treeview.focus()
        for filepath, text in self.texts.items():
            if filepath.startswith(section):
                self.texts_notebook.hide(text["tabid"])

    def texts_notebook_create(self):
        "Create the texts notebook."
        self.texts_notebook = ttk.Notebook(self.panedwindow)
        self.panedwindow.add(self.texts_notebook, minsize=constants.PANE_MINSIZE)
         # Key: tabid; value: instance
        self.texts_notebook_lookup = dict()

    def texts_notebook_render(self):
        "Render tabs for the texts notebook; first delete any existing tabs."
        while self.texts_notebook_lookup:
            self.texts_notebook.forget(self.texts_notebook_lookup.popitem()[0])
        for filepath, text in self.texts.items():
            viewer = TextViewer(self.texts_notebook, self, filepath)
            try:
                viewer.move_cursor(self.config["items"][filepath].get("cursor"))
            except KeyError:
                pass
            text["viewer"] = viewer
            self.texts_notebook.add(viewer.frame, text=viewer.name)
            tabs = self.texts_notebook.tabs()
            text["tabid"] = tabs[-1]
            text["tabindex"] = len(tabs) - 1
            self.texts_notebook_lookup[text["tabid"]] = text
            opener = functools.partial(self.open_texteditor, filepath=filepath)
            viewer.text.bind("<Double-Button-1>", opener)
            viewer.text.bind("<Return>", opener)

    def texts_notebook_set_selected(self, filepath):
        for tabid, text in self.texts_notebook_lookup.items():
            if text["filepath"] == filepath:
                try:
                    self.texts_notebook.select(tabid)
                except tk.TclError:
                    pass
                break

    def meta_notebook_create(self):
        "Create the meta content notebook."
        self.meta_notebook = ttk.Notebook(self.panedwindow)
        self.panedwindow.add(self.meta_notebook, minsize=constants.PANE_MINSIZE)

         # key: tabid; value: instance
        self.meta_notebook_lookup = dict()

        self.references = ReferencesViewer(self.meta_notebook, self)
        self.meta_notebook.add(self.references.frame, text="References")
        tabs = self.meta_notebook.tabs()
        self.meta_notebook_lookup[tabs[-1]] = self.references

        self.indexed = IndexedViewer(self.meta_notebook, self)
        self.meta_notebook.add(self.indexed.frame, text="Indexed")
        tabs = self.meta_notebook.tabs()
        self.meta_notebook_lookup[tabs[-1]] = self.indexed

        self.todo = TodoViewer(self.meta_notebook, self)
        self.meta_notebook.add(self.todo.frame, text="To do")
        tabs = self.meta_notebook.tabs()
        self.meta_notebook_lookup[tabs[-1]] = self.todo

        filepath = os.path.join(os.path.dirname(__file__), constants.HELP_FILENAME)
        self.help = HelpViewer(self.meta_notebook, self, filepath)
        self.meta_notebook.add(self.help.frame, text="Help")
        tabs = self.meta_notebook.tabs()
        self.meta_notebook_lookup[tabs[-1]] = self.help

    def meta_notebook_render(self):
        "Render the meta content notebook."
        self.references.render()
        self.indexed.render()
        self.todo.render()

    def config_apply(self):
        "Configure up windows and tabs."
        # The paste buffer is global to all editors, to facilitate cut-and-paste.
        self.paste_buffer = self.config.get("paste_buffer") or list()

        # Placement of paned window sashes.
        try:
            sash = self.config["main"]["sash"]
        except KeyError:
            pass
        else:
            self.panedwindow.update() # Has to be here for this to work.
            self.panedwindow.sash("place", 0, sash[0], 1)
            self.panedwindow.sash("place", 1, sash[1], 1)

        # Hide sections in texts notebook to agree with treeview.
        for filepath, item in self.config["items"].items():
            if filepath.endswith(constants.MARKDOWN_EXT):
                continue
            if not item.get("open"):
                self.treeview_close(section=filepath)

        # Set selected tab in notebooks.
        selected = self.config["main"]["texts"].get("selected")
        # Skip if it has been renamed.
        if selected in self.texts:
            self.treeview.selection_set(selected)
            self.treeview.focus(selected)
            self.treeview.see(selected)
            self.texts_notebook_set_selected(selected)

        selected = self.config["main"]["meta"].get("selected")
        for tabid, viewer in self.meta_notebook_lookup.items():
            if str(viewer) == selected:
                try:
                    self.meta_notebook.select(tabid)
                except tk.TclError:
                    pass
                break

    def render(self):
        "Re-render the contents of all three panels."
        self.treeview_render()
        self.texts_notebook_render()
        self.treeview_update_info()
        self.meta_notebook_render()
        self.config_apply()

    def treeview_update_info(self):
        "Update status, chars and age of text entries."
        for filepath in self.texts:
            self.set_treeview_info(filepath)

    def set_treeview_info(self, filepath):
        text = self.texts[filepath]
        try:
            modified = text["editor"].is_modified
        except KeyError:
            modified = False
        tags = set(self.treeview.item(filepath, "tags"))
        if modified:
            tags.add("modified")
        else:
            tags.discard("modified")
        self.treeview.item(filepath, tags=tuple(tags))
        try:
            viewer = text["viewer"]
        except KeyError:
            pass
        else:
            self.treeview.set(filepath, "status", str(viewer.status))
            self.treeview.set(filepath, "chars", viewer.character_count)
            age = viewer.age
            self.treeview.set(filepath, "age", f"{age[0]} {age[1]}")

    def treeview_rename_children(self, newdirpath, olddirpath, children):
        for oldpath in children:
            newpath = os.path.join(newdirpath, oldpath[len(olddirpath)+1:])
            self.texts[newpath] = self.texts.pop(oldpath)
            try:
                editor = self.texts[newpath]["editor"]
            except KeyError:
                pass
            else:
                editor.filepath = newpath
                editor.toplevel.title(os.path.splitext(newpath)[0])
            self.add_treeview_entry(newpath)

    def view_text_tab(self, event=None, filepath=None):
        if filepath is None:
            filepath = self.treeview.focus()
        try:
            self.texts_notebook.select(self.texts[filepath]["tabid"])
        except KeyError:
            pass

    def move_item_up(self, event=None):
        "Move the currently selected item up within its level of the treeview."
        try:
            filepath = self.treeview.selection()[0]
        except IndexError:
            return "break"

        parent = self.treeview.parent(filepath)
        old_index = self.treeview.index(filepath)
        max_index = len(self.treeview.get_children(parent)) - 1
        # Moving up implies decreasing the index.
        new_index = old_index - 1
        # Wrap around within level.
        if new_index < 0:
            new_index = max_index
        if new_index == old_index:
            return "break"

        ic(filepath, parent, old_index, new_index)
        self.treeview.move(filepath, parent, new_index)
        self.config_save()
        self.render()
        return "break"

    def move_item_down(self, event=None):
        "Move the currently selected item down within its level of the treeview."
        try:
            filepath = self.treeview.selection()[0]
        except IndexError:
            return "break"

        parent = self.treeview.parent(filepath)
        old_index = self.treeview.index(filepath)
        max_index = len(self.treeview.get_children(parent)) - 1
        # Moving down implies increasing the index.
        new_index = old_index + 1
        # Wrap around within level.
        if new_index > max_index:
            new_index = 0
        if new_index == old_index:
            return "break"

        self.treeview.move(filepath, parent, new_index)
        self.config_save()
        self.render()
        return "break"

    def move_item_into_section(self, event=None):
        "Move the currently selected item down one level in hierarchy."
        try:
            oldpath = self.treeview.selection()[0]
        except IndexError:
            return "break"

        prevpath = self.treeview.prev(oldpath)
        if not prevpath:    # This item is first; no section to move into.
            return "break"
        dirpath, ext = os.path.splitext(prevpath)
        if ext:             # Previous item is a text; no section to move into.
            return "break"

        oldabspath = os.path.join(self.absdirpath, oldpath)
        newpath = os.path.join(dirpath, os.path.basename(oldpath))
        newabspath = os.path.join(self.absdirpath, newpath)
        if os.path.exists(newabspath):
            tk_messagebox.showerror(
                parent=self.root,
                title="Name exists",
                message="Cannot move item into section; name already exists.")
            return "break"

        # Move on disk; this works for both text file and section directory.
        os.rename(oldabspath, newabspath)

        # # Move text file entry in treeview.
        # if os.path.isfile(newabspath):
        #     self.texts[newpath] = self.texts.pop(oldpath)
        #     try:
        #         ed = self.texts[newpath]["editor"]
        #     except KeyError:
        #         pass
        #     else:
        #         ed.filepath = newpath
        #         ed.toplevel.title(os.path.splitext(newpath)[0])
        #     self.treeview.delete(oldpath)
        #     self.add_treeview_entry(newpath)

        #     self.treeview.selection_set(newpath)
        #     self.treeview.see(newpath)
        #     self.treeview.focus(newpath)

        # # Move section and its items into the given section.
        # elif os.path.isdir(newabspath):
        #     olddirpath = oldpath
        #     newdirpath = newpath
        #     children = self.get_all_treeview_items(olddirpath)
        #     # This removes all children entries in the treeview.
        #     self.treeview.delete(olddirpath)
        #     self.add_treeview_entry(newdirpath)

        #     for oldpath in children:
        #         self.texts[newpath] = self.texts.pop(oldpath)
        #         try:
        #             ed = self.texts[newpath]["editor"]
        #         except KeyError:
        #             pass
        #         else:
        #             ed.filepath = newpath
        #             ed.toplevel.title(os.path.splitext(newpath)[0])
        #         newpath = os.path.join(newdirpath, oldpath[len(olddirpath)+1:])
        #         self.add_treeview_entry(newpath)

        #     self.treeview.selection_set(newdirpath)
        #     self.treeview.see(newdirpath)
        #     self.treeview.focus(newdirpath)

        # else:
        #     ic("No such old item", newabspath)

        self.config_save()
        self.render()
        return "break"

    def move_item_out_of_section(self, event=None):
        "Move the currently selected item up one level in the hierachy."
        try:
            oldpath = self.treeview.selection()[0]
        except IndexError:
            return "break"

        parent, filename = os.path.split(oldpath)
        # Already at top level.
        if not parent:
            return "break"

        parentindex = self.treeview.index(parent)
        superparent = os.path.split(parent)[0]
        oldabspath = os.path.join(self.absdirpath, oldpath)
        newpath = os.path.join(superparent, filename)
        newabspath = os.path.join(self.absdirpath, newpath)
        if os.path.exists(newabspath):
            tk_messagebox.showerror(
                parent=self.root,
                title="Name exists",
                message="Cannot move item out of section; name already exists.")
            return "break"

        # Move on disk; this works for both text file and section directory.
        os.rename(oldabspath, newabspath)

        # # Move text file entry in treeview.
        # if os.path.isfile(newabspath):
        #     self.texts[newpath] = self.texts.pop(oldpath)
        #     try:
        #         self.texts[newpath]["editor"].rename(newpath)
        #     except KeyError:
        #         pass
        #     self.treeview.delete(oldpath)
        #     self.add_treeview_entry(newpath, index=parentindex+1)

        #     self.treeview.selection_set(newpath)
        #     self.treeview.see(newpath)
        #     self.treeview.focus(newpath)

        # # Move section and its items out of the current section in treeview.
        # elif os.path.isdir(newabspath):
        #     olddirpath = oldpath
        #     newdirpath = newpath
        #     children = self.get_all_treeview_items(olddirpath)

        #     # This removes all children entries in the treeview.
        #     self.treeview.delete(olddirpath)

        #     self.add_treeview_entry(newdirpath, index=parentindex+1)
        #     self.treeview_rename_children(newdirpath, olddirpath, children)

        #     self.treeview.selection_set(newdirpath)
        #     self.treeview.see(newdirpath)
        #     self.treeview.focus(newdirpath)

        # else:
        #     ic("No such old item", newabspath)

        self.config_save()
        self.render()
        return "break"

    def section_rename(self):
        try:
            oldpath = self.treeview.selection()[0]
        except IndexError:
            return

        oldabspath = os.path.join(self.absdirpath, oldpath)
        if not os.path.isdir(oldabspath):
            return
        dirpath, oldname = os.path.split(oldpath)
        newname = tk_simpledialog.askstring(
            parent=self.root,
            title="New name",
            prompt="Give the new name for the section:",
            initialvalue=oldname)
        if not newname:
            return
        if newname == oldname:
            return
        try:
            utils.check_invalid_characters(newname)
        except ValueError as error:
            tk_messagebox.showerror(
                title="Error",
                message=str(error))
            return
        newpath = os.path.join(dirpath, newname)
        newabspath = os.path.join(self.absdirpath, newpath)
        if os.path.exists(newabspath):
            tk_messagebox.showerror(title="Exists",
                                    message="The name is already in use.")
            return

        # Rename the actual directory.
        os.rename(oldabspath, newabspath)

        # oldindex = self.treeview.index(oldpath)
        # oldopen = self.treeview.item(oldpath, "open")
        # children = self.get_all_treeview_items(oldpath)

        # # This removes all children entries in the treeview.
        # self.treeview.delete(oldpath)

        # self.add_treeview_entry(newpath, index=oldindex, open=oldopen)
        # self.treeview_rename_children(newpath, oldpath, children)
        # self.treeview.selection_set(newpath)
        # self.treeview.see(newpath)
        # self.treeview.focus(newpath)
        self.config_save()
        self.render()

    def section_copy(self):
        try:
            oldpath = self.treeview.selection()[0]
        except IndexError:
            return
        oldabspath = os.path.join(self.absdirpath, oldpath)
        if not os.path.isdir(oldabspath):
            return
        dirpath, oldname = os.path.split(oldpath)
        newname = tk_simpledialog.askstring(
            parent=self.root,
            title="Name",
            prompt="Give the name for the section copy:",
            initialvalue=f"Copy of {oldname}")
        if not newname:
            return
        if os.path.splitext(newname)[1]:
            tk_messagebox.showerror(title="Error",
                                    message="New name may not contain an extension.")
            return
        if os.path.split(newname)[0]:
            tk_messagebox.showerror(title="Error",
                                    message="New name may not contain a directory.")
            return
        newpath = os.path.join(dirpath, newname)
        newabspath = os.path.join(self.absdirpath, newpath)
        if os.path.exists(newabspath):
            tk_messagebox.showerror(title="Exists",
                                    message="The name is already in use.")
            return

        # Make copy on disk.
        shutil.copytree(oldabspath, newabspath)

        # oldindex = self.treeview.index(oldpath)
        # self.add_treeview_entry(newpath, index=oldindex+1)
        # for dirpath, dirnames, filenames in os.walk(newabspath):
        #     for dirname in dirnames:
        #         self.add_treeview_entry(os.path.join(newpath, dirname))
        #     for filename in filenames:
        #         self.add_treeview_entry(os.path.join(newpath, filename))

        # self.treeview.see(newpath)
        # self.treeview.focus(newpath)

        self.config_save()
        self.render()

    def section_create(self, parent=None):
        try:
            dirpath = self.treeview.selection()[0]
            absdirpath = os.path.join(self.absdirpath, dirpath)
        except IndexError:
            absdirpath = self.absdirpath
        if os.path.isfile(absdirpath):
            absdirpath = os.path.split(absdirpath)[0]
            dirpath = absdirpath[len(self.absdirpath)+1:]
        name = tk_simpledialog.askstring(
            parent=parent or self.root,
            title="New section",
            prompt=f"Give name of new section within section '{dirpath}':")
        if not name:
            return
        name = os.path.splitext(name)[0]
        dirpath = os.path.join(dirpath, name)
        absdirpath = os.path.normpath(os.path.join(self.absdirpath, dirpath))
        if not absdirpath.startswith(self.absdirpath):
            tk_messagebox.showerror(
                parent=self.root,
                title="Wrong directory",
                message=f"Must be within '{self.absdirpath}'")
            return
        if os.path.exists(absdirpath):
            tk_messagebox.showerror(
                parent=self.root,
                title="Name exists",
                message=f"The section '{dirpath}' already exists.")
            return

        os.makedirs(absdirpath)
        # self.add_treeview_entry(dirpath, set_selection=True)
        self.config_save()
        self.render()

    def section_delete(self):
        selection = self.treeview.selection()
        if not selection:
            return
        dirpath = selection[0]
        if not dirpath:
            return
        absdirpath = os.path.join(self.absdirpath, dirpath)
        if not os.path.isdir(absdirpath):
            return
        if not tk_messagebox.askokcancel(
                title="Delete section?",
                message=f"Really delete section '{dirpath}' and all its contents?"):
            return
        section = list(os.walk(absdirpath))
        archivepath = os.path.join(self.absdirpath, constants.ARCHIVE_DIRNAME)
        if not os.path.exists(archivepath):
            os.makedirs(archivepath)
        for sectiondir, dirnames, filenames in section:
            subdirpath = sectiondir[len(self.absdirpath)+1:]
            # Archive the files.
            archivedirpath = os.path.join(archivepath, sectiondir)
            if not os.path.exists(archivedirpath):
                os.mkdir(archivedirpath)
            for filename in filenames:
                os.rename(os.path.join(sectiondir, filename),
                          f"{archivedirpath}/{filename} {utils.get_now()}")
        # Actually remove the directory and files.
        shutil.rmtree(absdirpath)

        # # Remove the entry in the main window.
        # self.treeview.delete(dirpath)

        self.config_save()
        self.render()

    def open_texteditor(self, event=None, filepath=None):
        if filepath is None:
            try:
                filepath = self.treeview.selection()[0]
            except IndexError:
                pass
        text = self.texts[filepath]
        try:
            ed = text["editor"]
        except KeyError:
            ed = text["editor"] = TextEditor(self, filepath)
        else:
            ed.toplevel.lift()
        self.treeview.see(filepath)
        ed.move_cursor(self.config["items"][filepath].get("cursor"))
        ed.text.update()
        # ed.text.focus_set()
        return "break"

    def text_rename(self, parent=None, oldpath=None):
        if oldpath is None:
            try:
                oldpath = self.treeview.selection()[0]
            except IndexError:
                return

        section, oldname = os.path.split(oldpath)
        oldname, ext = os.path.splitext(oldname)
        if ext != constants.MARKDOWN_EXT:
            tk_messagebox.showerror(parent=parent or self.root,
                                    title="Not a text",
                                    message="Selected item is not a text.")
            return
        oldabspath = os.path.join(self.absdirpath, oldpath)
        newname = tk_simpledialog.askstring(
            parent=parent or self.root,
            title="New name",
            prompt="Give the new name for the text:",
            initialvalue=oldname)
        if not newname:
            return
        if newname == oldname:
            return
        try:
            utils.check_invalid_characters(newname)
        except ValueError as error:
            tk_messagebox.showerror(
                title="Error",
                message=str(error))
            return

        newpath = os.path.join(section, newname)
        newpath += constants.MARKDOWN_EXT
        newabspath = os.path.join(self.absdirpath, newpath)
        if os.path.exists(newabspath):
            tk_messagebox.showerror(parent=parent or self.root,
                                    title="Exists",
                                    message="The name is already in use.")
            return

        # Keep order in texts dict.
        items = []
        for filepath, text in self.texts.items():
            if filepath == oldpath:
                items.append((newpath, text))
            else:
                items.append((filepath, text))
        self.texts = dict(items)

        os.rename(oldabspath, newabspath)

        # oldindex = self.treeview.index(oldpath)
        # oldselection = self.treeview.selection() == oldpath
        # self.treeview.delete(oldpath)
        # self.add_treeview_entry(newpath, set_selection=oldselection, index=oldindex)
        # self.treeview.selection_set(newpath)
        # self.treeview.see(newpath)
        # self.treeview.focus(newpath)
        self.config_save()
        self.render()

    def text_create(self, event=None, parent=None):
        try:
            dirpath = self.treeview.selection()[0]
            absdirpath = os.path.join(self.absdirpath, dirpath)
        except IndexError:
            absdirpath = self.absdirpath
        if os.path.isfile(absdirpath):
            absdirpath = os.path.split(absdirpath)[0]
            dirpath = absdirpath[len(self.absdirpath)+1:]
        name = tk_simpledialog.askstring(
            parent=parent or self.root,
            title="New text",
            prompt=f"Give name of new text within section '{dirpath}':")
        if not name:
            return
        name = os.path.splitext(name)[0]
        filepath = os.path.join(dirpath, name + constants.MARKDOWN_EXT)
        absfilepath = os.path.normpath(os.path.join(self.absdirpath, filepath))
        if not absfilepath.startswith(self.absdirpath):
            tk_messagebox.showerror(
                parent=self.root,
                title="Wrong directory",
                message=f"Must be within '{self.absdirpath}'")
            return
        if os.path.exists(absfilepath):
            tk_messagebox.showerror(
                parent=self.root,
                title="Name exists",
                message=f"The text '{filepath}' already exists.")
            return
            
        with open(absfilepath, "w") as outfile:
            pass                # Empty file.

        self.config_save()
        self.render()
        self.open_texteditor(filepath=filepath)

    def text_copy(self):
        try:
            filepath = self.treeview.selection()[0]
            absfilepath = os.path.join(self.absdirpath, filepath)
        except IndexError:
            return

        dirpath, filename = os.path.split(filepath)
        if not os.path.isfile(absfilepath):
            tk_messagebox.showerror(
                parent=self.root,
                title="Not text",
                message=f"The selected item '{filepath}' is not a text.")
            return

        dirpath, filename = os.path.split(filepath)
        newfilename = f"Copy of {filename}"
        newfilepath = os.path.join(dirpath, newfilename)
        newabsfilepath = os.path.join(self.absdirpath, newfilepath)
        if os.path.exists(newabsfilepath):
            counter = 1
            while counter < 100:
                counter += 1
                newfilename = f"Copy {counter} of {filename}"
                newfilepath = os.path.join(dirpath, newfilename)
                newabsfilepath = os.path.join(self.absdirpath, newfilepath)
                if not os.path.exists(newabsfilepath):
                    break
                else:
                    tk_messagebox.showerror(
                        parent=self.root,
                        title="Name exists",
                        message=f"Could not generate a unique name.")
                    return
        shutil.copy(absfilepath, newabsfilepath)

        self.config_save()
        self.render()

    def text_delete(self, filepath=None, force=False):
        if filepath is None:
            try:
                filepath = self.treeview.selection()[0]
            except IndexError:
                return
        if not filepath.endswith(constants.MARKDOWN_EXT):
            return
        if not os.path.isfile(os.path.join(self.absdirpath, filepath)):
            return
        if not force and not tk_messagebox.askokcancel(
                title="Delete text?",
                message=f"Really delete text '{filepath}'?"):
            return
        try:
            ed = self.texts[filepath]["editor"]
        except KeyError:
            pass
        else:
            ed.close(force=True)
        self.treeview.delete(filepath)
        text = self.texts.pop(filepath)
        self.texts_notebook.forget(text["tabid"])
        self.texts_notebook_lookup.pop(text["tabid"])
        self.move_file_to_archive(filepath)

        self.config_save()
        self.render()

    def text_rerender(self, filepath, cursor=None):
        if cursor:
            self.config["items"][filepath]["cursor"] = cursor
        self.texts[filepath]["viewer"].rerender()

    def move_file_to_archive(self, filepath):
        """Move the text file to the archive.
        Create the archive subdirectory if it does not exist.
        Append the current timestamp to the filename.
        """
        # Create archive subdirectory if it does not exist.
        archivedfilepath = os.path.join(self.absdirpath, 
                                        constants.ARCHIVE_DIRNAME, 
                                        f"{filepath} {utils.get_now()}")
        archivepath = os.path.dirname(archivedfilepath)
        if not os.path.exists(archivepath):
            os.makedirs(archivepath)
        # Move the given file to archive.
        os.rename(os.path.join(self.absdirpath, filepath), archivedfilepath)

    def popup_menu(self, event):
        path = self.treeview.identify_row(event.y)
        if not path: 
            return
        self.treeview.selection_set(path)
        abspath = os.path.join(self.absdirpath, path)
        if os.path.isdir(abspath):
            self.section_menu.tk_popup(event.x_root, event.y_root)
        elif os.path.isfile(abspath):
            self.text_menu.tk_popup(event.x_root, event.y_root)

    def write_docx(self):
        title = os.path.basename(self.absdirpath)
        absfilepath = os.path.join(self.absdirpath, title + ".docx")
        if os.path.exists(absfilepath):
            archivedfilepath = os.path.join(self.absdirpath,
                                            constants.ARCHIVE_DIRNAME,
                                            f"{title} {utils.get_now()}" + ".docx")
            os.rename(absfilepath, archivedfilepath)
        docx_interface.Writer(self.absdirpath, self.texts).write()

    def write_pdf(self):
        raise NotImplementedError

    def write_epub(self):
        raise NotImplementedError

    def write_html(self):
        raise NotImplementedError

    def quit(self, event=None):
        for text in self.texts.values():
            try:
                if text["editor"].is_modified:
                    if not tk_messagebox.askokcancel(
                            parent=self.root,
                            title="Quit?",
                            message="All unsaved changes will be lost. Really quit?"):
                        return
                    break
            except KeyError:
                pass
        self.root.destroy()

    def treeview_all_items(self, parent=None):
        "Get the full names of all items in the treeview."
        result = []
        if parent:
            items = self.treeview.get_children(parent)
        else:
            items = self.treeview.get_children()
        for path in items:
            result.append(path)
            result.extend(self.treeview_all_items(path))
        return result

    def debug(self, event=None):
        ic(self.texts_notebook.tabs(),
           self.texts_notebook.select(),
           self.meta_notebook.select())

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
