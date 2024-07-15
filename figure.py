"SVG figure in canvas within a text."

from icecream import ic

import tkinter as tk
import xml.etree.ElementTree as ET

import constants


ET.register_namespace("", constants.SVG_NS)


class Figure:

    def __init__(self, view, ast):
        self.view = view
        root = ET.fromstring(ast["children"][0]["children"])
        assert root.tag == constants.SVG
        self.state = State()
        self.state.update(root)
        self.canvas = tk.Canvas(self.view,
                                cursor=constants.FIGURE_CURSOR,
                                width=int(root.get("width", 300)),
                                height=int(root.get("height", 200)),
                                background=self.state["background-color"])
        self.view.window_create(tk.INSERT, window=self.canvas)
        for elem in root:
            match elem.tag:
                case constants.CIRCLE:
                    self.draw_circle(elem)
                case constants.RECT:
                    self.draw_rect(elem)

    def draw_circle(self, elem):
        cx = int(elem.get("cx", 0))
        cy = int(elem.get("cy", 0))
        r = int(elem.get("r", 1))
        with self.state as s:
            s.update(elem)
            self.canvas.create_oval(cx-r, cy-r, cx+r, cy+r,
                                    fill=s["fill"],
                                    outline=s["stroke"],
                                    width=s["stroke-width"])

    def draw_rect(self, elem):
        x = int(elem.get("x", 0))
        y = int(elem.get("y", 0))
        width = int(elem.get("width", 10))
        height = int(elem.get("height", 10))
        with self.state as s:
            s.update(elem)
            try:
                rx = int(elem.get("rx"))
            except TypeError:
                rx = None
            try:
                ry = int(elem.get("ry"))
            except TypeError:
                ry = None
            if rx is None:
                if ry is not None:
                    rx = ry
            elif ry is None:
                ry = rx
            if rx is None:
                self.canvas.create_rectangle(x, y, x+width, y+height,
                                             fill=s["fill"],
                                             outline=s["stroke"],
                                             width=s["stroke-width"])
            else:
                rx = min(width/2, rx)
                ry = min(height/2, ry)
                kwargs = dict(fill=s["fill"], width=0)
                self.canvas.create_rectangle(x, y+ry, x+width, y+height-ry, **kwargs)
                self.canvas.create_rectangle(x+rx, y, x+width-rx, y+ry, **kwargs)
                self.canvas.create_rectangle(x+rx, y+height, x+width-rx, y+height-ry, **kwargs)
                kwargs = dict(fill=s["fill"], width=0, outline="", style=tk.PIESLICE)
                self.canvas.create_arc(x+width, y, x+width-2*rx, y+2*ry, start=0, extent=90, **kwargs)
                self.canvas.create_arc(x, y, x+2*rx, y+2*ry, start=90, extent=90, **kwargs)
                self.canvas.create_arc(x, y+height, x+2*rx, y+height-2*ry, start=180, extent=90, **kwargs)
                self.canvas.create_arc(x+width, y+height, x+width-2*rx, y+height-2*ry, start=270, extent=90, **kwargs)
                kwargs = dict(outline=s["stroke"], width=s["stroke-width"], style=tk.ARC)
                self.canvas.create_arc(x+width, y, x+width-2*rx, y+2*ry, start=0, extent=90, **kwargs)
                self.canvas.create_arc(x, y, x+2*rx, y+2*ry, start=90, extent=90, **kwargs)
                self.canvas.create_arc(x, y+height, x+2*rx, y+height-2*ry, start=180, extent=90, **kwargs)
                self.canvas.create_arc(x+width, y+height, x+width-2*rx, y+height-2*ry, start=270, extent=90, **kwargs)
                kwargs = dict(fill=s["stroke"], width=s["stroke-width"])
                self.canvas.create_line(x+rx, y, x+width-rx, y, **kwargs)
                self.canvas.create_line(x+rx, y+height, x+width-rx, y+height, **kwargs)
                self.canvas.create_line(x, y+ry, x, y+height-ry, **kwargs)
                self.canvas.create_line(x+width, y+ry, x+width, y+height-ry, **kwargs)

class State:
    "Graphics state, limited implementation."

    default = {"fill": "white",
               "stroke": None,
               "stroke-width": "1",
               "background-color": "white"}

    def __init__(self):
        self.stack = [{}]

    def save(self):
        self.stack.append(self.stack[-1].copy())

    def restore(self):
        self.stack.pop()

    def __getitem__(self, key):
        try:
            return self.stack[-1][key]
        except KeyError:
            return self.default[key]

    def __setitem__(self, key, value):
        self.stack[-1][key] = value

    def update(self, elem):
        "Update by element attributes and style, where style has higher precedence."
        for key in self.default.keys():
            value = elem.get(key)
            if value is not None:
                self[key] = value
        style = elem.get("style")
        if style:
            for part in style.split(";"):
                key, value = part.split(":", 1)
                self[key.strip()] = value.strip()

    def __enter__(self):
        self.save()
        return self

    def __exit__(self, type, value, tb):
        if type is None:
            self.restore()
        return False
