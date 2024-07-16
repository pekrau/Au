"Graphics canvas container and editor."

from icecream import ic

import tkinter as tk
import tkinter.ttk

import constants
import utils


class Conceptmap:

    def __init__(self, viewer, data=None):
        if data is None:
            data = {}
        self.viewer = viewer
        title = data.get("title")
        if title:
            self.canvas_frame = tk.ttk.LabelFrame(viewer.view,
                                                  text=f" {title} ",
                                                  cursor=constants.CONCEPTMAP_CURSOR)
        else:
            self.canvas_frame = tk.ttk.Frame(viewer.view,
                                             cursor=constants.CONCEPTMAP_CURSOR)
        viewer.view.window_create(tk.INSERT, window=self.canvas_frame)
        self.canvas_frame.rowconfigure(0, weight=1)
        self.canvas_frame.columnconfigure(0, weight=1)
        canvas = data.get("canvas", {})
        width = canvas.get("width", constants.CONCEPTMAP_WIDTH)
        height = canvas.get("height", constants.CONCEPTMAP_HEIGHT)
        kwargs = dict(width=width,
                      height=height,
                      background=canvas.get("background", constants.CONCEPTMAP_BACKGROUND))
        extend = canvas.get("extend")
        if extend:
            kwargs["scrollregion"] = (-extend, -extend, width+extend, height+extend)
        self.canvas = tk.Canvas(self.canvas_frame, **kwargs)
        self.canvas.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W, tk.E))
        self.scroll_x = tk.ttk.Scrollbar(
            self.canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview
        )
        self.scroll_x.grid(row=1, column=0, sticky=(tk.W, tk.E))
        self.canvas.configure(xscrollcommand=self.scroll_x.set)
        self.scroll_y = tk.ttk.Scrollbar(
            self.canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview
        )
        self.scroll_y.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.canvas.configure(yscrollcommand=self.scroll_y.set)
        ic(data)
