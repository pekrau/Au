"Authoring editor based on Tkinter."

import functools
import json
import os
import shutil

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox as tk_messagebox
from tkinter import simpledialog as tk_simpledialog
from tkinter import font as tk_font

from icecream import ic

import constants
import editor
import utils
import help_text
import docx_interface

VERSION = (0, 3, 0)


class Main:
    "Root window listing sections and texts."

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
        self.texts = dict()
        self.links_lookup = dict()

        self.root = tk.Tk()
        constants.FONT_FAMILIES = frozenset(tk_font.families())
        self.root.title(os.path.basename(dirpath))
        self.root.geometry(self.configuration["main"].get("geometry", constants.DEFAULT_ROOT_GEOMETRY))
        self.root.option_add("*tearOff", tk.FALSE)
        self.root.minsize(400, 400)
        self.root.bind_all("<Control-h>", self.open_help_text)
        self.au64 = tk.PhotoImage(data=constants.AU64)
        self.root.iconphoto(False, self.au64, self.au64)
        self.root.protocol("WM_DELETE_WINDOW", self.quit)

        self.menubar = tk.Menu(self.root)
        self.root["menu"] = self.menubar
        assert constants.FONT_FAMILY_NORMAL in constants.FONT_FAMILIES
        self.menubar.add_command(label="Au",
                                 font=(constants.FONT_FAMILY_NORMAL, 14, "bold"),
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
        self.menu_edit.add_command(label="Create text",
                                   command=self.create_text,
                                   accelerator="Ctrl-N")
        self.menu_edit.add_command(label="Copy text", command=self.copy_text)
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
                                     columns=("characters", "timestamp"),
                                     selectmode="browse")
        self.treeview.tag_configure("section", background=constants.SECTION_COLOR)
        self.treeview.tag_configure("modified", background=constants.MODIFIED_COLOR)
        self.treeview.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.treeview.heading("#0", text="Text")
        self.treeview.heading("characters", text="Characters")
        self.treeview.column("characters",
                             anchor=tk.E,
                             minwidth=6*constants.FONT_NORMAL_SIZE,
                             width=10*constants.FONT_NORMAL_SIZE)
        self.treeview.heading("timestamp", text="Timestamp")
        self.treeview.column("timestamp", anchor=tk.CENTER)
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

        self.treeview.bind("<Button-3>", self.popup_right_click_menu)

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

    def popup_right_click_menu(self, event):
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
        texts = self.configuration["texts"].copy()

        # Get directories and files that actually exist.
        pos = len(self.absdirpath) + 1
        archivedirpath = os.path.join(self.absdirpath, constants.ARCHIVE_DIRNAME)
        existing_items = set()
        for dirpath, dirnames, filenames in os.walk(self.absdirpath):
            if dirpath.startswith(archivedirpath):
                continue
            filename = dirpath[pos:]
            if filename:
                existing_items.add(filename)
            for filename in filenames:
                if filename.endswith(constants.CONFIGURATION_FILENAME): continue
                if filename.endswith(constants.HELP_FILENAME): continue
                existing_items.add(os.path.join(dirpath, filename)[pos:])

        # Remove files that do not exist.
        for filename in set(texts.keys()).difference(existing_items):
            texts.pop(filename)

        # Add files and dirs that exist, but are not in the configuration.
        for filename in existing_items.difference(texts.keys()):
            texts[filename] = dict()

        # Set up the treeview display.
        first = True
        for filepath in texts:
            self.add_treeview_entry(filepath, set_selection=first)
            if first:
                first = False

    def add_treeview_entry(self, itempath, set_selection=False):
        section, itemname = os.path.split(itempath)
        name, ext = os.path.splitext(itemname)
        absitempath = os.path.join(self.absdirpath, itempath)
        if ext == ".md":
            self.treeview.insert(section,
                                 tk.END,
                                 iid=itempath,
                                 text=name,
                                 tags=(itempath, ),
                                 values=("?", utils.get_time(absitempath)))
            self.treeview.tag_bind(itempath,
                                   "<Double-Button-1>",
                                   functools.partial(self.open_text, filepath=itempath))
            self.texts[itempath] = dict()
        elif os.path.isdir(absitempath):
            self.treeview.insert(section,
                                 tk.END,
                                 iid=itempath,
                                 text=name,
                                 tags=("section", itempath))
        if set_selection:
            self.treeview.see(itempath)
            self.treeview.selection_set(itempath)

    def flag_treeview_entry(self, filepath, modified=True):
        tags = set(self.treeview.item(filepath, "tags"))
        if modified:
            tags.add("modified")
        else:
            tags.discard("modified")
        self.treeview.item(filepath, tags=tuple(tags))

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
        "Move the currently selected item down one level in the treeview."
        try:
            oldpath = self.treeview.selection()[0]
        except IndexError:
            pass
        else:
            prevpath = self.treeview.prev(oldpath)
            if not prevpath:    # This item is first.
                return
            dirpath, ext = os.path.splitext(prevpath)
            if ext:             # Previous item is a text, not a section.
                return
            newpath = os.path.join(dirpath, os.path.basename(oldpath))
            newabspath = os.path.join(self.absdirpath, newpath)
            if os.path.exists(newabspath):
                tk_messagebox.showerror(
                    parent=self.root,
                    title="Name exists",
                    message="Cannot move item into section; name already exists.")
                return

            # This works for both text file and section directory.
            os.rename(os.path.join(self.absdirpath, oldpath), newabspath)

            # Move text file.
            if os.path.isfile(newabspath):
                self.texts[newpath] = self.texts.pop(oldpath)
                try:
                    ed = self.texts[newpath]["editor"]
                except KeyError:
                    pass
                else:
                    ed.filepath = newpath
                    ed.toplevel.title(os.path.splitext(newpath)[0])
                self.treeview.insert(
                    dirpath,
                    tk.END,
                    iid=newpath,
                    text=os.path.splitext(os.path.split(newpath)[1])[0],
                    tags=(newpath, ),
                    values=("?", utils.get_time(newabspath)))
                self.treeview.tag_bind(
                    newpath,
                    "<Double-Button-1>",
                    functools.partial(self.open_text, filepath=newpath))
            # XXX Move section and its items.
            else:
                ic("move dir and change all its children")
            self.treeview.delete(oldpath)
            self.treeview.selection_set(newpath)
            self.treeview.see(newpath)
            self.treeview.focus(newpath)
            self.save_configuration()
        finally:
            return "break"

    def move_item_out_of_section(self, event=None):
        "Move the currently selected item up one level in the treeview."
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
            newpath = os.path.join(superparent, filename)
            newabspath = os.path.join(self.absdirpath, newpath)
            if os.path.exists(newabspath):
                tk_messagebox.showerror(
                    parent=self.root,
                    title="Name exists",
                    message="Cannot move item out of section; name already exists.")
                return
            os.rename(os.path.join(self.absdirpath, oldpath), newabspath)
            # Move text file.
            if os.path.isfile(newabspath):
                self.texts[newpath] = self.texts.pop(oldpath)
                try:
                    self.texts[newpath]["editor"].rename(newpath)
                except KeyError:
                    pass
                self.treeview.insert(superparent,
                                     parentindex+1,
                                     iid=newpath,
                                     text=os.path.splitext(filename)[0],
                                     tags=(newpath, ),
                                     values=("?", utils.get_time(newabspath)))
                
                self.treeview.tag_bind(
                    newpath,
                    "<Double-Button-1>",
                    functools.partial(self.open_text, filepath=newpath))
            # XXX Move section and its items.
            else:
                ic("move dir and change all its children")
            self.treeview.delete(oldpath)
            self.treeview.selection_set(newpath)
            self.treeview.see(newpath)
            self.treeview.focus(newpath)
            self.save_configuration()
        finally:
            return "break"

    def rename_section(self, parent=None):
        ic("'rename_section' not implemented")
        self.save_configuration()

    def copy_section(self, parent=None):
        ic("'copy_section' not implemented")
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
                          f"{archivedirpath}/{filename} {utils.get_time()}")
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
            ed = self.texts[filepath]["editor"] = editor.Editor(self, filepath)
        self.treeview.see(filepath)
        ed.text.focus_set()

    def rename_text(self, parent=None, oldpath=None):
        "Rename text; to be called via menu entry."
        if oldpath is None:
            try:
                oldpath = self.treeview.selection()[0]
            except IndexError:
                return
        section, oldname = os.path.split(oldpath)
        oldname, ext = os.path.splitext(oldname)
        if ext != ".md":
            tk_messagebox.showerror(title="Error",
                                    message="Selected item is not a text.")
            return
        oldabspath = os.path.join(self.absdirpath, oldpath)
        newname = tk_simpledialog.askstring(
            parent=parent or self.root,
            title="New name",
            prompt="Give the new name for the text:",
            initialvalue=oldname)
        newname = os.path.splitext(newname)[0]
        newpath = os.path.join(section, newname)
        newpath += ".md"
        self.texts[newpath] = self.texts.pop(oldpath)
        index = self.treeview.index(oldpath)
        values = self.treeview.item(oldpath, "values")
        selected = self.treeview.selection()
        self.treeview.delete(oldpath)
        self.treeview.insert(
            section,
            index,
            iid=newpath,
            text=newname,
            tags=(newpath, ),
            values=values)
        self.treeview.tag_bind(
            newpath,
            "<Double-Button-1>",
            functools.partial(self.open_text, filepath=newpath))
        try:
            ed = self.texts[newpath]["editor"]
        except KeyError:
            pass
        else:
            ed.toplevel.title(os.path.join(section, newname))
            ed.filepath = newpath
        os.rename(os.path.join(self.absdirpath, oldpath),
                  os.path.join(self.absdirpath, newpath))
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
                                        f"{filepath} {utils.get_time()}")
        archivepath = os.path.dirname(archivedfilepath)
        if not os.path.exists(archivepath):
            os.makedirs(archivepath)
        # Move current file to archive.
        os.rename(os.path.join(self.absdirpath, filepath), archivedfilepath)

    def save_texts(self, event=None):
        "Save contents of all open text editor windows, and the configuration."
        for text in self.texts.values():
            try:
                text["editor"].save()
            except KeyError:
                pass

    def save_configuration(self, event=None):
        """Save the current configuration. 
        The contents of the dictionary must first be updated.
        Get geometry and item order from the respective widgets.
        """
        self.configuration["main"]["geometry"] = self.root.geometry()
        if self.help_text:
            self.configuration["help"] = self.help_text.get_configuration()
        else:
            self.configuration["help"] = dict()
        # Get the order of the texts as shown in the treeview.
        # This relies on the dictionary keeping the order of the items.
        self.configuration["texts"] = dict([(f, dict()) 
                                            for f in self.get_ordered_items()])
        for filepath, text in self.texts.items():
            try:
                editor = text["editor"]
            except KeyError:
                pass
            else:
                self.configuration["texts"][filepath] = editor.get_configuration()
        with open(self.configurationpath, "w") as outfile:
            json.dump(self.configuration, outfile, indent=2)
        ic("saved configuration")

    def write_docx(self):
        title = os.path.basename(self.absdirpath)
        absfilepath = os.path.join(self.absdirpath, title + ".docx")
        if os.path.exists(absfilepath):
            archivedfilepath = os.path.join(self.absdirpath,
                                            constants.ARCHIVE_DIRNAME,
                                            f"{title} {utils.get_time()}" + ".docx")
            os.rename(absfilepath, archivedfilepath)
        docx_interface.Writer(self.absdirpath, self.texts).write()

    def write_pdf(self):
        ic("'Create PDF' not implemented")

    def write_epub(self):
        ic("'Create EPUB' not implemented")

    def quit(self, event=None):
        for text in self.texts.values():
            try:
                if text["editor"].is_modified:
                    if not tk_messagebox.askokcancel(
                            parent=self.root,
                            title="Quit?",
                            message="All unsaved changes will be lost. Really quit?"):
                        return
            except KeyError:
                pass
        self.root.destroy()

    def get_ordered_items(self):
        "Get the full names of all items in the treeview."
        names = []
        for name in self.treeview.get_children():
            names.append(name)
            names.extend(self.get_children(name))
        return names

    def get_children(self, parentname):
        "Get the full names of all items recursively below the given parent."
        names = []
        for child in self.treeview.get_children(parentname):
            names.append(child)
            names.extend(self.get_children(child))
        return names

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
