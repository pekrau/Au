"Graphics canvas container and editor."

from icecream import ic

import tkinter as tk
import tkinter.ttk

import yaml

import constants
import utils


class Graphics:
    pass

class Conceptmap(Graphics):

    def __init__(self, viewer, text=None):
        import editor
        if text is None:
            self.data = {}
            self.entities = []
        else:
            self.data = yaml.safe_load(text)
            self.entities = self.data.get("entities", [])
        self.entity_lookup = dict([(e["id"], e) for e in self.entities])
        self.viewer = viewer
        self.edit = isinstance(self.viewer, editor.Editor)
        title = self.data.get("title")
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
        canvas = self.data.get("canvas", {})
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
        for entity in self.entities:
            match entity["type"]:
                case "concept":
                    self.draw_concept(entity)
        self.canvas.bind("<ButtonPress-1>", self.pick_entity)
        self.canvas.bind("<ButtonRelease-1>", self.unpick_entity)
        self.picked_entity = None

    def __repr__(self):
        return f"```conceptmap\n{yaml.dump(self.data)}\n```\n"

    def draw_concept(self, entity):
         self.canvas.create_rectangle(entity["x"] - entity["width"] / 2,
                                      entity["y"] - entity["height"] / 2,
                                      entity["x"] + entity["width"] / 2,
                                      entity["y"] + entity["height"] / 2,
                                      outline=entity["stroke"],
                                      fill=entity["fill"],
                                      tags=entity["id"])
         self.canvas.create_text(entity["x"],
                                 entity["y"],
                                 text=entity["text"],
                                 justify=tk.CENTER,
                                 tags=entity["id"])

    def pick_entity(self, event):
        overlapping = self.canvas.find_overlapping(event.x, event.y, event.x, event.y)
        if overlapping:
            for id in self.canvas.gettags(overlapping[0]):
                if id.startswith("id"):
                    self.picked_entity = self.entity_lookup[id]
                    if self.edit:
                        self.canvas.bind("<B1-Motion>", self.move_entity)
                        self.move_coords = (event.x, event.y)
                    return

    def unpick_entity(self, event):
        self.picked_entity = None
        self.canvas.unbind("<B1-Motion>")

    def move_entity(self, event):
        dx = event.x - self.move_coords[0]
        dy = event.y - self.move_coords[1]
        if not dx and not dy:
            return
        self.viewer.modified = True
        self.canvas.move(self.picked_entity["id"], dx, dy)
        self.picked_entity["x"] += dx
        self.picked_entity["y"] += dy
        self.move_coords = (event.x, event.y)
        
