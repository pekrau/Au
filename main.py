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
from meta_viewers import HelpViewer
# from meta_viewers import ReferencesViewer, IndexedViewer, TodoViewer, HelpViewer


class Main:
    """Main window containing three panes:
    1) The tree of sections and texts.
    2) The notebook containing tabs for all top-level texts.
    3) The notebook with references, indexed and help.
    """

    def __init__(self, absdirpath):
        self.absdirpath = absdirpath
        self.help = Source(os.path.join(os.path.dirname(__file__), "help"))
        self.source = Source(self.absdirpath)
        self.config_read()
        self.source.apply_config(self.config)

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

        # Populate the graphics interface.
        self.render()
        self.config_save()

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

    def root_resized(self, event):
        "Save configuration after root window resize."
        if event.widget != self.root:
            return
        if getattr(self, "_after_id", None):
            self.root.after_cancel(self._after_id)
        self._after_id = self.root.after(1000, lambda: self.config_save())

    def config_save(self):
        "Save the current config. Get current state from the respective widgets."
        ic("config_save")
        config = dict(main=dict(geometry=self.root.geometry(),
                                selected=self.treeview.focus(),
                                sash=[self.panedwindow.sash("coord", 0)[0],
                                      self.panedwindow.sash("coord", 1)[0]]))
        # meta=dict(
        #     selected=str(self.meta_notebook_lookup[self.meta_notebook.select()])))

        config.update(self.source.get_config())

        # Save the current cut-and-paste buffer.
        config["paste"] = self.paste_buffer

        with open(self.configpath, "w") as outfile:            
            json.dump(config, outfile, indent=2)

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
        self.menu_edit.add_command(label="Rename", command=self.rename)
        self.menu_edit.add_command(label="Copy", command=self.copy)
        self.menu_edit.add_command(label="Delete", command=self.delete)
        # XXX Create text
        # XXX Create section

        self.menu_move = tk.Menu(self.menubar)
        self.menubar.add_cascade(menu=self.menu_move, label="Rearrange")
        self.menu_move.add_command(label="Up",
                                      command=self.move_item_up,
                                      accelerator="Ctrl-Up")
        self.menu_move.add_command(label="Down",
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

        # self.treeview.bind("<Control-e>", self.open_texteditor)
        # self.treeview.bind("<Control-n>", self.text_create)
        self.treeview.bind("<Control-Up>", self.move_item_up)
        self.treeview.bind("<Control-Down>", self.move_item_down)
        self.treeview.bind("<Control-Right>", self.move_item_into_section)
        self.treeview.bind("<Control-Left>", self.move_item_out_of_section)

        # self.treeview.bind("<Button-3>", self.popup_menu)
        self.treeview.bind("<<TreeviewSelect>>", self.treeview_selected)
        self.treeview.bind("<<TreeviewOpen>>", self.treeview_open)
        self.treeview.bind("<<TreeviewClose>>", self.treeview_close)
        self.treeview.focus_set()

    def treeview_render(self):
        for child in self.treeview.get_children():
            self.treeview.delete(child)
        for item in self.source.all_items:
            self.add_treeview_entry(item)

    def add_treeview_entry(self, item, index=None):
        if item.is_text:
            tag = constants.ITEM_PREFIX + item.fullname
            self.treeview.insert(item.parentpath,
                                 index or tk.END,
                                 iid=item.fullname,
                                 text=item.name,
                                 tags=(tag, ))
            self.treeview.tag_bind(tag,
                                   "<Double-Button-1>",
                                   functools.partial(self.open_texteditor,
                                                     fullname=item.fullname))
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
            item = self.source.lookup[self.treeview.focus()]
        except KeyError:
            pass
        else:
            if item.is_text:
                self.texts_notebook.select(item.tabid)

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

    def texts_notebook_create(self):
        "Create the texts notebook."
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

    def texts_notebook_render(self):
        "Render tabs for the texts notebook; first delete any existing tabs."
        while self.texts_notebook_lookup:
            self.texts_notebook.forget(self.texts_notebook_lookup.popitem()[0])
        for text in self.source.all_texts:
            viewer = Viewer(self.texts_notebook, self, text)
            text.viewer = viewer
            # try:
            #     viewer.move_cursor(self.config["items"][filepath].get("cursor"))
            # except KeyError:
            #     pass
            self.texts_notebook.add(viewer.frame, text=viewer.name,
                                    state=text.shown and tk.NORMAL or tk.HIDDEN)
            tabs = self.texts_notebook.tabs()
            text.tabid = tabs[-1]
            self.texts_notebook_lookup[text.tabid] = text
            # opener = functools.partial(self.open_texteditor, filepath=filepath)
            # viewer.text.bind("<Double-Button-1>", opener)
            # viewer.text.bind("<Return>", opener)

    def meta_notebook_create(self):
        "Create the meta content notebook."
        self.meta_notebook = ttk.Notebook(self.panedwindow)
        self.panedwindow.add(self.meta_notebook, minsize=constants.PANE_MINSIZE)

         # key: tabid; value: instance
        self.meta_notebook_lookup = dict()

    #     self.references = ReferencesViewer(self.meta_notebook, self)
    #     self.meta_notebook.add(self.references.frame, text="References")
    #     tabs = self.meta_notebook.tabs()
    #     self.meta_notebook_lookup[tabs[-1]] = self.references

    #     self.indexed = IndexedViewer(self.meta_notebook, self)
    #     self.meta_notebook.add(self.indexed.frame, text="Indexed")
    #     tabs = self.meta_notebook.tabs()
    #     self.meta_notebook_lookup[tabs[-1]] = self.indexed

    #     self.todo = TodoViewer(self.meta_notebook, self)
    #     self.meta_notebook.add(self.todo.frame, text="To do")
    #     tabs = self.meta_notebook.tabs()
    #     self.meta_notebook_lookup[tabs[-1]] = self.todo

        self.help = HelpViewer(self.meta_notebook, self)
        self.meta_notebook.add(self.help.frame, text="Help")
        tabs = self.meta_notebook.tabs()
        self.meta_notebook_lookup[tabs[-1]] = self.help

    def meta_notebook_render(self):
        "Render the meta content notebook."
        pass
    #     self.references.render()
    #     self.indexed.render()
    #     self.todo.render()

    def config_apply(self):
        "Configure up windows and tabs."
        # The paste buffer is global to all editors, to facilitate cut-and-paste.
        self.paste_buffer = self.config.get("paste") or list()

        # Placement of paned window sashes.
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
            text = self.source[self.config["main"]["selected"]]
        except KeyError:
            pass
        else:
            self.treeview.selection_set(text.fullname)
            self.treeview.focus(text.fullname)

        # selected = self.config["main"]["meta"].get("selected")
        # for tabid, viewer in self.meta_notebook_lookup.items():
        #     if str(viewer) == selected:
        #         try:
        #             self.meta_notebook.select(tabid)
        #         except tk.TclError:
        #             pass
        #         break

    def archive(self):
        self.source.archive()

    def quit(self, event=None):
        # for text in self.texts.values():
        #     try:
        #         if text["editor"].is_modified:
        #             if not tk_messagebox.askokcancel(
        #                     parent=self.root,
        #                     title="Quit?",
        #                     message="All unsaved changes will be lost. Really quit?"):
        #                 return
        #             break
        #     except KeyError:
        #         pass
        self.config_save()
        self.root.destroy()

    def render(self):
        "Re-render the contents of all three panels."
        self.treeview_render()
        self.texts_notebook_render()
        self.treeview_update_info()
        self.meta_notebook_render()
        self.config_apply()

    def treeview_update_info(self):
        "Update status, chars and age of text entries."
        for text in self.source.all_texts:
            self.set_treeview_info(text)

    def set_treeview_info(self, text):
        # try:
        #     modified = text.editor.is_modified
        # except AttributeError:
        #     modified = False
        # # XXX
        # # tags = set(self.treeview.item(text.fullname), "tags")
        # tags = set()
        # if modified:
        #     tags.add("modified")
        # else:
        #     tags.discard("modified")
        # self.treeview.item(text.fullname, tags=tuple(tags))
        self.treeview.set(text.fullname, "status", str(text.status))
        self.treeview.set(text.fullname, "chars", text.viewer.character_count)
        self.treeview.set(text.fullname, "age", text.age)

    def treeview_rename_children(self, newdirpath, olddirpath, children):
        pass
        # for oldpath in children:
        #     newpath = os.path.join(newdirpath, oldpath[len(olddirpath)+1:])
        #     self.texts[newpath] = self.texts.pop(oldpath)
        #     try:
        #         editor = self.texts[newpath]["editor"]
        #     except KeyError:
        #         pass
        #     else:
        #         editor.filepath = newpath
        #         editor.toplevel.title(os.path.splitext(newpath)[0])
        #     self.add_treeview_entry(newpath)

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
        item = self.source.lookup[fullname]
        try:
            item.move_to_section(item.prev)
        except ValueError:
            return "break"
        self.treeview_render()        # XXX Optimize!
        self.treeview.update()
        self.texts_notebook_render()  # XXX Optimize!
        self.texts_notebook.update()
        self.treeview.selection_set(item.fullname)
        self.treeview.focus(item.fullname)
        self.config_save()
        return "break"

    def move_item_out_of_section(self, event=None):
        "Move the currently selected item up one level in the hierachy."
        try:
            fullname = self.treeview.selection()[0]
        except IndexError:
            return "break"
        item = self.source.lookup[fullname]
        try:
            item.move_to_parent()
        except ValueError:
            return "break"
        self.treeview_render()        # XXX Optimize!
        self.treeview.update()
        self.texts_notebook_render()  # XXX Optimize!
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
        item = self.source.lookup[fullname]
        newname = tk_simpledialog.askstring(
            parent=self.root,
            title="New name",
            prompt="Give the new name for the item",
            initialvalue=item.name)
        if newname == item.name:
            return
        try:
            item.rename(newname)
        except ValueError as error:
            tk_messagebox.showerror(
                title="Error",
                message=str(error))
            return
        if item.is_text:
            index = self.treeview.index(fullname)
            self.treeview.delete(fullname)
            self.add_treeview_entry(item, index=index)
            self.texts_notebook.tab(item.tabid, text=item.name)
            item.viewer.rerender()
        elif item.is_section:
            self.treeview_render()        # XXX Optimize!
            self.treeview.update()
            self.texts_notebook_render()  # XXX Optimize!
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
        item = self.source.lookup[fullname]
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
                title="Error",
                message="Could not generate a unique name for the copy.")
            return
        self.treeview_render()        # XXX Optimize!
        self.treeview.update()
        self.texts_notebook_render()  # XXX Optimize!
        self.texts_notebook.update()
        self.treeview.selection_set(newitem.fullname)
        self.treeview.focus(newitem.fullname)
        self.config_save()

    def create_text(self, parent=None):
        pass

    def create_section(self, parent=None):
        pass

    def delete(self):
        try:
            fullname = self.treeview.selection()[0]
        except IndexError:
            return
        item = self.source.lookup[fullname]
        if item.is_text:
            if not tk_messagebox.askokcancel(
                    title="Delete text?",
                    message=f"Really delete text '{item.fullname}'?"):
                return
        elif item.is_section:
            if not tk_messagebox.askokcancel(
                    title="Delete section?",
                    message=f"Really delete section '{item.fullname}' and all its contents?"):
                return
        item.delete()
        if item.is_text:
            self.treeview.delete(fullname)
            self.texts_notebook.forget(item.tabid)
        else:
            self.treeview_render()        # XXX Optimize!
            self.treeview.update()
            self.texts_notebook_render()  # XXX Optimize!
            self.texts_notebook.update()

    def open_texteditor(self, event=None, fullname=None):
        ic("open_texteditor", event, fullname)
        # if filepath is None:
        #     try:
        #         filepath = self.treeview.selection()[0]
        #     except IndexError:
        #         pass
        # text = self.texts[filepath]
        # try:
        #     ed = text["editor"]
        # except KeyError:
        #     ed = text["editor"] = Editor(self, filepath)
        # else:
        #     ed.toplevel.lift()
        # self.treeview.see(filepath)
        # ed.move_cursor(self.config["items"][filepath].get("cursor"))
        # ed.text.update()
        # # ed.text.focus_set()
        # return "break"

    # def text_create(self, event=None, parent=None):
    #     pass
    #     try:
    #         dirpath = self.treeview.selection()[0]
    #         absdirpath = os.path.join(self.absdirpath, dirpath)
    #     except IndexError:
    #         absdirpath = self.absdirpath
    #     if os.path.isfile(absdirpath):
    #         absdirpath = os.path.split(absdirpath)[0]
    #         dirpath = absdirpath[len(self.absdirpath)+1:]
    #     name = tk_simpledialog.askstring(
    #         parent=parent or self.root,
    #         title="New text",
    #         prompt=f"Give name of new text within section '{dirpath}':")
    #     if not name:
    #         return
    #     name = os.path.splitext(name)[0]
    #     filepath = os.path.join(dirpath, name + constants.MARKDOWN_EXT)
    #     absfilepath = os.path.normpath(os.path.join(self.absdirpath, filepath))
    #     if not absfilepath.startswith(self.absdirpath):
    #         tk_messagebox.showerror(
    #             parent=self.root,
    #             title="Wrong directory",
    #             message=f"Must be within '{self.absdirpath}'")
    #         return
    #     if os.path.exists(absfilepath):
    #         tk_messagebox.showerror(
    #             parent=self.root,
    #             title="Name exists",
    #             message=f"The text '{filepath}' already exists.")
    #         return
            
    #     with open(absfilepath, "w") as outfile:
    #         pass                # Empty file.

    #     self.config_save()
    #     self.render()
    #     self.open_texteditor(filepath=filepath)

    # def text_rerender(self, filepath, cursor=None):
    #     pass
    #     if cursor:
    #         self.config["items"][filepath]["cursor"] = cursor
    #     self.texts[filepath]["viewer"].rerender()

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
           self.texts_notebook.select())
           # self.meta_notebook.select())

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
