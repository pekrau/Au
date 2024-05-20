"View of the help file Markdown contents."

from icecream import ic

import tkinter as tk

import constants

from renderer import Renderer
from text_viewer import Viewer


class HelpRenderer(Renderer):
    "Display help text contents."

    def display(self):
        self.display_initialize()
        self.display_title()
        for text in self.main.help.source.all_texts:
            tag = constants.H_LOOKUP[text.depth+1]["tag"]
            self.view.insert(tk.INSERT, text.name + "\n", (tag,))
            self.render(text.ast)
        self.display_finalize()
        
    def display_title(self):
        title = "Au " + ".".join([str(n) for n in constants.VERSION])
        self.view.insert(tk.INSERT, title + "\n", (constants.H1["tag"],))


class HelpViewer(Viewer):
    "View of the help file Markdown contents."

    def __init__(self, parent, main):
        self.main = main
        self.view_create(parent)
        self.renderer = HelpRenderer(main, self, self.view)

    def __str__(self):
        return "Help"
