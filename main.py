"Authoring editor based on Tkinter."

import json
import os
import shutil

import tkinter as tk
from tkinter import ttk
from tkinter import filedialog
from tkinter import messagebox

import constants
import editor
import utils

VERSION = (0, 1, 0)


class Main:
    "Root window listing sections and texts."

    def __init__(self, absdirpath):
        self.absdirpath = absdirpath
        try:
            with open(self.configurationpath) as infile:
                self.configuration = json.load(infile)
            if "main" not in self.configuration:
                raise ValueError
        except (OSError, json.JSONDecodeError, ValueError):
            self.configuration = dict(main=dict(), texts=dict())
        self.texts = dict()
        self.links_lookup = dict()

        self.root = tk.Tk()
        self.root.title(os.path.basename(dirpath))
        self.root.geometry(self.configuration["main"].get("geometry", constants.DEFAULT_ROOT_GEOMETRY))
        self.root.option_add("*tearOff", tk.FALSE)
        self.au64 = tk.PhotoImage(data=constants.AU64)
        self.root.iconphoto(False, self.au64)
        self.root.minsize(400, 400)

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
        self.menu_edit.add_command(label="Create section", command=self.create_section)
        self.menu_edit.add_command(label="Delete section", command=self.delete_section)
        self.menu_edit.add_separator()
        self.menu_edit.add_command(label="Create text", command=self.create_text)
        self.menu_edit.add_separator()
        self.menu_edit.add_command(label="Move item up",
                                   command=self.move_item_up,
                                   accelerator="Ctrl-up")
        self.menu_edit.add_command(label="Move item down",
                                   command=self.move_item_down,
                                   accelerator="Ctrl-down")
        self.menu_edit.add_command(label="Move item into subtree",
                                   command=self.move_item_into_subtree,
                                   accelerator="Ctrl-down")
        self.menu_edit.add_command(label="Move item out of subtree",
                                   command=self.move_item_out_of_subtree,
                                   accelerator="Ctrl-up")

        self.menubar.add_command(label="Help", command=self.help)

        self.treeview_frame = ttk.Frame(self.root, padding=4)
        self.treeview_frame.pack(fill=tk.BOTH, expand=1)
        self.treeview_frame.rowconfigure(0, weight=1)
        self.treeview_frame.columnconfigure(0, weight=1)
        self.treeview = ttk.Treeview(self.treeview_frame,
                                     columns=("characters", "timestamp"),
                                     selectmode="browse")
        self.treeview.tag_configure("section", background="gainsboro")
        self.treeview.tag_configure("modified", background="lightpink")
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

        self.treeview.bind("<Control-Up>", self.move_item_up)
        self.treeview.bind("<Control-Down>", self.move_item_down)
        self.treeview.bind("<Control-Right>", self.move_item_into_subtree)
        self.treeview.bind("<Control-Left>", self.move_item_out_of_subtree)

        self.setup_treeview()

        for filepath, config in self.configuration["texts"].items():
            if config.get("geometry"):
                self.open(filepath)
        self.treeview.focus_set()

        self.root.update_idletasks()
        self.save_configuration()

    def help(self, event=None):
        print("help")

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
                if not filename.endswith(constants.CONFIGURATION_FILENAME):
                    existing_items.add(os.path.join(dirpath, filename)[pos:])

        # Remove files that do not exist.
        for filename in set(texts.keys()).difference(existing_items):
            texts.pop(filename)

        # Add files and dirs that exist, but are not in the configuration.
        for filename in existing_items.difference(texts.keys()):
            print(f"add {filename}")
            texts[filename] = dict()

        # Set up the treeview display.
        for filepath in texts:
            parent, filename = os.path.split(filepath)
            name, ext = os.path.splitext(filename)
            absfilepath = os.path.join(self.absdirpath, filepath)
            if ext == ".md":
                self.treeview.insert(parent, tk.END, iid=filepath, text=name,
                                     tags=(filepath, ),
                                     values=("?", utils.get_timestamp(absfilepath)))
                self.treeview.tag_bind(filepath,
                                       "<Double-Button-1>",
                                       OpenEditor(self, filepath))
                self.texts[filepath] = dict()
            else:
                self.treeview.insert(parent, tk.END, iid=filepath, text=name,
                                     tags=("section", filepath))

    def move_item_up(self, event=None):
        "Move the currently selected item up in its level of the treeview."
        try:
            selection = self.treeview.selection()
            if not selection:
                raise ValueError
        except ValueError:
            pass
        else:
            iid = selection[0]
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
            selection = self.treeview.selection()
            if not selection:
                raise ValueError
        except ValueError:
            pass
        else:
            iid = selection[0]
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
            selection = self.treeview.selection()
            if not selection:
                raise ValueError
        except ValueError:
            pass
        else:
            iid = selection[0]
            parent = self.treeview.parent(iid)
            index = self.treeview.index(iid)
            # XXX actually move it
        return "break"

    def move_item_out_of_subtree(self, event=None):
        "Move the currently selected item up one level in the treeview."
        try:
            selection = self.treeview.selection()
            if not selection:
                raise ValueError
        except ValueError:
            pass
        else:
            iid = selection[0]
            parent = self.treeview.parent(iid)
            index = self.treeview.index(iid)
            # XXX actually move it
        return "break"

    def open(self, filepath):
        try:
            ed = self.texts[filepath]["editor"]
            ed.toplevel.lift()
        except KeyError:
            ed = self.texts[filepath]["editor"] = editor.Editor(self, filepath)
        ed.text.focus_set()

    def create_section(self):
        dirpath = filedialog.askdirectory(parent=self.root,
                                          title="Create section directory",
                                          initialdir=self.absdirpath)
        if not dirpath:
            return
        if not dirpath.startswith(self.absdirpath):
            messagebox.showerror(parent=self.root,
                                 title="Wrong directory",
                                 message=f"Must be subdirectory of '{self.main.absdirpath}'.")
            return
        subdirpath = dirpath[len(self.absdirpath)+1:]
        if os.path.isdir(dirpath):
            messagebox.showerror(parent=self.root,
                                 title="Already exists",
                                 message=f"The section name '{subdirpath}' is already in use.")
            return
        if os.path.splitext(dirpath)[1]:
            messagebox.showerror(parent=self.root,
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
        if not messagebox.askokcancel(title="Really delete section?",
                                      message=f"Do you wish to delete the section '{dirpath}' and all its contents?"):
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
                    editor = self.texts[subfilepath]["editor"]
                except KeyError:
                    pass
                else:
                    editor.close(force=True)
            for filename in filenames:
                os.rename(os.path.join(sectiondir, filename),
                          f"{archivedirpath}/{filename} {utils.get_timestamp()}")
        # Remove the entry in the main window.
        self.treeview.delete(dirpath)
        # Actually remove the directory and files.
        shutil.rmtree(absdirpath)

    def create_text(self):
        try:
            dirpath = self.treeview.selection()[0]
            absdirpath = os.path.join(self.absdirpath, dirpath)
            if not os.path.isdir(absdirpath):
                raise ValueError
        except (IndexError, ValueError):
            absdirpath = self.absdirpath
        filepath = filedialog.asksaveasfilename(parent=self.root,
                                                title="Create text file",
                                                initialdir=absdirpath,
                                                filetypes=[("Markdown files", "*.md")],
                                                defaultextension=".md",
                                                confirmoverwrite=False)
        if not filepath:
            return
        if not filepath.startswith(self.absdirpath):
            messagebox.showerror(parent=self.root,
                                 title="Wrong directory",
                                 message=f"Must be (subdirectory of) {self.main.absdirpath}")
            return
        if os.path.splitext(filepath)[1] != ".md":
            messagebox.showerror(parent=self.root,
                                 title="Wrong extension",
                                 message="File extension must be '.md'.")
            return
        if os.path.exists(filepath):
            messagebox.showerror(parent=self.root,
                                 title="Exists",
                                 message=f"The text file '{filepath}'  already exists.")
            return
            
        with open(filepath, "w") as outfile:
            pass                # Empty file
        filepath = filepath[len(self.absdirpath)+1:]
        self.add_text_to_treeview(filepath)
        self.open(filepath)

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
        # Get the order of the texts as shown in the treeview.
        # This relies on the dictionary keeping the order of the items.
        self.configuration["texts"] = dict([(f, dict()) for f in self.get_ordered_items()])
        for filepath, text in self.texts.items():
            try:
                editor = text["editor"]
            except KeyError:
                pass
            else:
                self.configuration["texts"][filepath] = dict(geometry=editor.toplevel.geometry())
        with open(self.configurationpath, "w") as outfile:
            json.dump(self.configuration, outfile, indent=2)

    def quit(self, event=None):
        for text in self.texts.values():
            try:
                if text["editor"].modified:
                    if not messagebox.askokcancel(parent=self.root,
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


class OpenEditor:
    "Action to open an editor window."

    def __init__(self, main, path):
        self.main = main
        self.path = path

    def __call__(self, event):
        self.main.open(self.path)



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
