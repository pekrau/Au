"Book source Markdown text in files and directories."

from icecream import ic

import os
import re

import marko
import marko.ast_renderer
import marko.inline
import marko.helpers
import marko.ext.gfm
import yaml

import constants

FRONTMATTER = re.compile(r"^---([\n\r].*?[\n\r])---[\n\r](.*)$", re.DOTALL)


class Book:
    "Book source Markdown text in files and directories."

    def __init__(self, absdirpath):
        self.absdirpath = absdirpath
        self.title = os.path.basename(absdirpath)
        self.read()

    @property
    def abspath(self):
        return self.absdirpath

    def __str__(self):
        return self.title

    def read(self):
        self.items = []

        # Section and Text instances for directories and files that actually exist.
        for itemname in sorted(os.listdir(self.absdirpath)):

            # Skip hard-wired special directories.
            if itemname == constants.ARCHIVE_DIRNAME:
                continue
            if itemname == constants.REFERENCES_DIRNAME:
                continue
            if itemname == constants.TODO_DIRNAME:
                continue

            itempath = os.path.join(self.absdirpath, itemname)
            if os.path.isdir(itempath):
                self.items.append(Section(self, itemname))
            elif itemname.endswith(constants.MARKDOWN_EXT):
                self.items.append(Text(self, itemname))
            else:
                pass

    @property
    def texts(self):
        result = []
        for item in self.items:
            result.extend(item.texts)
        return result


class Item:

    def __init__(self, parent, title):
        self.parent = parent
        self.title = title
        self.read()

    def __str__(self):
        return self.title

    @property
    def fulltitle(self):
        if isinstance(self.parent, Book):
            return self.title
        else:
            return os.path.join(self.parent.fulltitle, self.title)

    @property
    def abspath(self):
        raise NotImplementedError

    def read(self):
        raise NotImplementedError
        
    def retitle(self, newtitle):
        raise NotImplementedError

    def move_up(self):
        raise NotImplementedError

    def move_down(self, section):
        raise NotImplementedError

    def copy(self, title):
        raise NotImplementedError

    def delete(self):
        raise NotImplementedError

    def archive(self)
        raise NotImplementedError


class Section(Item):

    def __init__(self, parent, title):
        self.items = []
        super().__init__(parent, title)

    @property
    def abspath(self):
        return os.path.join(self.parent.abspath, self.title)

    def read(self):
        for itemname in sorted(os.listdir(self.abspath)):
            itempath = os.path.join(self.abspath, itemname)
            if os.path.isdir(itempath):
                self.items.append(Section(self, itemname))
            elif itemname.endswith(constants.MARKDOWN_EXT):
                self.items.append(Text(self, itemname))
            else:
                pass

    @property
    def texts(self):
        result = []
        for item in self.items:
            result.extend(item.texts)
        return result


class Text(Item):

    def __init__(self, parent, title):
        title, ext = os.path.splitext(title)
        assert ext == constants.MARKDOWN_EXT
        super().__init__(parent, title)

    @property
    def abspath(self):
        return os.path.join(self.parent.abspath, self.title + constants.MARKDOWN_EXT)

    def read(self):
        with open(self.abspath) as infile:
            content = infile.read()
        match = FRONTMATTER.match(content)
        if match:
            self.frontmatter = yaml.safe_load(match.group(1))
            content = content[match.start(2):]
        else:
            self.frontmatter = dict()
        self.ast = parser.convert(content)

    @property
    def texts(self):
        return [self]

    def write(self):
        raise NotImplementedError
        

class Indexed(marko.inline.InlineElement):
    "Markdown indexed term."

    pattern = re.compile(r"\[#(.+?)\]")
    parse_children = False

    def __init__(self, match):
        self.target = match.group(1).strip()


class Reference(marko.inline.InlineElement):
    "Markdown reference."

    pattern = re.compile(r"\[@(.+?)\]")
    parse_children = False

    def __init__(self, match):
        self.target = match.group(1).strip()


parser = marko.Markdown(renderer=marko.ast_renderer.ASTRenderer)
parser.use("footnote")
parser.use(marko.helpers.MarkoExtension(elements=[
    marko.ext.gfm.elements.Table,
    marko.ext.gfm.elements.TableRow,
    marko.ext.gfm.elements.TableCell
]))
parser.use(marko.helpers.MarkoExtension(elements=[Indexed, Reference]))


if __name__ == "__main__":
    book = Book("/home/pekrau/Att konfrontera lejonen")
    book.read()
    ic([t.fulltitle for t in book.texts])
