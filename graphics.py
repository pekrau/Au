"Graphics canvas container and editor."

from icecream import ic

import tkinter as tk
import tkinter.ttk
import tkinter.simpledialog
import tkinter.colorchooser

import yaml

import constants
import utils

from utils import Tr


class Conceptmap:

    def __init__(self, viewer, text=None):
        import editor
        if text is None:
            self.data = {}
            self.concepts = []
        else:
            self.data = yaml.safe_load(text)
            self.concepts = self.data.get("concepts", [])
        self.cid_count = 0
        for concept in self.concepts:
            self.cid_count = max(int(concept["id"][3:]), self.cid_count)
        self.concept_lookup = dict([(c["id"], c) for c in self.concepts])
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
        for concept in self.concepts:
            self.draw_concept(concept)
        self.canvas.bind("<ButtonPress-1>", self.pick_concept)
        if self.edit:
            self.canvas.bind("<B1-Motion>", self.move_concept)
            self.canvas.bind("<Double-Button-1>", self.edit_concept)
        self.canvas.bind("<ButtonRelease-1>", self.unpick_concept)
        self.picked_concept = None

    def __repr__(self):
        return f"```conceptmap\n{yaml.dump(self.data)}\n```\n"

    def edit_concept(self, event):
        "Edit or create a concept."
        self.pick_concept(event)
        editor = EditConcept(self, self.picked_concept)
        if editor.result is None:
            return
        if self.picked_concept:
            concept = self.picked_concept
            concept.update(editor.result)
        else:
            self.cid_count += 1
            concept = dict(id=f"cid{self.cid_count}",
                           x=event.x,
                           y=event.y,
                           width=100,
                           height=20,
                           fill="white",
                           stroke="black",
                           text_color="black")
            concept.update(editor.result)
            self.concepts.append(concept)
            self.concept_lookup[concept["id"]] = concept
        self.resize_concept(concept)
        self.draw_concept(concept)
        self.viewer.modified = True

    def draw_concept(self, concept):
        self.canvas.delete(concept["id"])
        self.canvas.create_rectangle(concept["x"] - concept["width"] / 2,
                                     concept["y"] - concept["height"] / 2,
                                     concept["x"] + concept["width"] / 2,
                                     concept["y"] + concept["height"] / 2,
                                     outline=concept["stroke"],
                                     fill=concept["fill"],
                                     tags=concept["id"])
        self.canvas.create_text(concept["x"],
                                concept["y"],
                                text=concept["text"],
                                fill=concept["text_color"],
                                justify=tk.CENTER,
                                tags=concept["id"])

    def resize_concept(self, concept):
        "Adjust the width and height according to the the bounding box of the text."
        obj = self.canvas.create_text(0, 0, text=concept["text"])
        bbox = self.canvas.bbox(obj)
        concept["width"] = bbox[2] - bbox[0] + constants.CONCEPT_WIDTH
        concept["height"] = bbox[3] - bbox[1] + constants.CONCEPT_HEIGHT
        self.canvas.delete(obj)

    def pick_concept(self, event):
        self.picked_concept = None
        overlapping = self.canvas.find_overlapping(event.x, event.y, event.x, event.y)
        if not overlapping:
            return
        for id in self.canvas.gettags(overlapping[0]):
            if id.startswith("cid"):
                self.picked_concept = self.concept_lookup[id]
                self.starting_coords = (event.x, event.y)
                break

    def unpick_concept(self, event):
        self.picked_concept = None

    def move_concept(self, event):
        if self.picked_concept is None:
            return
        dx = event.x - self.starting_coords[0]
        dy = event.y - self.starting_coords[1]
        if not dx and not dy:
            return
        self.canvas.move(self.picked_concept["id"], dx, dy)
        self.picked_concept["x"] += dx
        self.picked_concept["y"] += dy
        self.starting_coords = (event.x, event.y)
        self.viewer.modified = True
        

class EditConcept(tk.simpledialog.Dialog):
    "Dialog window for editing a concept."

    def __init__(self, conceptmap, concept=None):
        self.conceptmap = conceptmap
        self.concept = concept
        super().__init__(conceptmap.viewer.toplevel, title="Edit concept")

    def body(self, body):
        label = tk.ttk.Label(body, text=Tr("Concept"))
        label.grid(row=0, column=0, padx=4, sticky=tk.E)
        self.concept_entry = tk.Entry(body, width=50)
        if self.concept:
            self.concept_entry.insert(0, self.concept["text"])
        self.concept_entry.grid(row=0, column=1)

        label = tk.ttk.Label(body, text=Tr("Fill color"))
        label.grid(row=1, column=0, padx=4, sticky=tk.E)
        self.fill_color = self.concept.get("fill", "white")
        button = tk.ttk.Button(body, text="Fill color", command=self.set_fill_color)
        button.grid(row=1, column=1)

        label = tk.ttk.Label(body, text=Tr("Stroke color"))
        label.grid(row=2, column=0, padx=4, sticky=tk.E)
        self.stroke_color = self.concept.get("stroke", "white")
        button = tk.ttk.Button(body, text="Stroke color", command=self.set_stroke_color)
        button.grid(row=2, column=1)

        label = tk.ttk.Label(body, text=Tr("Text color"))
        label.grid(row=3, column=0, padx=4, sticky=tk.E)
        self.text_color = self.concept.get("text_color", "black")
        button = tk.ttk.Button(body, text="Text color", command=self.set_text_color)
        button.grid(row=3, column=1)
        return self.concept_entry

    def set_fill_color(self):
        color = tk.colorchooser.askcolor(title="Fill color", color=self.fill_color)
        if color:
            self.fill_color = color[1]

    def set_stroke_color(self):
        color = tk.colorchooser.askcolor(title="Stroke color", color=self.stroke_color)
        if color:
            self.stroke_color = color[1]

    def set_text_color(self):
        color = tk.colorchooser.askcolor(title="Text color", color=self.text_color)
        if color:
            self.text_color = color[1]

    def remove(self):
        "Remove the concept."
        self.conceptmap.concepts.remove(self.concept)
        self.conceptmap.concept_lookup.pop(self.concept["id"])
        self.cancel()

    def apply(self):
        self.result = dict(text=self.concept_entry.get(),
                           fill=self.fill_color,
                           stroke=self.stroke_color,
                           text_color=self.text_color)

    def buttonbox(self):
        box = tk.Frame(self)
        w = tk.ttk.Button(
            box, text=Tr("OK"), width=10, command=self.ok, default=tk.ACTIVE
        )
        w.pack(side=tk.LEFT, padx=5, pady=5)
        w = tk.ttk.Button(box, text=Tr("Remove"), width=10, command=self.remove,
                          state=tk.DISABLED if self.concept is None else tk.NORMAL)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        w = tk.ttk.Button(box, text=Tr("Cancel"), width=10, command=self.cancel)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)
        box.pack()

