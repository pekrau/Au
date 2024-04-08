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


class Main:
    "Root window listing sections and texts."

    def __init__(self, absdirpath):
        self.absdirpath = absdirpath
        try:
            with open(self.statepath) as infile:
                self.state = json.load(infile)
            if "root" not in self.state:
                raise ValueError
            if "editors" not in self.state:
                raise ValueError
        except (OSError, json.JSONDecodeError, ValueError):
            self.state = dict(root=dict(), editors=dict())
        self.root = tk.Tk()
        self.root.title(os.path.basename(dirpath))
        self.root.geometry(self.state["root"].get("geometry", constants.DEFAULT_ROOT_GEOMETRY))
        self.root.option_add("*tearOff", tk.FALSE)
        self.au64 = tk.PhotoImage(data=constants.AU64)
        self.root.iconphoto(False, self.au64)
        self.root.minsize(400, 400)

        self.links_lookup = dict()

        self.menubar = tk.Menu(self.root)
        self.root["menu"] = self.menubar
        self.menubar.add_command(label="Au",
                                 font=(constants.FONT_FAMILY, 14, "bold"),
                                 background="gold")

        self.menu_file = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_file, label="File")
        self.menu_file.add_command(label="Save state",
                                   command=self.save_state,
                                   accelerator="Ctrl-S")
        self.root.bind("<Control-s>", self.save_state)
        self.menu_file.add_command(label="Save texts", command=self.save_texts)
        self.menu_file.add_separator()
        self.menu_file.add_command(label="Quit", command=self.quit)

        self.menu_edit = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_edit, label="Edit")
        self.menu_edit.add_command(label="Create section", command=self.create_section)
        self.menu_edit.add_command(label="Delete section", command=self.delete_section)
        self.menu_edit.add_separator()
        self.menu_edit.add_command(label="Create text", command=self.create_text)

        self.treeview_frame = ttk.Frame(self.root, padding=4)
        self.treeview_frame.pack(fill=tk.BOTH, expand=1)
        self.treeview_frame.rowconfigure(0, weight=1)
        self.treeview_frame.columnconfigure(0, weight=1)
        self.treeview = ttk.Treeview(self.treeview_frame,
                                     columns=("changed", "characters", "timestamp"),
                                     selectmode="browse")
        self.treeview.tag_configure("section", background="gainsboro")
        self.treeview.tag_configure("changed", background="lightpink")
        self.treeview.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.treeview.heading("#0", text="Text")
        self.treeview.heading("changed", text=" ", anchor=tk.CENTER)
        self.treeview.column("changed", 
                             anchor=tk.CENTER,
                             stretch=False,
                             minwidth=2*constants.FONT_NORMAL_SIZE,
                             width=2*constants.FONT_NORMAL_SIZE)
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

        self.texts = dict()
        self.add_dir_to_treeview()
        self.root.update_idletasks()

        for filepath, state in self.state["editors"].items():
            if state.get("open"):
                self.open(filepath)

    @property
    def statepath(self):
        return os.path.join(self.absdirpath, constants.STATE_FILENAME)

    def add_dir_to_treeview(self, subdirpath=""):
        if subdirpath:
            absdirpath = os.path.join(self.absdirpath, subdirpath)
        else:
            absdirpath = self.absdirpath
        itemnames = [n for n in os.listdir(absdirpath or ".") if not n.startswith(".")]
        for itemname in sorted(itemnames):
            filepath = os.path.join(subdirpath, itemname)
            if itemname.endswith(".md"):
                self.add_text_to_treeview(filepath)
            elif os.path.isdir(os.path.join(self.absdirpath, filepath)):
                self.treeview.insert(subdirpath,
                                     tk.END,
                                     iid=filepath,
                                     text=itemname,
                                     tags=("section", filepath, ))
                self.add_dir_to_treeview(filepath)
            else:
                pass            # Skip all other files.

    def add_text_to_treeview(self, filepath):
        parent, filename = os.path.split(filepath)
        self.texts[filepath] = dict()
        if not self.state["editors"].get(filepath):
            self.state["editors"][filepath] = dict(open=False)
        name = os.path.splitext(filename)[0]
        self.treeview.insert(parent, tk.END, iid=filepath, text=name, tags=(filepath, ))
        self.treeview.tag_bind(filepath,
                               "<Double-Button-1>",
                               OpenEditor(self, filepath))

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
        # Actually remove the files.
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
        "Save contents of all open text editor windows, and the state."
        for text in self.texts.values():
            try:
                text["editor"].save()
            except KeyError:
                pass
        self.save_state()

    def save_state(self, event=None):
        self.state["root"]["geometry"] = self.root.geometry()
        for filepath, text in self.texts.items():
            state = self.state["editors"][filepath]
            if state.get("open"):
                state["geometry"] = self.texts[filepath]["editor"].toplevel.geometry()
        with open(self.statepath, "w") as outfile:
            json.dump(self.state, outfile, indent=2)

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
