"Authoring editor based on Tkinter."

import json
import os
import re
import time
import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import webbrowser

import marko
import marko.ast_renderer


AU64 = "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAABhGlDQ1BJQ0MgcHJvZmlsZQAAKJF9kT1Iw0AcxV/TSkWqDnaQ4pChOlkQleKoVShChVArtOpgcv2EJg1Jiouj4Fpw8GOx6uDirKuDqyAIfoA4OzgpukiJ/0sKLWI8OO7Hu3uPu3eA0Kwy1QxMAKpmGelkQszmVsXgKwLwYwBxRGRm6nOSlILn+LqHj693MZ7lfe7P0Z8vmAzwicSzTDcs4g3i+Kalc94nDrOynCc+Jx436ILEj1xXXH7jXHJY4JlhI5OeJw4Ti6UuVrqYlQ2VeJo4mlc1yheyLuc5b3FWq3XWvid/YaigrSxzneYIkljEEiSIUFBHBVVYiNGqkWIiTfsJD3/E8UvkUshVASPHAmpQITt+8D/43a1ZnJp0k0IJoOfFtj9GgeAu0GrY9vexbbdOAP8zcKV1/LUmMPNJeqOjRY+AwW3g4rqjKXvA5Q4w/KTLhuxIfppCsQi8n9E35YChW6Bvze2tvY/TByBDXaVugINDYKxE2ese7+7t7u3fM+3+fgBwYnKmw5NibQAAAAZiS0dEAP8A/wD/oL2nkwAAAAlwSFlzAAAuIwAALiMBeKU/dgAAAAd0SU1FB+gEAw45EiZV65kAAAAZdEVYdENvbW1lbnQAQ3JlYXRlZCB3aXRoIEdJTVBXgQ4XAAADoklEQVR42u2aWUiUURTHf5qVLa6kIVZQUBptRLtKYVBhQUFky0NZ2fbQQ1ESREbLQxJCEe0RVIhJRSumJZGV5qRmlla2SZstlo6mUKk5PXz5kN77+c1iOTP3wMcM93/u3Lm/Ofeeew/jYXmKBTc2T9zcFAAFQAFQABQABUABUAAUAAVAAVAAFAAFQAFwP/OypVNlFfSNat+vygSBfi4YAaaHxvzyH7ngEmhuhlMXjPmmXgFLJ684elhbFH3+GsJijPuXZ8HAfi4UAbfyrfO/U+hCS+DHT9h70roBDqVCQ6OLAHhYBk/Kxdq4YZINswRKX7gIgPRsubZ/q1y7dse6LxW/GTyGip/qGtv71tbbAaDKDDsPi7V1i2H8SFg5T6zvOgI1dU4eASadnD57qvY6d7pYr/sOhSWOylv/AYDFAqmX5froP+t/7HC5T1q6E0dA+TtIvSrWtq8Ffx/tfZ8ASFgm9jt+Ht5+6HQBYAzA7QK5NqPVnWBWtNw3574TLoGfDbA/Raz1C4YRYa2Ww1Dw6SH2P5wGjU1OFgElz6GoTKxtXA49vf9u8+0Nm1ZKToVF8PSVk0VApk4Oj54obp8WKe+TlWvn/P8lAPM3SNwnP/mFDxJrI4bAoFCxtvsYfKt3kixQoJP71yyCbl3FWg9vWL9UUkypgfuPOw8A3YrQaZ3cHb9Fe2yxc5kQPcG2vu3VF76YHRQBryvgxMWOoX4wDSo+29b31y+51tQE94odBCCng+/xd4vkWvdu+mlZZhWV2hKzG0Bjo5azO9KOnYEmya8ZoFNI/Wp2XLFGCqD0JeQWdyyALBM8k9QWQvvK+900idtfvIG1Oxy0CV7P0TnOpkDkGOMDZOdDdJxYu5EHwwa3bZelV4B1SRAUCDFTtENXXT0UlsKGJO3WafW5onVRtLYe+k+Wf1j1PQjwNT7AVzMERciP0mUZ0Ktnq528GoIjHR91NQXg17udJVBYIp/8+iXWTb7lhrgqVqy9r4SiJ23bgwIhOcH6CR5IhLg5du4BZzKM3/yM2swpcu1Clrh9RSzMiDA+RnICrJoPXTztAPDuIxw9K3ceGWYbgFHhcm3PKfj0pW27nw+kJMujp8WC/eHSAe3k6eVl5yaYq5ObF8ZASLBtAAaEQEwUZEg217sPxOW0PgFwcBusXgB5xWAqhkfPoH+I9mNEjYFJo61flrqboLuZ+n+AAqAAKAAKgAKgACgACoACoAAoAAqAAqAAuJ/9BkYG9/zutbrRAAAAAElFTkSuQmCC"

DEFAULT_ROOT_GEOMETRY = "400x400+700+0"
DEFAULT_EDITOR_GEOMETRY = ""

STATE_NAME = ".state.json"
ARCHIVE_NAME = ".archive"

FONT_FAMILY = "Arial"
FONT_NORMAL_SIZE = 12
FONT_LARGE_SIZE = 14
FONT_NORMAL = (FONT_FAMILY, FONT_NORMAL_SIZE)
FONT_ITALIC = (FONT_FAMILY, FONT_NORMAL_SIZE, "italic")
FONT_BOLD = (FONT_FAMILY, FONT_NORMAL_SIZE, "bold")
FONT_LARGE_BOLD = (FONT_FAMILY, FONT_LARGE_SIZE, "bold")

LINK_COLOR = "blue"
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def get_markdown_to_ast(markdown_text):
    "Convert Markdown to AST."
    return marko.Markdown(renderer=marko.ast_renderer.ASTRenderer).convert(markdown_text)
def get_now():
    "Get formatted string for the current local time."
    return time.strftime(TIME_FORMAT, time.localtime())

class Main:
    "Root window listing sections and texts."

    def __init__(self, dirpath):
        self.dirpath = dirpath
        try:
            with open(os.path.join(self.dirpath, STATE_NAME)) as infile:
                self.state = json.load(infile)
            if "root" not in self.state:
                raise ValueError
            if "editors" not in self.state:
                raise ValueError
        except (OSError, json.JSONDecodeError, ValueError):
            self.state = dict(root=dict(), editors=dict())
        self.root = tk.Tk()
        self.root.title(os.path.basename(dirpath))
        self.root.geometry(self.state["root"].get("geometry", DEFAULT_ROOT_GEOMETRY))
        self.root.option_add("*tearOff", tk.FALSE)
        self.au64 = tk.PhotoImage(data=AU64)
        self.root.iconphoto(False, self.au64)
        self.root.minsize(400, 400)

        self.menubar = tk.Menu(self.root)
        self.root["menu"] = self.menubar
        self.menubar.add_command(label="Au", font=(FONT_FAMILY, 14, "bold"),
                                 background="gold")

        self.menu_file = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_file, label="File")
        self.menu_file.add_command(label="Create", command=self.create)
        self.menu_file.add_command(label="Save", command=self.save,
                                   accelerator="Ctrl-S")
        self.root.bind("<Control-s>", self.save)
        self.menu_file.add_command(label="Quit", command=self.quit,
                                   accelerator="Ctrl-Q")
        self.root.bind_all("<Control-q>", self.quit)

        self.menu_edit = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_edit, label="Edit")

        self.treeview_frame = ttk.Frame(self.root, padding=4)
        self.treeview_frame.pack(fill=tk.BOTH, expand=1)
        self.treeview_frame.rowconfigure(0, weight=1)
        self.treeview_frame.columnconfigure(0, weight=1)
        self.treeview = ttk.Treeview(self.treeview_frame,
                                     columns=("changed", "characters", "timestamp"),
                                     selectmode="browse")
        self.treeview.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.treeview.heading("changed", text=" ", anchor=tk.CENTER)
        self.treeview.column("changed", anchor=tk.CENTER, stretch=False,
                             minwidth=2*FONT_NORMAL_SIZE, width=2*FONT_NORMAL_SIZE)
        self.treeview.heading("characters", text="Characters")
        self.treeview.column("characters", anchor=tk.E,
                             minwidth=6*FONT_NORMAL_SIZE, width=10*FONT_NORMAL_SIZE)
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

        for subpath, state in self.state["editors"].items():
            if state.get("open"):
                self.open(subpath)

    def add_dir_to_treeview(self, subdirpath="", id=""):
        dirpath = os.path.join(self.dirpath, subdirpath) if subdirpath else self.dirpath
        paths = [p for p in os.listdir(dirpath) if not p.startswith(".")]
        for path in sorted(paths):
            subpath = os.path.join(subdirpath, path) if subdirpath else path
            self.texts[subpath] = dict()
            tag = os.path.join(dirpath, path)
            if path.endswith(".md"):
                name = os.path.splitext(path)[0]
                subid = self.treeview.insert(id, "end", subpath, text=name, tags=(tag, ))
                self.texts[subpath]["listentry"] = subid
                self.treeview.tag_bind(tag, "<Button-1>", OpenEditor(self, subpath))
            elif os.path.isdir(os.path.join(dirpath, path)):
                subid = self.treeview.insert(id, "end", subpath, text=path, tags=(tag, ))
                self.texts[subpath]["listentry"] = subid
                self.add_dir_to_treeview(os.path.join(subdirpath, path), subid)

    def open(self, subpath):
        try:
            editor = self.texts[subpath]["editor"]
            editor.toplevel.lift()
        except KeyError:
            self.texts[subpath]["editor"] = editor = Editor(self, subpath)
        editor.text.focus_set()

    def create(self):
        print("create")

    def save(self, event=None):
        "Save contents of all open text editor windows."
        for text in self.texts.values():
            try:
                text["editor"].save()
            except KeyError:
                pass
        self.state["root"]["geometry"] = self.root.geometry()
        with open(os.path.join(self.dirpath, STATE_NAME), "w") as outfile:
            json.dump(self.state, outfile, indent=2)

    def quit(self, event=None):
        self.root.lift()
        for text in self.texts.values():
            try:
                if text["editor"].modified:
                    if not messagebox.askokcancel(title="Quit?",
                                                  message="Modifications will not be saved. Really quit?"):
                        return
            except KeyError:
                pass
        self.root.destroy()

    def mainloop(self):
        self.root.mainloop()


class Editor:
    "Text editor window."

    def __init__(self, main, subpath):
        self.main = main
        self.subpath = subpath
        self.toplevel = tk.Toplevel(self.main.root)
        self.toplevel.title(os.path.splitext(self.subpath)[0])
        self.toplevel.protocol("WM_DELETE_WINDOW", self.close)

        if self.subpath not in self.main.state["editors"]:
            self.main.state["editors"][self.subpath] = dict()
        try:
            self.toplevel.geometry(self.main.state["editors"][self.subpath]["geometry"])
        except KeyError:
            pass

        self.menubar = tk.Menu(self.toplevel)
        self.toplevel["menu"] = self.menubar
        self.menubar.add_command(label="Au", font=FONT_LARGE_BOLD, background="gold",
                                 command=self.main.root.lift)

        self.menu_file = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_file, label="File")
        self.menu_file.add_command(label="Save", command=self.save,
                                   accelerator="Ctrl-S")
        self.toplevel.bind("<Control-s>", self.save)
        self.menu_file.add_command(label="Close", command=self.close,
                                   accelerator="Ctrl-Z")
        self.toplevel.bind("<Control-z>", self.close)

        self.menu_edit = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_edit, label="Edit")

        self.text_frame= ttk.Frame(self.toplevel, padding=4)
        self.text_frame.pack(fill=tk.BOTH, expand=1)
        self.text_frame.rowconfigure(0, weight=1)
        self.text_frame.columnconfigure(0, weight=1)

        self.text = tk.Text(self.text_frame, width=80, height=50, padx=10,
                            font=FONT_NORMAL, wrap=tk.WORD, spacing1=4, spacing2=8)
        self.text.grid(column=0, row=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.text_scroll_y = ttk.Scrollbar(self.text_frame, orient=tk.VERTICAL,
                                           command=self.text.yview)
        self.text_scroll_y.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.text.configure(yscrollcommand=self.text_scroll_y.set)

        self.info_frame = ttk.Frame(self.toplevel, padding=4)
        self.info_frame.pack(fill=tk.X, expand=1)
        self.info_frame.columnconfigure(0, weight=1)
        self.info_frame.columnconfigure(1, weight=2)
        self.info_frame.columnconfigure(2, weight=2)
        self.size_var = tk.StringVar()
        size_label = ttk.Label(self.info_frame)
        size_label.grid(column=0, row=0, sticky=tk.W, padx=4)
        size_label["textvariable"] = self.size_var
        self.url_var = tk.StringVar()
        url_label = ttk.Label(self.info_frame, anchor=tk.W)
        url_label.grid(column=1, row=0, sticky=tk.W, padx=4)
        url_label["textvariable"] = self.url_var
        self.title_var = tk.StringVar()
        title_label = ttk.Label(self.info_frame, anchor=tk.W)
        title_label.grid(column=2, row=0, sticky=tk.W, padx=4)
        title_label["textvariable"] = self.title_var

        self.text.tag_configure("italic", font=FONT_ITALIC)
        self.italic_start = None
        self.text.tag_configure("bold", font=FONT_BOLD)
        self.bold_start = None

        self.links = Links(self)

        path = os.path.join(self.main.dirpath, self.subpath)
        self.timestamp = time.strftime(TIME_FORMAT, time.localtime(os.path.getmtime(path)))
        with open(path) as infile:
            markdown_text = infile.read()
        ast = get_markdown_to_ast(markdown_text)
        print(json.dumps(ast, indent=4))
        self.char_count = 0
        self.parse(ast)
        self.update_metadata()

        self.text.update()
        width = self.text.winfo_width() / 2
        url_label.configure(wraplength=width)
        title_label.configure(wraplength=width)

        self.text.bind("<<Modified>>", self.handle_modified)
        self.ignore_modified_event = True
        self.text.edit_modified(False)

    def parse(self, ast):
        try:
            method = getattr(self, f"parse_{ast['element']}")
        except AttributeError:
            print("Could not handle", ast['element'])
        else:
            method(ast)

    def parse_document(self, ast):
        self.previous_blank_line = False
        for child in ast["children"]:
            self.parse(child)

    def parse_paragraph(self, ast):
        if self.previous_blank_line:
            self.text.insert(tk.END, "\n")
            self.char_count += 1
            self.previous_blank_line = False
        for child in ast["children"]:
            self.parse(child)

    def parse_emphasis(self, ast):
        self.italic_start = self.text.index(tk.INSERT)
        for child in ast["children"]:
            self.parse(child)
        self.text.tag_add("italic", self.italic_start, self.text.index(tk.INSERT))
        self.italic_start = None

    def parse_strong_emphasis(self, ast):
        self.bold_start = self.text.index(tk.INSERT)
        for child in ast["children"]:
            self.parse(child)
        self.text.tag_add("bold", self.bold_start, self.text.index(tk.INSERT))
        self.bold_start = None

    def parse_raw_text(self, ast):
        self.text.insert(tk.END, ast["children"])
        self.char_count += len(ast["children"])

    def parse_line_break(self, ast):
        self.text.insert(tk.END, "\n")
        self.char_count += 1

    def parse_blank_line(self, ast):
        self.text.insert(tk.END, "\n")
        self.previous_blank_line = True

    def parse_link(self, ast):
        link_start = self.text.index(tk.INSERT)
        for child in ast["children"]:
            self.parse(child)
        self.text.tag_add("link", link_start, self.text.index(tk.INSERT))
        self.text.tag_add(self.links.add(ast), link_start, self.text.index(tk.INSERT))
        
    @property
    def modified(self):
        return self.text.edit_modified()

    @property
    def character_count(self):
        return len(self.text.get("1.0", tk.END))

    def update_metadata(self):
        self.size_var.set(f"{self.character_count} characters")
        self.main.treeview.set(self.subpath, "characters", str(self.character_count))
        self.main.treeview.set(self.subpath, "timestamp", self.timestamp)

    def handle_modified(self, event=None):
        print(self.modified, self.ignore_modified_event)
        if self.ignore_modified_event:
            self.ignore_modified_event = False
        if not self.modified:
            return
        self.main.treeview.set(self.subpath, "changed", "*")

    def close(self, event=None):
        if self.modified:
            if not messagebox.askokcancel(title="Close?",
                                          message="Modifications will not be saved. Really close?"):
                return
        self.main.state["editors"][self.subpath]["open"] = False
        del self.main.texts[self.subpath]["editor"]
        self.toplevel.destroy()

    def save(self, event=None):
        state = self.main.state["editors"][self.subpath]
        state["open"] = True
        state["geometry"] = self.toplevel.geometry()
        if not self.modified:
            return
        self.current_link_tag = None
        # Create archive subdirectory if it does not exist.
        archivedfilepath = os.path.join(self.main.dirpath, ARCHIVE_NAME, f"{self.subpath} {get_now()}")
        archivepath = os.path.dirname(archivedfilepath)
        if not os.path.exists(archivepath):
            os.makedirs(archivepath)
        # Move current file to the archive.
        filepath = os.path.join(self.main.dirpath, self.subpath)
        os.rename(filepath, archivedfilepath)
        # Save the current contents in a new file.
        with open(filepath, "w") as outfile:
            for item in self.text.dump("1.0", tk.END):
                try:
                    method = getattr(self, f"save_{item[0]}")
                except AttributeError:
                    print("Could not handle", item)
                else:
                    method(outfile, item)
        self.update_metadata()
        self.main.treeview.set(self.subpath, "changed", "")
        self.ignore_modified_event = True
        self.text.edit_modified(False)

    def save_text(self, outfile, item):
        outfile.write(item[1])

    def save_tagon(self, outfile, item):
        try:
            method = getattr(self, f"save_tagon_{item[1]}")
        except AttributeError:
            pass
        else:
            method(outfile, item)

    def save_tagon_italic(self, outfile, item):
        outfile.write("*")

    def save_tagon_bold(self, outfile, item):
        outfile.write("**")

    def save_tagon_link(self, outfile, item):
        for tag in self.text.tag_names(item[2]):
            if tag.startswith("link-"):
                self.current_link_tag = tag
                outfile.write("[")
                return

    def save_tagoff(self, outfile, item):
        try:
            method = getattr(self, f"save_tagoff_{item[1]}")
        except AttributeError:
            pass
        else:
            method(outfile, item)

    def save_tagoff_italic(self, outfile, item):
        outfile.write("*")

    def save_tagoff_bold(self, outfile, item):
        outfile.write("**")

    def save_tagoff_link(self, outfile, item):
        link = self.links.get_link(self.current_link_tag)
        if link["title"]:
            outfile.write(f"""]({link['url']} "{link['title']}")""")
        else:
            outfile.write(f"]({link['url']})")
        self.current_link_tag = None

    def save_mark(self, outfile, item):
        pass


class OpenEditor:
    "Action to open an editor window."

    def __init__(self, main, path):
        self.main = main
        self.path = path

    def __call__(self, event):
        self.main.open(self.path)


class Links:
    "Manage links in a text editor."

    def __init__(self, editor):
        self.editor = editor
        self.editor.text.tag_configure("link", foreground=LINK_COLOR, underline=True)
        self.editor.text.tag_bind("link", "<Enter>", self.enter)
        self.editor.text.tag_bind("link", "<Leave>", self.leave)
        self.editor.text.tag_bind("link", "<Button-1>", self.click)
        self.lookup = dict()

    def add(self, ast):
        tag = f"link-{len(self.lookup)}"
        self.lookup[tag] = dict(url=ast["dest"], title=ast["title"])
        return tag

    def enter(self, event):
        self.editor.text.configure(cursor="hand2")
        ast = self.get_current_link()
        self.editor.url_var.set(ast["url"])
        self.editor.title_var.set(ast["title"] or "-")

    def leave(self, event):
        self.editor.text.configure(cursor="")
        self.editor.url_var.set("")
        self.editor.title_var.set("")

    def get_current_link(self):
        for tag in self.editor.text.tag_names(tk.CURRENT):
            if tag.startswith("link-"):
                return self.lookup[tag]

    def get_link(self, tag):
        return self.lookup[tag]

    def click(self, event):
        webbrowser.open_new_tab(self.get_current_link()["url"])


if __name__ == "__main__":
    import sys
    if len(sys.argv) == 2:
        dirpath = sys.argv[1]
        if not os.path.isabs(dirpath):
            dirpath = os.path.normpath(os.path.join(os.getcwd(), dirpath))
            if not os.path.exists(dirpath):
                sys.exit(f"Error: '{dirpath}' does not exist.")
            if not os.path.isdir(dirpath):
                sys.exit(f"Error: '{dirpath}' is not a directory.")
    elif len(sys.argv) == 1:
        dirpath = os.getcwd()
    else:
        sys.exit("Error: at most one directory path can be provided.")
    Main(dirpath).mainloop()
