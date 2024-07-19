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
    def __init__(self, viewer, text=None, title=None):
        import editor

        if text is None:
            self.data = dict(concepts=[], relations=[])
        else:
            self.data = yaml.safe_load(text)
        self.concepts = self.data["concepts"]
        self.relations = self.data["relations"]
        self.title = self.data.get("title") or title
        self.cid_count = 0
        self.rid_count = 0
        for concept in self.concepts:
            self.cid_count = max(int(concept["id"][3:]), self.cid_count)
        self.concepts_lookup = dict([(c["id"], c) for c in self.concepts])
        for relation in self.relations:
            self.rid_count = max(int(relation["id"][3:]), self.rid_count)
        self.relations_lookup = dict([(r["id"], r) for r in self.relations])
        self.viewer = viewer
        self.edit = isinstance(self.viewer, editor.Editor)
        if self.title:
            self.canvas_frame = tk.ttk.LabelFrame(
                viewer.view,
                padding=4,
                text=f" {self.title} ",
                cursor=constants.CONCEPTMAP_CURSOR,
            )
        else:
            self.canvas_frame = tk.ttk.Frame(
                viewer.view, padding=4, cursor=constants.CONCEPTMAP_CURSOR
            )
        viewer.view.window_create(tk.INSERT, window=self.canvas_frame)
        self.canvas_frame.rowconfigure(0, weight=1)
        self.canvas_frame.columnconfigure(0, weight=1)
        canvas = self.data.get("canvas", {})
        self.canvas = tk.Canvas(
            self.canvas_frame,
            width=canvas.get("width", constants.CONCEPTMAP_WIDTH),
            height=canvas.get("height", constants.CONCEPTMAP_HEIGHT),
            background="white",
        )
        self.canvas.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.W, tk.E))
        for concept in self.concepts:
            self.draw_concept(concept)
        for relation in self.relations:
            self.draw_relation(relation)
        self.canvas.bind("<ButtonPress-1>", self.select_concept)
        if self.edit:
            self.canvas.bind("<ButtonRelease-1>", self.stop_move_concept)
            self.canvas.bind("<Double-Button-1>", self.edit_entity)
            self.canvas.bind("<ButtonPress-3>", self.create_relation)
            self.canvas.bind("<Double-Button-3>", self.create_concept)
        self.picked_concept = None

    def __repr__(self):
        return f"```conceptmap\n{yaml.dump(self.data)}\n```\n"

    def create_concept(self, event):
        "Create a concept from scratch, or copy the one picked."
        concept = self.pick_concept(event)
        # Create a new concept from scratch.
        if concept is None:
            editor = EditConcept(self, concept)
            if editor.result is None:
                return
            self.cid_count += 1
            new = dict(
                id=f"cid{self.cid_count}",
                type="primary",
                x=event.x,
                y=event.y,
                width=100,
                height=20,
            )
            new.update(editor.result)
            self.resize_concept(new)
            self.concepts.append(new)
            self.concepts_lookup[new["id"]] = new
        # Copy the picked concept.
        else:
            new = concept.copy()
            self.cid_count += 1
            new["id"] = f"cid{self.cid_count}"
            new["x"] += 10
            new["y"] += 10
            self.draw_concept(new)
            self.concepts.append(new)
            self.concepts_lookup[new["id"]] = new
            editor = EditConcept(self, new)
            if editor.result is None:
                return
            new.update(editor.result)
            self.resize_concept(new)
        self.draw_concept(new)
        self.viewer.modified = True

    def delete_concept(self, concept):
        cid = concept["id"]
        self.canvas.delete(cid)
        self.concepts.remove(concept)
        self.concepts_lookup.pop(cid)
        relations = [
            r for r in self.relations if r["source"] == cid or r["target"] == cid
        ]
        for relation in relations:
            self.delete_relation(relation)
        self.viewer.modified = True

    def edit_entity(self, event):
        "Edit a concept or a relation."
        concept = self.pick_concept(event)
        if concept is None:
            relation = self.pick_relation(event)
            if relation is None:
                return
            editor = EditRelation(self, relation)
            if editor.result is None:
                return
            relation.update(editor.result)
            self.draw_relation(relation)
        else:
            editor = EditConcept(self, concept)
            if editor.result is None:
                return
            concept.update(editor.result)
            self.resize_concept(concept)
            self.concepts.remove(concept)  # Move to the top of the display list.
            self.concepts.append(concept)
            self.draw_concept(concept)
            self.draw_relations(concept)
        self.viewer.modified = True

    def draw_concept(self, concept):
        self.canvas.delete(concept["id"])
        type = constants.CONCEPTMAP_TYPES[concept["type"]]
        self.canvas.create_rectangle(
            concept["x"] - concept["width"] / 2,
            concept["y"] - concept["height"] / 2,
            concept["x"] + concept["width"] / 2,
            concept["y"] + concept["height"] / 2,
            outline="",
            fill=type["fill"],
            tags=concept["id"],
        )
        self.canvas.create_text(
            concept["x"],
            concept["y"],
            justify=tk.CENTER,
            text=concept["text"],
            fill=type["stroke"],
            tags=concept["id"],
        )

    def draw_relations(self, concept):
        "Draw all relations for a given concept."
        cid = concept["id"]
        for relation in self.relations:
            if relation["source"] == cid or relation["target"] == cid:
                self.draw_relation(relation)

    def draw_relation(self, relation):
        self.canvas.delete(relation["id"])
        c1 = self.concepts_lookup[relation["source"]]
        c2 = self.concepts_lookup[relation["target"]]
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
        type = constants.CONCEPTMAP_TYPES[relation["type"]]
        self.canvas.create_line(
            p1x,
            p1y,
            p2x,
            p2y,
            width=2,
            fill=type["fill"],
            arrow=tk.LAST,
            tags=relation["id"],
        )
        if relation.get("text"):
            tid = self.canvas.create_text(
                (p1x + p2x) / 2,
                (p1y + p2y) / 2,
                justify=tk.CENTER,
                text=relation["text"],
                fill="black",
                tags=relation["id"],
            )
            rid = self.canvas.create_rectangle(
                *self.canvas.bbox(tid), fill="white", width=0, tags=relation["id"]
            )
            self.canvas.tag_lower(rid, tid)

    def resize_concept(self, concept):
        "Adjust the width and height according to the the bounding box of the text."
        obj = self.canvas.create_text(0, 0, text=concept["text"])
        bbox = self.canvas.bbox(obj)
        concept["width"] = bbox[2] - bbox[0] + constants.CONCEPTMAP_XPADDING
        concept["height"] = bbox[3] - bbox[1] + constants.CONCEPTMAP_YPADDING
        self.canvas.delete(obj)

    def select_concept(self, event):
        if self.picked_concept is not None:
            for obj in self.canvas.find_withtag(self.picked_concept["id"]):
                if self.canvas.type(obj) == "rectangle":
                    self.canvas.itemconfigure(obj, outline="", width=1)
                    break
        self.picked_concept = self.pick_concept(event)
        if self.picked_concept is not None:
            for obj in self.canvas.find_withtag(self.picked_concept["id"]):
                if self.canvas.type(obj) == "rectangle":
                    self.canvas.itemconfigure(obj, outline="black", width=2)
                    break

    def pick_concept(self, event):
        overlapping = self.canvas.find_overlapping(event.x, event.y, event.x, event.y)
        if not overlapping:
            return None
        for overlap in overlapping:
            for id in self.canvas.gettags(overlap):
                if id.startswith("cid"):
                    self.starting_coords = (event.x, event.y)
                    if self.edit:
                        self.canvas.bind("<B1-Motion>", self.move_concept)
                    return self.concepts_lookup[id]
        return None

    def pick_relation(self, event):
        overlapping = self.canvas.find_closest(event.x, event.y, halo=2)
        if not overlapping:
            return None
        for overlap in overlapping:
            for id in self.canvas.gettags(overlap):
                if id.startswith("rid"):
                    return self.relations_lookup[id]
        return None

    def stop_move_concept(self, event):
        self.canvas.unbind("<B1-Motion>")

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

    def create_relation(self, event):
        source = self.picked_concept
        target = self.pick_concept(event)
        if source is None:
            return
        if target is None:
            return
        if source is target:
            return
        self.rid_count += 1
        relation = {
            "id": f"rid{self.rid_count}",
            "source": source["id"],
            "target": target["id"],
            "type": "dark",
        }
        self.relations.append(relation)
        self.relations_lookup[relation["id"]] = relation
        self.draw_relation(relation)
        self.viewer.modified = True

    def delete_relation(self, relation):
        rid = relation["id"]
        self.canvas.delete(rid)
        self.relations.remove(relation)
        self.relations_lookup.pop(rid)
        self.viewer.modified = True


class EditConcept(tk.simpledialog.Dialog):
    "Dialog window for editing or creating a concept."

    def __init__(self, conceptmap, concept=None):
        self.conceptmap = conceptmap
        self.concept = concept
        if self.concept is None:
            super().__init__(conceptmap.viewer.toplevel, title=Tr("Create concept"))
        else:
            super().__init__(
                conceptmap.viewer.toplevel,
                title=f"{Tr('Edit concept')} {self.concept['id']}",
            )

    def body(self, body):
        label = tk.ttk.Label(body, text=Tr("Text"))
        label.grid(row=0, column=0, padx=4, sticky=tk.E)
        self.concept_entry = tk.Entry(body, width=50)
        if self.concept:
            self.concept_entry.insert(0, self.concept.get("text", ""))
        self.concept_entry.grid(row=0, column=1)

        label = tk.ttk.Label(body, text=Tr("Type"))
        label.grid(row=1, column=0, padx=4, sticky=(tk.E, tk.N))
        self.types_list = list(constants.CONCEPTMAP_TYPES.keys())
        self.concept_type = tk.Listbox(
            body,
            listvariable=tk.StringVar(value=self.types_list),
            height=len(self.types_list),
        )
        if self.concept:
            self.concept_type.selection_set(self.types_list.index(self.concept["type"]))
        else:
            self.concept_type.selection_set(0)
        self.concept_type.grid(row=1, column=1, sticky=(tk.W, tk.N))

        return self.concept_entry

    def buttonbox(self):
        box = tk.Frame(self)
        w = tk.ttk.Button(
            box, text=Tr("OK"), width=10, command=self.ok, default=tk.ACTIVE
        )
        w.pack(side=tk.LEFT, padx=5, pady=5)
        w = tk.ttk.Button(
            box,
            text=Tr("Delete"),
            width=10,
            command=self.delete,
            state=tk.DISABLED if self.concept is None else tk.NORMAL,
        )
        w.pack(side=tk.LEFT, padx=5, pady=5)
        w = tk.ttk.Button(box, text=Tr("Cancel"), width=10, command=self.cancel)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)
        box.pack()

    def delete(self):
        "Delete the concept and its relations."
        self.conceptmap.delete_concept(self.concept)
        self.cancel()

    def apply(self):
        self.result = dict(
            text=self.concept_entry.get(),
            type=self.types_list[self.concept_type.curselection()[0]],
        )


class EditRelation(tk.simpledialog.Dialog):
    "Dialog window for editing or creating a relation."

    def __init__(self, conceptmap, relation=None):
        self.conceptmap = conceptmap
        self.relation = relation
        if self.relation is None:
            super().__init__(conceptmap.viewer.toplevel, title=Tr("Create relation"))
        else:
            super().__init__(
                conceptmap.viewer.toplevel,
                title=f"{Tr('Edit relation')} {self.relation['id']}",
            )

    def body(self, body):
        label = tk.ttk.Label(body, text=Tr("text"))
        label.grid(row=0, column=0, padx=4, sticky=tk.E)
        self.relation_entry = tk.Entry(body, width=50)
        if self.relation:
            self.relation_entry.insert(0, self.relation.get("text", ""))
        self.relation_entry.grid(row=0, column=1)

        label = tk.ttk.Label(body, text=Tr("Type"))
        label.grid(row=1, column=0, padx=4, sticky=(tk.E, tk.N))
        self.types_list = list(constants.CONCEPTMAP_TYPES.keys())
        self.relation_type = tk.Listbox(
            body,
            listvariable=tk.StringVar(value=self.types_list),
            height=len(self.types_list),
        )
        if self.relation:
            self.relation_type.selection_set(
                self.types_list.index(self.relation["type"])
            )
        else:
            self.relation_type.selection_set(0)
        self.relation_type.grid(row=1, column=1, sticky=(tk.W, tk.N))

        return self.relation_type

    def buttonbox(self):
        box = tk.Frame(self)
        w = tk.ttk.Button(
            box, text=Tr("OK"), width=10, command=self.ok, default=tk.ACTIVE
        )
        w.pack(side=tk.LEFT, padx=5, pady=5)
        w = tk.ttk.Button(
            box,
            text=Tr("Delete"),
            width=10,
            command=self.delete,
            state=tk.DISABLED if self.relation is None else tk.NORMAL,
        )
        w.pack(side=tk.LEFT, padx=5, pady=5)
        w = tk.ttk.Button(box, text=Tr("Cancel"), width=10, command=self.cancel)
        w.pack(side=tk.LEFT, padx=5, pady=5)
        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)
        box.pack()

    def delete(self):
        "Delete the relation."
        self.conceptmap.delete_relation(self.relation)
        self.cancel()

    def apply(self):
        self.result = dict(
            text=self.relation_entry.get(),
            type=self.types_list[self.relation_type.curselection()[0]],
        )
