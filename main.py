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
import editor
import help_text
import utils

VERSION = (0, 5, 4)


class Main:
    "Root window showing the tree of sections and texts."

    def __init__(self, absdirpath):
        self.absdirpath = absdirpath
        try:
            with open(self.configurationpath) as infile:
                self.configuration = json.load(infile)
            if "main" not in self.configuration:
                raise ValueError # When invalid JSON.
            if "help" not in self.configuration:
                self.configuration["help"] = dict()
        except (OSError, json.JSONDecodeError, ValueError):
            self.configuration = dict(main=dict(), help=dict(), texts=dict())

        # All texts, with references to any open editor windows.
        self.texts = dict()
        # The links lookup is global to all editors, to facilitate cut-and-paste.
        self.links = dict()
        # The paste buffer is global to all editors, to facilitate cut-and-paste.
        self.paste_buffer = self.configuration.get("paste_buffer")

        self.root = tk.Tk()
        constants.FONT_FAMILIES = frozenset(tk_font.families())
        self.root.title(os.path.basename(dirpath))
        self.root.geometry(self.configuration["main"].get(
            "geometry", constants.DEFAULT_ROOT_GEOMETRY))
        self.root.option_add("*tearOff", tk.FALSE)
        self.root.minsize(400, 400)
        self.au64 = tk.PhotoImage(data=constants.AU64)
        self.root.iconphoto(False, self.au64, self.au64)
        self.root.protocol("WM_DELETE_WINDOW", self.quit)
        self.root.bind_all("<Control-h>", self.open_help_text)

        self.menubar = tk.Menu(self.root)
        self.root["menu"] = self.menubar
        assert constants.FONT_FAMILY_NORMAL in constants.FONT_FAMILIES
        self.menubar.add_command(label="Au",
                                 font=constants.FONT_LARGE_BOLD,
                                 background="gold")

        self.menu_file = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_file, label="File")
        self.menu_file.add_command(label="Save configuration",
                                   command=self.save_configuration,
                                   accelerator="Ctrl-S")
        self.root.bind("<Control-s>", self.save_configuration)
        self.menu_file.add_command(label="Save texts", command=self.save_texts)
        self.menu_file.add_separator()
        self.menu_file.add_command(label="Write DOCX", command=self.write_docx)
        self.menu_file.add_command(label="Write PDF", command=self.write_pdf)
        self.menu_file.add_command(label="Write EPUB", command=self.write_epub)
        self.menu_file.add_separator()
        self.menu_file.add_command(label="Quit", command=self.quit)

        self.menu_edit = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_edit, label="Edit")
        self.menu_edit.add_command(label="Rename section", command=self.rename_section)
        self.menu_edit.add_command(label="Copy section", command=self.copy_section)
        self.menu_edit.add_command(label="Create section", command=self.create_section)
        self.menu_edit.add_command(label="Delete section", command=self.delete_section)
        self.menu_edit.add_separator()
        self.menu_edit.add_command(label="Open text",
                                   command=self.open_text,
                                   accelerator="Ctrl-O")
        self.menu_edit.add_command(label="Rename text", command=self.rename_text)
        self.menu_edit.add_command(label="Copy text", command=self.copy_text)
        self.menu_edit.add_command(label="Create text",
                                   command=self.create_text,
                                   accelerator="Ctrl-N")
        self.menu_edit.add_command(label="Delete text", command=self.delete_text)
        self.menu_edit.add_separator()
        self.menu_edit.add_command(label="Move item up",
                                   command=self.move_item_up,
                                   accelerator="Ctrl-Up")
        self.menu_edit.add_command(label="Move item down",
                                   command=self.move_item_down,
                                   accelerator="Ctrl-Down")
        self.menu_edit.add_command(label="Move item into section",
                                   command=self.move_item_into_section,
                                   accelerator="Ctrl-Left")
        self.menu_edit.add_command(label="Move item out of section",
                                   command=self.move_item_out_of_section,
                                   accelerator="Ctrl-Right")

        self.menubar.add_command(label="Help", command=self.open_help_text)

        self.treeview_frame = ttk.Frame(self.root, padding=4)
        self.treeview_frame.pack(fill=tk.BOTH, expand=1)
        self.treeview_frame.rowconfigure(0, weight=1)
        self.treeview_frame.columnconfigure(0, weight=1)
        self.treeview = ttk.Treeview(self.treeview_frame,
                                     columns=("status", "size", "age"),
                                     selectmode="browse")
        self.treeview.tag_configure("section", background=constants.SECTION_COLOR)
        self.treeview.tag_configure("modified", background=constants.MODIFIED_COLOR)
        self.treeview.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.treeview.heading("#0", text="Text")
        self.treeview.heading("status", text="Status")
        self.treeview.heading("size", text="Size")
        self.treeview.heading("age", text="Age")
        self.treeview.column("status",
                             anchor=tk.E,
                             minwidth=4*constants.FONT_NORMAL_SIZE,
                             width=8*constants.FONT_NORMAL_SIZE)
        self.treeview.column("size",
                             anchor=tk.E,
                             minwidth=4*constants.FONT_NORMAL_SIZE,
                             width=8*constants.FONT_NORMAL_SIZE)
        self.treeview.column("age",
                             anchor=tk.E,
                             minwidth=4*constants.FONT_NORMAL_SIZE,
                             width=8*constants.FONT_NORMAL_SIZE)
        self.treeview_scroll_y = ttk.Scrollbar(self.treeview_frame,
                                               orient=tk.VERTICAL,
                                               command=self.treeview.yview)
        self.treeview_scroll_y.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.treeview.configure(yscrollcommand=self.treeview_scroll_y.set)

        self.treeview.bind("<Control-o>", self.open_text)
        self.treeview.bind("<Control-n>", self.create_text)
        self.treeview.bind("<Control-Up>", self.move_item_up)
        self.treeview.bind("<Control-Down>", self.move_item_down)
        self.treeview.bind("<Control-Right>", self.move_item_into_section)
        self.treeview.bind("<Control-Left>", self.move_item_out_of_section)

        self.treeview.bind("<Button-3>", self.popup_menu_right_click)

        self.section_menu = tk.Menu(self.treeview, tearoff=False)
        self.section_menu.add_command(label="Rename", command=self.rename_section)
        self.section_menu.add_command(label="Copy", command=self.copy_section)
        self.section_menu.add_command(label="Delete", command=self.delete_section)
        self.section_menu.add_separator()
        self.section_menu.add_command(label="Move up", command=self.move_item_up)
        self.section_menu.add_command(label="Move down", command=self.move_item_down)
        self.section_menu.add_command(label="Move into section",
                                      command=self.move_item_into_section)
        self.section_menu.add_command(label="Move out of section", 
                                      command=self.move_item_out_of_section)

        self.text_menu = tk.Menu(self.treeview, tearoff=False)
        self.text_menu.add_command(label="Open", command=self.open_text)
        self.text_menu.add_command(label="Rename", command=self.rename_text)
        self.text_menu.add_command(label="Copy", command=self.copy_text)
        self.text_menu.add_command(label="Delete", command=self.delete_text)
        self.text_menu.add_separator()
        self.text_menu.add_command(label="Move up", command=self.move_item_up)
        self.text_menu.add_command(label="Move down", command=self.move_item_down)
        self.text_menu.add_command(label="Move into section",
                                   command=self.move_item_into_section)
        self.text_menu.add_command(label="Move out of section",
                                   command=self.move_item_out_of_section)

        self.setup_treeview()
        self.root.update_idletasks()
        self.root.lift()

        for filepath in self.texts:
            try:
                config = self.configuration["texts"][filepath]
            except KeyError:
                pass
            else:
                if config.get("geometry"):
                    self.open_text(filepath=filepath)
        self.treeview.focus_set()

        if self.configuration["help"].get("geometry"):
            self.help_text = help_text.HelpText(self)
        else:
            self.help_text = None

        self.save_configuration()

    def popup_menu_right_click(self, event):
        path = self.treeview.identify_row(event.y)
        if not path: 
            return
        self.treeview.selection_set(path)
        abspath = os.path.join(self.absdirpath, path)
        if os.path.isdir(abspath):
            self.section_menu.tk_popup(event.x_root, event.y_root)
        elif os.path.isfile(abspath):
            self.text_menu.tk_popup(event.x_root, event.y_root)

    def open_help_text(self, event=None):
        if self.help_text is None:
            self.help_text = help_text.HelpText(self)
        self.help_text.toplevel.lift()
        return "break"

    @property
    def configurationpath(self):
        return os.path.join(self.absdirpath, constants.CONFIGURATION_FILENAME)

    def setup_treeview(self):
        "Insert the data for the treeview from the configuration."
        # Get directories and files that actually exist.
        pos = len(self.absdirpath) + 1
        archivedirpath = os.path.join(self.absdirpath, constants.ARCHIVE_DIRNAME)
        # The set of existing files needs to be ordered. Use dict.
        existing = dict()
        for absdirpath, dirnames, filenames in os.walk(self.absdirpath):
            if absdirpath.startswith(archivedirpath):
                continue
            dirpath = absdirpath[pos:]
            if dirpath:
                existing[dirpath] = None
            for filename in filenames:
                if filename.endswith(constants.CONFIGURATION_FILENAME): continue
                if filename.endswith(constants.HELP_FILENAME): continue
                if not filename.endswith(".md"): continue
                existing[os.path.join(dirpath, filename)] = None

        # Use data from configuration for existing files and directories.
        # Items in configuration but missing in existing will be ignored.
        texts = dict()
        for path, data in self.configuration["texts"].items():
            try:
                existing.pop(path)
                texts[path] = data
            except KeyError:
                pass

        # Add files and directories not present in configuration.
        for path in existing:
            texts[path] = dict()
        self.configuration["texts"] = texts

        # Set up the treeview display.
        first = True
        for path, data in texts.items():
            self.add_treeview_entry(path, set_selection=first, open=data.get("open", False))
            if first:
                first = False

    def add_treeview_entry(self, itempath, set_selection=False, index=None, open=False):
        dirpath, itemname = os.path.split(itempath)
        name, ext = os.path.splitext(itemname)
        absitempath = os.path.join(self.absdirpath, itempath)
        if ext == ".md":
            try:
                size = str(utils.get_size(absitempath))
                age, unit = utils.get_age(absitempath)
            except OSError:
                size = "?"
                age = "?"
                unit = ""
            self.treeview.insert(dirpath,
                                 index or tk.END,
                                 iid=itempath,
                                 text=name,
                                 tags=(itempath, ),
                                 values=("?", size, f"{age} {unit}"))
            self.treeview.tag_bind(itempath,
                                   "<Double-Button-1>",
                                   functools.partial(self.open_text, filepath=itempath))
            self.texts[itempath] = dict()
        elif not ext:
            self.treeview.insert(dirpath,
                                 index or tk.END,
                                 iid=itempath,
                                 text=name,
                                 open=open,
                                 tags=("?", "section", itempath))
        else:
            ic("Ignored file", itemname)
        if set_selection:
            self.treeview.see(itempath)
            self.treeview.selection_set(itempath)

    def rename_treeview_children(self, newdirpath, olddirpath, children):
        for oldpath in children:
            newpath = os.path.join(newdirpath, oldpath[len(olddirpath)+1:])
            self.texts[newpath] = self.texts.pop(oldpath)
            try:
                ed = self.texts[newpath]["editor"]
            except KeyError:
                pass
            else:
                ed.filepath = newpath
                ed.toplevel.title(os.path.splitext(newpath)[0])
            self.add_treeview_entry(newpath)

    def update_treeview_entry(self, filepath,
                              modified=None, status=None, size=None, age=None):
        if modified is not None:
            tags = set(self.treeview.item(filepath, "tags"))
            if modified:
                tags.add("modified")
            else:
                tags.discard("modified")
            self.treeview.item(filepath, tags=tuple(tags))
        if status is not None:
            self.treeview.set(filepath, "status", str(status))
        if size is not None:
            self.treeview.set(filepath, "size", size)
        if age is not None:
            self.treeview.set(filepath, "age", f"{age[0]} {age[1]}")

    def move_item_up(self, event=None):
        "Move the currently selected item up in its level of the treeview."
        try:
            iid = self.treeview.selection()[0]
        except IndexError:
            pass
        else:
            parent = self.treeview.parent(iid)
            index = self.treeview.index(iid)
            max_index = len(self.treeview.get_children(parent)) - 1
            index -= 1
            if index < 0:
                index = max_index
            self.treeview.move(iid, parent, index)
        self.save_configuration()
        return "break"

    def move_item_down(self, event=None):
        "Move the currently selected item down in its level of the treeview."
        try:
            iid = self.treeview.selection()[0]
        except IndexError:
            pass
        else:
            parent = self.treeview.parent(iid)
            index = self.treeview.index(iid)
            max_index = len(self.treeview.get_children(parent)) - 1
            index += 1
            if index > max_index:
                index = 0
            self.treeview.move(iid, parent, index)
        self.save_configuration()
        return "break"

    def move_item_into_section(self, event=None):
        "Move the currently selected item down one level in hierarchy."
        try:
            oldpath = self.treeview.selection()[0]
        except IndexError:
            pass
        else:
            prevpath = self.treeview.prev(oldpath)
            if not prevpath:    # This item is first; no section to move into.
                return
            dirpath, ext = os.path.splitext(prevpath)
            if ext:             # Previous item is a text; no section to move into.
                return

            oldabspath = os.path.join(self.absdirpath, oldpath)
            newpath = os.path.join(dirpath, os.path.basename(oldpath))
            newabspath = os.path.join(self.absdirpath, newpath)
            if os.path.exists(newabspath):
                tk_messagebox.showerror(
                    parent=self.root,
                    title="Name exists",
                    message="Cannot move item into section; name already exists.")
                return

            # Move on disk; this works for both text file and section directory.
            os.rename(oldabspath, newabspath)

            # Move text file entry in treeview.
            if os.path.isfile(newabspath):
                self.texts[newpath] = self.texts.pop(oldpath)
                try:
                    ed = self.texts[newpath]["editor"]
                except KeyError:
                    pass
                else:
                    ed.filepath = newpath
                    ed.toplevel.title(os.path.splitext(newpath)[0])
                self.treeview.delete(oldpath)
                self.add_treeview_entry(newpath)

                self.treeview.selection_set(newpath)
                self.treeview.see(newpath)
                self.treeview.focus(newpath)

            # Move section and its items into the given section.
            elif os.path.isdir(newabspath):
                olddirpath = oldpath
                newdirpath = newpath
                children = self.get_all_items(olddirpath)
                # This removes all children entries in the treeview.
                self.treeview.delete(olddirpath)
                self.add_treeview_entry(newdirpath)

                for oldpath in children:
                    self.texts[newpath] = self.texts.pop(oldpath)
                    try:
                        ed = self.texts[newpath]["editor"]
                    except KeyError:
                        pass
                    else:
                        ed.filepath = newpath
                        ed.toplevel.title(os.path.splitext(newpath)[0])
                    newpath = os.path.join(newdirpath, oldpath[len(olddirpath)+1:])
                    self.add_treeview_entry(newpath)

                self.treeview.selection_set(newdirpath)
                self.treeview.see(newdirpath)
                self.treeview.focus(newdirpath)

            else:
                ic("No such old item", newabspath)

            self.save_configuration()
        finally:
            return "break"

    def move_item_out_of_section(self, event=None):
        "Move the currently selected item up one level in the hierachy."
        try:
            oldpath = self.treeview.selection()[0]
        except IndexError:
            pass
        else:
            parent, filename = os.path.split(oldpath)
            # Already at top level.
            if not parent:
                return

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
                return

            # Move on disk; this works for both text file and section directory.
            os.rename(oldabspath, newabspath)

            # Move text file entry in treeview.
            if os.path.isfile(newabspath):
                self.texts[newpath] = self.texts.pop(oldpath)
                try:
                    self.texts[newpath]["editor"].rename(newpath)
                except KeyError:
                    pass
                self.treeview.delete(oldpath)
                self.add_treeview_entry(newpath, index=parentindex+1)

                self.treeview.selection_set(newpath)
                self.treeview.see(newpath)
                self.treeview.focus(newpath)

            # Move section and its items out of the current section in treeview.
            elif os.path.isdir(newabspath):
                olddirpath = oldpath
                newdirpath = newpath
                children = self.get_all_items(olddirpath)

                # This removes all children entries in the treeview.
                self.treeview.delete(olddirpath)

                self.add_treeview_entry(newdirpath, index=parentindex+1)
                self.rename_treeview_children(newdirpath, olddirpath, children)

                self.treeview.selection_set(newdirpath)
                self.treeview.see(newdirpath)
                self.treeview.focus(newdirpath)

            else:
                ic("No such old item", newabspath)

            self.save_configuration()
        finally:
            return "break"

    def rename_section(self):
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

        # Move on disk.
        os.rename(oldabspath, newabspath)

        oldindex = self.treeview.index(oldpath)
        oldopen = self.treeview.item(oldpath, "open")
        children = self.get_all_items(oldpath)

        # This removes all children entries in the treeview.
        self.treeview.delete(oldpath)

        self.add_treeview_entry(newpath, index=oldindex, open=oldopen)
        self.rename_treeview_children(newpath, oldpath, children)
        self.treeview.selection_set(newpath)

        self.treeview.see(newpath)
        self.treeview.focus(newpath)
        self.save_configuration()

    def copy_section(self):
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

        oldindex = self.treeview.index(oldpath)
        self.add_treeview_entry(newpath, index=oldindex+1)
        for dirpath, dirnames, filenames in os.walk(newabspath):
            for dirname in dirnames:
                self.add_treeview_entry(os.path.join(newpath, dirname))
            for filename in filenames:
                self.add_treeview_entry(os.path.join(newpath, filename))

        self.treeview.see(newpath)
        self.treeview.focus(newpath)
        self.save_configuration()

    def create_section(self, parent=None):
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
        self.add_treeview_entry(dirpath, set_selection=True)
        self.save_configuration()

    def delete_section(self):
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
            # 'join' does the wrong thing with directory name starting with period '.'.
            # archivedirpath = os.path.join(archivepath, sectiondir)
            archivedirpath = f"{archivepath}/{subdirpath}"
            if not os.path.exists(archivedirpath):
                os.mkdir(archivedirpath)
            # Close any open editors for the affected files.
            for filename in filenames:
                subfilepath = os.path.join(subdirpath, filename)
                try:
                    ed = self.texts[subfilepath]["editor"]
                except KeyError:
                    pass
                else:
                    ed.close(force=True)
            for filename in filenames:
                os.rename(os.path.join(sectiondir, filename),
                          f"{archivedirpath}/{filename} {utils.get_now()}")
        # Remove the entry in the main window.
        self.treeview.delete(dirpath)
        # Actually remove the directory and files.
        shutil.rmtree(absdirpath)
        self.save_configuration()

    def open_text(self, event=None, filepath=None):
        if filepath is None:
            try:
                filepath = self.treeview.selection()[0]
            except IndexError:
                pass
        try:
            ed = self.texts[filepath]["editor"]
            ed.toplevel.lift()
        except KeyError:
            config = self.configuration["texts"].setdefault(filepath, dict())
            ed = self.texts[filepath]["editor"] = editor.Editor(self, filepath, config)
        self.treeview.see(filepath)
        ed.text.focus_set()

    def rename_text(self, parent=None, oldpath=None):
        if oldpath is None:
            try:
                oldpath = self.treeview.selection()[0]
            except IndexError:
                return
        section, oldname = os.path.split(oldpath)
        oldname, ext = os.path.splitext(oldname)
        if ext != ".md":
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
        newname = os.path.splitext(newname)[0]
        if os.path.split(newname)[0]:
            tk_messagebox.showerror(parent=parent or self.root,
                                    title="Bad name",
                                    message="New name may not contain a directory.")
            return
        newpath = os.path.join(section, newname)
        newpath += ".md"
        newabspath = os.path.join(self.absdirpath, newpath)
        if os.path.exists(newabspath):
            tk_messagebox.showerror(parent=parent or self.root,
                                    title="Exists",
                                    message="The name is already in use.")
            return
        try:
            ed = self.texts[oldpath]["editor"]
        except KeyError:
            pass
        else:
            ed.toplevel.title(os.path.join(section, newname))
            ed.filepath = newpath
        self.texts[newpath] = self.texts.pop(oldpath)
        oldindex = self.treeview.index(oldpath)
        oldselection = self.treeview.selection() == oldpath
        self.treeview.delete(oldpath)
        self.add_treeview_entry(newpath, set_selection=oldselection, index=oldindex)
        self.treeview.selection_set(newpath)
        self.treeview.see(newpath)
        self.treeview.focus(newpath)
        os.rename(oldabspath, newabspath)
        self.save_configuration()

    def create_text(self, event=None, parent=None):
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
        filepath = os.path.join(dirpath, name + ".md")
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
            pass                # Empty file
        self.add_treeview_entry(filepath, set_selection=True)
        self.open_text(filepath=filepath)

    def copy_text(self):
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
        self.add_treeview_entry(newfilepath)

    def delete_text(self, filepath=None, force=False):
        if filepath is None:
            try:
                filepath = self.treeview.selection()[0]
            except IndexError:
                return
        if not filepath.endswith(".md"):
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
        self.move_file_to_archive(filepath)
        self.save_configuration()

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
        # Move current file to archive.
        os.rename(os.path.join(self.absdirpath, filepath), archivedfilepath)

    def new_link(self, url, title):
        # Links are not removed from 'main.lookup' during a session.
        # The link count must remain strictly increasing.
        tag = f"{constants.LINK_PREFIX}{len(self.links) + 1}"
        self.links[tag] = dict(tag=tag, url=url, title=title)
        return tag

    def save_texts(self, event=None):
        "Save contents of all open text editor windows, and the configuration."
        for text in self.texts.values():
            try:
                text["editor"].save_text()
            except KeyError:
                pass

    def save_configuration(self, event=None):
        """Save the current configuration. 
        The contents of the dictionary must first be updated.
        Get current state from the respective widgets.
        """
        self.configuration["main"]["geometry"] = self.root.geometry()
        self.configuration["paste_buffer"] = self.paste_buffer
        if self.help_text:
            self.configuration["help"] = dict(geometry=self.help_text.toplevel.geometry())
        else:
            self.configuration["help"] = dict()
        # Get the order of the texts as shown in the treeview.
        # This relies on the dictionary keeping the order of the items.
        self.configuration["texts"] = dict()
        for filepath in self.get_all_items():
            self.configuration["texts"][filepath] = conf = dict()
            try:
                editor = self.texts[filepath]["editor"]
            except KeyError:
                pass
            else:
                conf["geometry"] = editor.toplevel.geometry()
            if not filepath.endswith(".md"):
                conf["open"] = bool(self.treeview.item(filepath, "open"))
        with open(self.configurationpath, "w") as outfile:            
            json.dump(self.configuration, outfile, indent=2)
        print("saved configuration")

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

    def get_all_items(self, parent=None):
        "Get the full names of all items in the treeview."
        result = []
        if parent:
            items = self.treeview.get_children(parent)
        else:
            items = self.treeview.get_children()
        for path in items:
            result.append(path)
            result.extend(self.get_all_items(path))
        return result

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
    Main(absdirpath).mainloop()
