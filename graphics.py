"Graphics canvas container and editor."

from icecream import ic

import tkinter as tk
import tkinter.ttk
import tkinter.simpledialog

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
            self.relations = []
        else:
            self.data = yaml.safe_load(text)
            self.concepts = self.data.get("concepts", [])
            self.relations = self.data.get("relations", [])
        self.cid_count = 0
        self.rid_count = 0
        for concept in self.concepts:
            self.cid_count = max(int(concept["id"][3:]), self.cid_count)
        for relation in self.relations:
            self.rid_count = max(int(relation["id"][3:]), self.rid_count)
        self.concept_lookup = dict([(c["id"], c) for c in self.concepts])
        self.viewer = viewer
        self.edit = isinstance(self.viewer, editor.Editor)
        title = self.data.get("title")
        if title:
            self.canvas_frame = tk.ttk.LabelFrame(viewer.view,
                                                  padding=4,
                                                  text=f" {title} ",
                                                  cursor=constants.CONCEPTMAP_CURSOR)
        else:
            self.canvas_frame = tk.ttk.Frame(viewer.view,
                                             padding=4,
                                             cursor=constants.CONCEPTMAP_CURSOR)
        viewer.view.window_create(tk.INSERT, window=self.canvas_frame)
        self.canvas_frame.rowconfigure(0, weight=1)
        self.canvas_frame.columnconfigure(0, weight=1)
        canvas = self.data.get("canvas", {})
        width = canvas.get("width", constants.CONCEPTMAP_WIDTH)
        height = canvas.get("height", constants.CONCEPTMAP_HEIGHT)
        kwargs = dict(width=width, height=height, background="white")
        self.canvas = tk.Canvas(self.canvas_frame, **kwargs)
        self.canvas.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W, tk.E))
        for concept in self.concepts:
            self.draw_concept(concept)
        for relation in self.relations:
            self.draw_relation(relation)
        self.canvas.bind("<ButtonPress-1>", self.pick_concept)
        if self.edit:
            self.canvas.bind("<B1-Motion>", self.move_concept)
            self.canvas.bind("<Double-Button-1>", self.edit_concept)
            self.canvas.bind("<Double-Button-3>", self.create_concept)
        self.canvas.bind("<ButtonRelease-1>", self.unpick_concept)
        self.picked_concept = None

    def __repr__(self):
        return f"```conceptmap\n{yaml.dump(self.data)}\n```\n"

    def create_concept(self, event):
        "Create a concept from scratch, or copy the one picked."
        self.pick_concept(event)
        # Create a new concept from scratch.
        if self.picked_concept is None:
            editor = EditConcept(self, self.picked_concept)
            if editor.result is None:
                return
            self.cid_count += 1
            concept = dict(id=f"cid{self.cid_count}",
                           type="primary",
                           x=event.x,
                           y=event.y,
                           width=100,
                           height=20)
            concept.update(editor.result)
            self.resize_concept(concept)
            self.concepts.append(concept)
            self.concept_lookup[concept["id"]] = concept
        # Copy the picked concept.
        else:
            concept = self.picked_concept.copy()
            self.cid_count += 1
            concept["id"] = f"cid{self.cid_count}"
            concept["x"] += 10
            concept["y"] += 10
            self.draw_concept(concept)
            self.concepts.append(concept)
            self.concept_lookup[concept["id"]] = concept
            editor = EditConcept(self, concept)
            if editor.result is None:
                return
            concept.update(editor.result)
            self.resize_concept(concept)
        self.draw_concept(concept)
        self.viewer.modified = True

    def edit_concept(self, event):
        "Edit a concept."
        self.pick_concept(event)
        if self.picked_concept is None:
            return
        editor = EditConcept(self, self.picked_concept)
        if editor.result is None:
            return
        concept = self.picked_concept
        concept.update(editor.result)
        self.resize_concept(concept)
        self.concepts.remove(concept)
        self.concepts.append(concept)
        self.draw_concept(concept)
        self.draw_relations(concept)
        self.viewer.modified = True

    def draw_concept(self, concept):
        self.canvas.delete(concept["id"])
        type = constants.CONCEPTMAP_TYPES[concept["type"]]
        self.canvas.create_rectangle(concept["x"] - concept["width"] / 2,
                                     concept["y"] - concept["height"] / 2,
                                     concept["x"] + concept["width"] / 2,
                                     concept["y"] + concept["height"] / 2,
                                     outline="black",
                                     fill=type["fill"],
                                     tags=concept["id"])
        self.canvas.create_text(concept["x"],
                                concept["y"],
                                justify=tk.CENTER,
                                text=concept["text"],
                                fill=type["stroke"],
                                tags=concept["id"])

    def draw_relations(self, concept):
        id = concept["id"] 
        for relation in self.relations:
            if relation["from"] == id or relation["to"] == id:
                self.draw_relation(relation)

    def draw_relation(self, relation):
        c1 = self.concept_lookup[relation["from"]]
        c2 = self.concept_lookup[relation["to"]]
        self.canvas.delete(f"{c1['id']}-{c2['id']}")
        c1_xlo = c1["x"] - c1["width"] / 2
        c1_xhi = c1["x"] + c1["width"] / 2
        c2_xlo = c2["x"] - c2["width"] / 2
        c2_xhi = c2["x"] + c2["width"] / 2
        c1_ylo = c1["y"] - c1["height"] / 2
        c1_yhi = c1["y"] + c1["height"] / 2
        c2_ylo = c2["y"] - c2["height"] / 2
        c2_yhi = c2["y"] + c2["height"] / 2
        if c1_xhi < c2_xlo:
            p1x = c1_xhi
            p2x = c2_xlo
        elif c1_xlo > c2_xhi:
            p1x = c1_xlo
            p2x = c2_xhi
        else:
            p1x = c1["x"]
            p2x = c2["x"]
        if c1_yhi < c2_ylo:
            p1y = c1_yhi
            p2y = c2_ylo
        elif c1_ylo > c2_yhi:
            p1y = c1_ylo
            p2y = c2_yhi
        else:
            p1y = c1["y"]
            p2y = c2["y"]
        self.canvas.create_line(p1x, p1y, p2x, p2y,
                                width=2,
                                fill="black",
                                tags=f"{c1['id']}-{c2['id']}")

    def resize_concept(self, concept):
        "Adjust the width and height according to the the bounding box of the text."
        obj = self.canvas.create_text(0, 0, text=concept["text"])
        bbox = self.canvas.bbox(obj)
        concept["width"] = bbox[2] - bbox[0] + constants.CONCEPTMAP_XPADDING
        concept["height"] = bbox[3] - bbox[1] + constants.CONCEPTMAP_YPADDING
        self.canvas.delete(obj)

    def pick_concept(self, event):
        self.picked_concept = None
        overlapping = self.canvas.find_overlapping(event.x, event.y, event.x, event.y)
        if not overlapping:
            return
        for overlap in overlapping:
            for id in self.canvas.gettags(overlap):
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
        self.draw_relations(self.picked_concept)
        self.viewer.modified = True

    def remove_concept(self, concept):
        self.canvas.delete(concept["id"])
        self.concepts.remove(concept)
        self.concept_lookup.pop(concept["id"])


class EditConcept(tk.simpledialog.Dialog):
    "Dialog window for editing or creating a concept."

    def __init__(self, conceptmap, concept=None):
        self.conceptmap = conceptmap
        self.concept = concept
        if self.concept is None:
            super().__init__(conceptmap.viewer.toplevel,
                             title=Tr("Create concept"))
        else:
            super().__init__(conceptmap.viewer.toplevel,
                             title=f"{Tr('Edit concept')} {self.concept['id']}")

    def body(self, body):
        label = tk.ttk.Label(body, text=Tr("Concept"))
        label.grid(row=0, column=0, padx=4, sticky=tk.E)
        self.concept_entry = tk.Entry(body, width=50)
        if self.concept:
            self.concept_entry.insert(0, self.concept["text"])
        self.concept_entry.grid(row=0, column=1)

        label = tk.ttk.Label(body, text=Tr("Type"))
        label.grid(row=1, column=0, padx=4, sticky=tk.E)
        self.types_list = list(constants.CONCEPTMAP_TYPES.keys())
        self.concept_type = tk.Listbox(body, 
                                       listvariable=tk.StringVar(value=self.types_list),
                                       height=len(self.types_list))
        if self.concept:
            self.concept_type.selection_set(self.types_list.index(self.concept["type"]))
        else:
            self.concept_type.selection_set(0)
        self.concept_type.grid(row=1, column=1, sticky=(tk.W, tk.N))

        return self.concept_entry

    def remove(self):
        "Remove the concept."
        self.conceptmap.remove_concept(self.concept)
        self.cancel()

    def apply(self):
        self.result = dict(text=self.concept_entry.get())
        selected = self.concept_type.curselection()
        if selected:
            self.result["type"] = self.types_list[selected[0]]
        else:
            self.result["type"] = self.concept["type"]

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

