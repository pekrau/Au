"Authoring editor based on Tkinter."

import json
import os
import re
import tkinter as tk
from tkinter import ttk

import marko
import marko.ast_renderer


AU64 = "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAABhGlDQ1BJQ0MgcHJvZmlsZQAAKJF9kT1Iw0AcxV/TSkWqDnaQ4pChOlkQleKoVShChVArtOpgcv2EJg1Jiouj4Fpw8GOx6uDirKuDqyAIfoA4OzgpukiJ/0sKLWI8OO7Hu3uPu3eA0Kwy1QxMAKpmGelkQszmVsXgKwLwYwBxRGRm6nOSlILn+LqHj693MZ7lfe7P0Z8vmAzwicSzTDcs4g3i+Kalc94nDrOynCc+Jx436ILEj1xXXH7jXHJY4JlhI5OeJw4Ti6UuVrqYlQ2VeJo4mlc1yheyLuc5b3FWq3XWvid/YaigrSxzneYIkljEEiSIUFBHBVVYiNGqkWIiTfsJD3/E8UvkUshVASPHAmpQITt+8D/43a1ZnJp0k0IJoOfFtj9GgeAu0GrY9vexbbdOAP8zcKV1/LUmMPNJeqOjRY+AwW3g4rqjKXvA5Q4w/KTLhuxIfppCsQi8n9E35YChW6Bvze2tvY/TByBDXaVugINDYKxE2ese7+7t7u3fM+3+fgBwYnKmw5NibQAAAAZiS0dEAP8A/wD/oL2nkwAAAAlwSFlzAAAuIwAALiMBeKU/dgAAAAd0SU1FB+gEAw45EiZV65kAAAAZdEVYdENvbW1lbnQAQ3JlYXRlZCB3aXRoIEdJTVBXgQ4XAAADoklEQVR42u2aWUiUURTHf5qVLa6kIVZQUBptRLtKYVBhQUFky0NZ2fbQQ1ESREbLQxJCEe0RVIhJRSumJZGV5qRmlla2SZstlo6mUKk5PXz5kN77+c1iOTP3wMcM93/u3Lm/Ofeeew/jYXmKBTc2T9zcFAAFQAFQABQABUABUAAUAAVAAVAAFAAFQAFwP/OypVNlFfSNat+vygSBfi4YAaaHxvzyH7ngEmhuhlMXjPmmXgFLJ684elhbFH3+GsJijPuXZ8HAfi4UAbfyrfO/U+hCS+DHT9h70roBDqVCQ6OLAHhYBk/Kxdq4YZINswRKX7gIgPRsubZ/q1y7dse6LxW/GTyGip/qGtv71tbbAaDKDDsPi7V1i2H8SFg5T6zvOgI1dU4eASadnD57qvY6d7pYr/sOhSWOylv/AYDFAqmX5froP+t/7HC5T1q6E0dA+TtIvSrWtq8Ffx/tfZ8ASFgm9jt+Ht5+6HQBYAzA7QK5NqPVnWBWtNw3574TLoGfDbA/Raz1C4YRYa2Ww1Dw6SH2P5wGjU1OFgElz6GoTKxtXA49vf9u8+0Nm1ZKToVF8PSVk0VApk4Oj54obp8WKe+TlWvn/P8lAPM3SNwnP/mFDxJrI4bAoFCxtvsYfKt3kixQoJP71yyCbl3FWg9vWL9UUkypgfuPOw8A3YrQaZ3cHb9Fe2yxc5kQPcG2vu3VF76YHRQBryvgxMWOoX4wDSo+29b31y+51tQE94odBCCng+/xd4vkWvdu+mlZZhWV2hKzG0Bjo5azO9KOnYEmya8ZoFNI/Wp2XLFGCqD0JeQWdyyALBM8k9QWQvvK+900idtfvIG1Oxy0CV7P0TnOpkDkGOMDZOdDdJxYu5EHwwa3bZelV4B1SRAUCDFTtENXXT0UlsKGJO3WafW5onVRtLYe+k+Wf1j1PQjwNT7AVzMERciP0mUZ0Ktnq528GoIjHR91NQXg17udJVBYIp/8+iXWTb7lhrgqVqy9r4SiJ23bgwIhOcH6CR5IhLg5du4BZzKM3/yM2swpcu1Clrh9RSzMiDA+RnICrJoPXTztAPDuIxw9K3ceGWYbgFHhcm3PKfj0pW27nw+kJMujp8WC/eHSAe3k6eVl5yaYq5ObF8ZASLBtAAaEQEwUZEg217sPxOW0PgFwcBusXgB5xWAqhkfPoH+I9mNEjYFJo61flrqboLuZ+n+AAqAAKAAKgAKgACgACoACoAAoAAqAAqAAuJ/9BkYG9/zutbrRAAAAAElFTkSuQmCC"

FONT_FAMILY = "Arial"
FONT_NORMAL = (FONT_FAMILY, 12)
FONT_ITALIC = (FONT_FAMILY, 12, "italic")
FONT_BOLD = (FONT_FAMILY, 12, "bold")
FONT_LARGE_BOLD = (FONT_FAMILY, 14, "bold")


def get_markdown_to_ast(markdown_text):
    "Convert Markdown to AST."
    return marko.Markdown(renderer=marko.ast_renderer.ASTRenderer).convert(markdown_text)

class Main:
    "Root window listing sections and texts."

    def __init__(self, dirpath):
        self.dirpath = dirpath
        self.root = tk.Tk()
        self.root.title(os.path.basename(dirpath))
        self.root.geometry("+700+0")
        self.root.option_add("*tearOff", tk.FALSE)
        self.au64 = tk.PhotoImage(data=AU64)
        self.root.iconphoto(False, self.au64)
        self.root.protocol("WM_DELETE_WINDOW", self.quit)

        self.menubar = tk.Menu(self.root)
        self.root["menu"] = self.menubar
        self.menubar.add_command(label="Au", font=(FONT_FAMILY, 14, "bold"),
                                 background="gold")

        self.menu_file = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_file, label="File")
        self.menu_file.add_command(label="Create", command=self.create)
        self.menu_file.add_command(label="Save", command=self.save)
        self.menu_file.add_command(label="Quit", command=self.quit)

        self.menu_edit = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_edit, label="Edit")

        self.tree_frame = ttk.Frame(self.root, padding=4)
        self.tree_frame.pack(fill=tk.BOTH, expand=1)
        self.tree_frame.rowconfigure(0, weight=1)
        self.tree_frame.columnconfigure(0, weight=1)
        self.tree = ttk.Treeview(self.tree_frame,
                                 columns=("size", "timestamp"),
                                 selectmode="browse")
        self.tree.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        self.tree.heading("size", text="Size")
        self.tree.heading("timestamp", text="Timestamp")
        self.tree_scroll_y = ttk.Scrollbar(self.tree_frame,
                                           orient=tk.VERTICAL,
                                           command=self.tree.yview)
        self.tree_scroll_y.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.tree.configure(yscrollcommand=self.tree_scroll_y.set)

        self.texts = {}
        self.add_dir_to_treeview()

        self.root.update_idletasks()
        width, height = self.root.geometry().split("+", 1)[0].split("x")
        self.root.minsize(int(width), int(height))

    def add_dir_to_treeview(self, subdirpath="", id=""):
        dirpath = os.path.join(self.dirpath, subdirpath) if subdirpath else self.dirpath
        for path in sorted(os.listdir(dirpath)):
            subpath = os.path.join(subdirpath, path) if subdirpath else path
            self.texts[subpath] = dict()
            tag = os.path.join(dirpath, path)
            if path.endswith(".md"):
                name = os.path.splitext(path)[0]
                subid = self.tree.insert(id, "end", text=name, tags=(tag, ))
                self.texts[subpath]["listentry"] = subid
                self.tree.tag_bind(tag, "<1>", OpenEditor(self, subpath))
            elif os.path.isdir(os.path.join(dirpath, path)):
                subid = self.tree.insert(id, "end", text=path, tags=(tag, ))
                self.texts[subpath]["listentry"] = subid
                self.add_dir_to_treeview(os.path.join(subdirpath, path), subid)

    def open(self, subpath):
        try:
            editor = self.texts[subpath]["editor"]
        except KeyError:
            self.texts[subpath]["editor"] = editor = Editor(self, subpath)
        editor.text.focus_set() # XXX Doesn't work for the first editor window!?
        editor.toplevel.lift()

    def create(self):
        print("create")

    def save(self):
        "Save contents of all open text editor windows."
        for text in self.texts.values():
            try:
                text["editor"].save()
            except KeyError:
                pass

    def quit(self):
        self.root.destroy()

    def mainloop(self):
        self.root.mainloop()


class OpenEditor:

    def __init__(self, main, path):
        self.main = main
        self.path = path

    def __call__(self, event):
        self.main.open(self.path)


class Editor:
    "Text editor window."

    def __init__(self, main, subpath):
        self.main = main
        self.subpath = subpath
        self.toplevel = tk.Toplevel(self.main.root)
        self.toplevel.title(os.path.splitext(self.subpath)[0])
        self.toplevel.protocol("WM_DELETE_WINDOW", self.close)
        self.toplevel.bind("<Control-s>", self.save)

        self.menubar = tk.Menu(self.toplevel)
        self.toplevel["menu"] = self.menubar
        self.menubar.add_command(label="Au", font=FONT_LARGE_BOLD, background="gold",
                                 command=self.main.root.lift)

        self.menu_file = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_file, label="File")
        self.menu_file.add_command(label="Save", command=self.save)
        self.menu_file.add_command(label="Close", command=self.close)

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

        self.text.tag_configure("italic", font=FONT_ITALIC)
        self.italic_start = None
        self.text.tag_configure("bold", font=FONT_BOLD)
        self.bold_start = None

        self.text.bind("<<Modified>>", self.was_modified)
        self.ignore_modified = 2

        with open(os.path.join(self.main.dirpath, self.subpath)) as infile:
            markdown_text = infile.read()
        if subpath == "test.md":
            ast = get_markdown_to_ast(markdown_text)
            print(json.dumps(ast, indent=4))
            self.parse(ast)
        else:
            self.text.insert("1.0", markdown_text)
            self.text.edit_modified(False)

    def parse(self, ast):
        self.char_count = 0
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

    def parse_blank_line(self, ast):
        self.text.insert(tk.END, "\n")
        self.previous_blank_line = True

    def was_modified(self, event=None):
        if self.ignore_modified:
            self.text.edit_modified(False)
            self.ignore_modified -= 1
        else:
            self.ignore_modified += 1

    def save(self, event=None):
        if not self.text.edit_modified():
            print("has not been modified")
        filepath = os.path.join(self.main.dirpath, f"{self.subpath}.save")
        with open(filepath, "w") as outfile:
            for item in self.text.dump("1.0", tk.END):
                try:
                    method = getattr(self, f"save_{item[0]}")
                except AttributeError:
                    print("Could not handle", item)
                else:
                    method(outfile, item[1])
        self.text.edit_modified(False)

    def save_text(self, outfile, data):
        outfile.write(data)

    def save_tagon(self, outfile, data):
        if data == "italic":
            outfile.write("*")
        elif data == "bold":
            outfile.write("**")
        else:
            print("Could not handle tagon", data)

    def save_tagoff(self, outfile, data):
        if data == "italic":
            outfile.write("*")
        elif data == "bold":
            outfile.write("**")
        else:
            print("Could not handle tagoff", data)

    def close(self, event=None):
        if self.text.edit_modified():
            print("had been modified")
        del self.main.texts[self.subpath]["editor"]
        self.toplevel.destroy()



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
