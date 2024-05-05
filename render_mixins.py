"Mixin classes containing methods to render Marko AST to tk.Text instance."

from icecream import ic

import tkinter as tk

import constants
import utils


class BaseRenderMixin:
    """Mixin class containing basic methods to render Marko AST to tk.Text instance.
    It assumes an attribute '.view'; instance of tk.Text.
    """

    def render(self, ast):
        try:
            method = getattr(self, f"render_{ast['element']}")
        except AttributeError:
            ic("Could not handle ast", ast)
        else:
            method(ast)

    def get_prev_line_blank(self):
        try:
            return self._prev_line_blank
        except AttributeError:
            self._prev_line_blank = True
            return self._prev_line_blank

    def set_prev_line_blank(self, value):
        self._prev_line_blank = value

    prev_line_blank = property(get_prev_line_blank, set_prev_line_blank)

    def render_document(self, ast):
        self.prev_line_blank = True
        for child in ast["children"]:
            self.render(child)

    def render_heading(self, ast):
        self.conditional_line_break()
        first = self.view.index(tk.INSERT)
        h = constants.H.get(ast["level"], constants.H4)
        for child in ast["children"]:
            self.render(child)
        self.view.tag_add(h, first, tk.INSERT)
        self.conditional_line_break()

    def render_paragraph(self, ast):
        self.conditional_line_break(flag=True)
        for child in ast["children"]:
            self.render(child)

    def render_emphasis(self, ast):
        first = self.view.index(tk.INSERT)
        for child in ast["children"]:
            self.render(child)
        self.view.tag_add(constants.ITALIC, first, tk.INSERT)

    def render_strong_emphasis(self, ast):
        first = self.view.index(tk.INSERT)
        for child in ast["children"]:
            self.render(child)
        self.view.tag_add(constants.BOLD, first, tk.INSERT)

    def render_raw_text(self, ast):
        children = ast["children"]
        if type(children) == str:
            if children[-1] == "\n":
                children[-1] = " "
            self.view.insert(tk.INSERT, children)
        elif type(children) == list:
            for child in ast["children"]:
                self.render(child)

    def render_line_break(self, ast):
        self.view.insert(tk.INSERT, " ")

    def render_blank_line(self, ast):
        self.view.insert(tk.INSERT, "\n")
        self.prev_line_blank = False

    def render_link(self, ast):
        first = self.view.index(tk.INSERT)
        for child in ast["children"]:
            self.render(child)
        self.link_create(ast["dest"], ast["title"], first, self.view.index(tk.INSERT))

    def render_quote(self, ast):
        self.conditional_line_break(flag=True)
        first = self.view.index(tk.INSERT)
        for child in ast["children"]:
            self.render(child)
        self.view.tag_add("quote", first, tk.INSERT)

    def render_literal(self, ast):
        self.view.insert(tk.INSERT, ast["children"])

    def render_thematic_break(self, ast):
        self.conditional_line_break()
        self.view.insert(tk.INSERT, "\u2014" * 20, (constants.THEMATIC_BREAK,))

    def render_list(self, ast):
        try:
            count = len(self.list_lookup)
        except AttributeError:
            self.list_lookup = dict()
            count = 0
        tag = f"{constants.LIST_PREFIX}{count}"
        data = dict(tag=tag,
                    ordered=ast["ordered"],
                    start=ast["start"],
                    count=ast["start"],
                    tight=ast["tight"])
        self.list_lookup[tag] = data
        try:
            self.list_stack.append(data)
        except AttributeError:
            self.list_stack = [data]
        data["depth"] = len(self.list_stack)
        if data["tight"]:
            self.view.insert(tk.INSERT, "\n")
        self.prev_line_blank = True
        first = self.view.index(tk.INSERT)
        for child in ast["children"][:-1]:
            self.render(child)
            self.view.insert(tk.INSERT, "\n")
            self.prev_line_blank = True
        for child in ast["children"][-1:]:
            self.render(child)
        self.view.tag_configure(tag,
                                lmargin1=data["depth"]*constants.LIST_INDENT,
                                lmargin2=(data["depth"]+0.5)*constants.LIST_INDENT)
        self.view.tag_add(tag, first, tk.INSERT)
        self.list_stack.pop()

    def render_list_item(self, ast):
        data = self.list_stack[-1]
        if not data["tight"]:
            self.view.insert(tk.INSERT, "\n")
        if data["ordered"]:
            bullet = f"{data['count']}. "
            data["count"] += 1
        else:
            level = 0
            for prev in reversed(self.list_stack[:-1]):
                if prev["ordered"]:
                    break
                level += 1
            try:
                bullet = constants.LIST_BULLETS[level]
            except IndexError:
                bullet = constants.LIST_BULLETS[-1]
            bullet += " "
        first = self.view.index(tk.INSERT)
        self.view.insert(tk.INSERT, bullet, (constants.LIST_BULLET, ))
        for child in ast["children"]:
            self.render(child)
        self.view.tag_add(data["tag"], first, tk.INSERT)

    def render_indexed(self, ast):
        # Position here is not useful; will be affected by footnotes.
        tag = constants.INDEXED_PREFIX + ast["canonical"]
        self.view.insert(tk.INSERT, ast["term"], (constants.INDEXED, tag))

    def render_reference(self, ast):
        # Position here is not useful; will be affected by footnotes.
        tag = constants.REFERENCE_PREFIX + ast["reference"]
        self.view.insert(tk.INSERT, f"{ast['reference']}", (constants.REFERENCE, tag))

    def conditional_line_break(self, flag=False):
        if not self.prev_line_blank:
            self.view.insert(tk.INSERT, "\n")
            try:
                if self.list_stack:
                    self.view.insert(tk.INSERT, "  ") # Empirically two blanks.
            except AttributeError:
                pass
            self.prev_line_blank = flag

    def locate_indexed(self):
        "Get the final positions of the indexed terms; affected by footnotes."
        self.indexed = dict()
        for tag in self.view.tag_names():
            if not tag.startswith(constants.INDEXED_PREFIX):
                continue
            canonical = tag[len(constants.INDEXED_PREFIX):]
            range = self.view.tag_nextrange(tag, "1.0")
            while range:
                self.indexed.setdefault(canonical, set()).add(range[0])
                range = self.view.tag_nextrange(tag, range[0] + "+1c")

    def locate_references(self):
        "Get the final positions of the references; affected by footnotes."
        self.references = dict()
        range = self.view.tag_nextrange(constants.REFERENCE, "1.0")
        while range:
            self.references.setdefault(self.view.get(*range), set()).add(range[0])
            range = self.view.tag_nextrange(constants.REFERENCE, range[0] + "+1c")


class FootnoteRenderMixin:
    """Mixin class containing  methods to render footnote Marko AST to tk.Text instance.
    It assumes the presence of an attribute 'view'; instance of tk.Text.
    """

    def render_footnote_ref(self, ast):
        label = ast["label"]
        tag = constants.FOOTNOTE_REF_PREFIX + label
        self.footnotes[label] = dict(label=label, tag=tag)
        self.view.insert(tk.INSERT, f"^{label}", (constants.FOOTNOTE_REF, tag))
        self.view.tag_bind(tag, "<Button-1>", self.footnote_toggle)

    def render_footnote_def(self, ast):
        tag = self.footnotes[ast["label"]]["tag"]
        first = self.view.tag_nextrange(tag, "1.0")[1]
        self.view.mark_set(tk.INSERT, first)
        for child in ast["children"]:
            self.render(child)
        self.view.tag_add(constants.FOOTNOTE_DEF, first + "+1c", tk.INSERT)
        tag = constants.FOOTNOTE_DEF_PREFIX + ast["label"]
        self.tag_elide(tag)
        self.view.tag_add(tag, first, tk.INSERT)

    def init_elided_tags(self):
        """Horrible work-around for apparent Tk/Tcl bug that affects
        searches ot text with tags for elided parts.
        Keep track of all tags set as elided, so that they can be
        temporarily be unelided before a search, and restored after.
        """
        self.elided_tags = set()

    def tag_toggle_elide(self, tag):
        if int(self.view.tag_cget(tag, "elide")):
            self.tag_configure_not_elide(tag)
        else:
            self.tag_configure_elide(tag)

    def tag_elide(self, tag):
        self.view.tag_configure(tag, elide=True)
        self.elided_tags.add(tag)

    def tag_not_elide(self, tag):
        self.view.tag_configure(tag, elide=False)
        self.elided_tags.remove(tag)

    def tags_inhibit_elide(self):
        "Before search, temporarily set all elide tags to not elide."
        for tag in self.elided_tags:
            self.view.tag_configure(tag, elide=False)

    def tags_restore_elide(self):
        "After search, set all elide tags to elide again."
        for tag in self.elided_tags:
            self.view.tag_configure(tag, elide=True)
