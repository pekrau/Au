"Authoring editor based on Tkinter."

import functools
import json
import os
import shutil

import tkinter as tk
from tkinter import ttk
from tkinter import filedialog as tk_filedialog
from tkinter import messagebox as tk_messagebox
from tkinter import simpledialog as tk_simpledialog

from icecream import ic

import constants
import editor
import utils
import help_text

VERSION = (0, 2, 1)


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
        self.menubar.add_command(label="Au",
                                 font=(constants.FONT_FAMILY, 14, "bold"),
                                 background="gold")

        self.menu_file = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_file, label="File")
        self.menu_file.add_command(label="Save configuration",
                                   command=self.save_configuration,
                                   accelerator="Ctrl-S")
        self.root.bind("<Control-s>", self.save_configuration)
        self.menu_file.add_command(label="Save texts", command=self.save_texts)
        self.menu_file.add_separator()
        self.menu_file.add_command(label="Quit", command=self.quit)

        self.menu_edit = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_edit, label="Edit")
        self.menu_edit.add_command(label="Rename section", command=self.rename_section)
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
        self.menu_edit.add_command(label="Delete text", command=self.delete_text)
        self.menu_edit.add_separator()
        self.menu_edit.add_command(label="Move item up",
                                   command=self.move_item_up,
                                   accelerator="Ctrl-Up")
        self.menu_edit.add_command(label="Move item down",
                                   command=self.move_item_down,
                                   accelerator="Ctrl-Down")
        self.menu_edit.add_command(label="Move item into subtree",
                                   command=self.move_item_into_subtree,
                                   accelerator="Ctrl-Left")
        self.menu_edit.add_command(label="Move item out of subtree",
                                   command=self.move_item_out_of_subtree,
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
        self.treeview.bind("<Control-Right>", self.move_item_into_subtree)
        self.treeview.bind("<Control-Left>", self.move_item_out_of_subtree)

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
        first = None
        for filepath in texts:
            if first is None:
                first = filepath
            self.add_treeview_entry(filepath)
        if first:
            self.treeview.selection_set(first)
            self.treeview.focus(first)

    def add_treeview_entry(self, filepath):
        section, filename = os.path.split(filepath)
        name, ext = os.path.splitext(filename)
        absfilepath = os.path.join(self.absdirpath, filepath)
        if ext == ".md":
            self.treeview.insert(section,
                                 tk.END,
                                 iid=filepath,
                                 text=name,
                                 tags=(filepath, ),
                                 values=("?", utils.get_timestamp(absfilepath)))
            self.treeview.tag_bind(filepath,
                                   "<Double-Button-1>",
                                   functools.partial(self.open_text, filepath=filepath))
            self.texts[filepath] = dict()
        elif os.path.isdir(absfilepath):
            self.treeview.insert(section,
                                 tk.END,
                                 iid=filepath,
                                 text=name,
                                 tags=("section", filepath))

    def flag_treeview_entry(self, filepath, modified=True):
        tags = set(self.treeview.item(filepath, "tags"))
        if modified:
            tags.add("modified")
        else:
            tags.discard("modified")
        self.treeview.item(filepath, tags=tuple(tags))

    def rename_section(self):
        pass

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
                                    message="Selected item is no a text.")
            return
        oldabspath = os.path.join(self.absdirpath, oldpath)
        newname = self.get_newname(parent=parent)
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

    def get_newname(self, parent=None):
        return tk_simpledialog.askstring(
            parent=parent or self.root,
            title="New name",
            prompt="Give the new name for the item:")

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
        return "break"

    def move_item_into_subtree(self, event=None):
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
                    title="Error",
                    message="Cannot move item into section; name collision.")
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
                    values=("?", utils.get_timestamp(newabspath)))
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

    def move_item_out_of_subtree(self, event=None):
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
                    title="Error",
                    message="Cannot move item out of section; name collision.")
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
                                     values=("?", utils.get_timestamp(newabspath)))
                
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

    def move_to_subtree(self, oldpath, newpath):
        pass

    def create_section(self):
        dirpath = tk_filedialog.askdirectory(
            parent=self.root,
            title="Create section directory",
            initialdir=self.absdirpath)
        if not dirpath:
            return
        if not dirpath.startswith(self.absdirpath):
            tk_messagebox.showerror(
                parent=self.root,
                title="Wrong directory",
                message=f"Must be subdirectory of '{self.absdirpath}'.")
            return
        subdirpath = dirpath[len(self.absdirpath)+1:]
        if os.path.isdir(dirpath):
            tk_messagebox.showerror(
                parent=self.root,
                title="Already exists",
                message=f"The section name '{subdirpath}' is already in use.")
            return
        if os.path.splitext(dirpath)[1]:
            tk_messagebox.showerror(
                parent=self.root,
                title="Contains extension",
                message=f"The section name '{subdirpath}' may not contain an extension.")
            return
        os.makedirs(dirpath)
        self.treeview.insert(os.path.split(subdirpath)[0],
                             tk.END,
                             iid=dirpath,
                             text=os.path.basename(subdirpath),
                             tags=("section", dirpath,))

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
                          f"{archivedirpath}/{filename} {utils.get_timestamp()}")
        # Remove the entry in the main window.
        self.treeview.delete(dirpath)
        # Actually remove the directory and files.
        shutil.rmtree(absdirpath)

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

    def create_text(self, event=None):
        try:
            dirpath = self.treeview.selection()[0]
            absdirpath = os.path.join(self.absdirpath, dirpath)
            if not os.path.isdir(absdirpath):
                raise ValueError
        except (IndexError, ValueError):
            absdirpath = self.absdirpath
        filepath = tk_filedialog.asksaveasfilename(
            parent=self.root,
            title="Create text file",
            initialdir=absdirpath,
            filetypes=[("Markdown files", "*.md")],
            defaultextension=".md",
            confirmoverwrite=False)
        if not filepath:
            return
        if not filepath.startswith(self.absdirpath):
            tk_messagebox.showerror(
                parent=self.root,
                title="Wrong directory",
                message=f"Must be (subdirectory of) {self.absdirpath}")
            return
        if os.path.splitext(filepath)[1] != ".md":
            tk_messagebox.showerror(
                parent=self.root,
                title="Wrong extension",
                message="File extension must be '.md'.")
            return
        if os.path.exists(filepath):
            tk_messagebox.showerror(
                parent=self.root,
                title="Exists",
                message=f"The text file '{filepath}'  already exists.")
            return
            
        with open(filepath, "w") as outfile:
            pass                # Empty file
        filepath = filepath[len(self.absdirpath)+1:]
        self.add_treeview_entry(filepath)
        self.open_text(filepath=filepath)

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
        archivedfilepath = os.path.join(self.absdirpath, constants.ARCHIVE_DIRNAME, f"{filepath} {utils.get_timestamp()}")
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
        self.configuration["texts"] = dict([(f, dict()) for f in self.get_ordered_items()])
        for filepath, text in self.texts.items():
            try:
                editor = text["editor"]
            except KeyError:
                pass
            else:
                self.configuration["texts"][filepath] = editor.get_configuration()
        with open(self.configurationpath, "w") as outfile:
            json.dump(self.configuration, outfile, indent=2)

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
