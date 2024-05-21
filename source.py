"Tree of source Markdown texts in files and directories."

from icecream import ic

import datetime
import os
import re
import shutil
import tarfile
import time

import marko
import marko.ast_renderer
import marko.inline
import marko.helpers
import marko.ext.gfm
import yaml

import constants

FRONTMATTER = re.compile(r"^---([\n\r].*?[\n\r])---[\n\r](.*)$", re.DOTALL)


class Source:
    "Tree of source Markdown texts in files and directories."

    def __init__(self, absdirpath):
        self.absdirpath = absdirpath
        self.name = os.path.basename(absdirpath)
        self.read()

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"Source('{self}')"

    def __len__(self):
        return sum([len(i) for i in self.all_items])

    def __getitem__(self, fullname):
        return self.lookup[fullname]

    @property
    def abspath(self):
        return self.absdirpath

    @property
    def fullname(self):
        return ""

    @property
    def parent(self):
        return None

    @property
    def depth(self):
        return 0

    @property
    def all_items(self):
        "Return list of all sub-items. Self is *not* included."
        result = []
        for item in self.items:
            result.append(item)
            result.extend(item.all_items)
        return result

    @property
    def all_texts(self):
        "Return list of all sub-items that are texts."
        result = []
        for item in self.items:
            result.extend(item.all_texts)
        return result

    @property
    def is_text(self):
        return False

    def read(self):
        self.items = []

        # Section and Text instances for directories and files that actually exist.
        for itemname in sorted(os.listdir(self.absdirpath)):
            # Skip hard-wired special directories.
            if itemname == constants.ARCHIVE_DIRNAME:
                continue
            if itemname == constants.REFERENCES_DIRNAME:
                continue

            itempath = os.path.join(self.absdirpath, itemname)
            if os.path.isdir(itempath):
                self.items.append(Section(self, self, itemname))
            elif itemname.endswith(constants.MARKDOWN_EXT):
                self.items.append(Text(self, self, itemname))
            else:
                pass

        self.lookup = {}
        for item in self.all_items:
            self.lookup[item.fullname] = item

    def get(self, fullname, default=None):
        return self.lookup.get(fullname, default)

    def get_config(self):
        return dict(items=[i.get_config() for i in self.items])

    def apply_config(self, config):
        original = dict([(i.name, i) for i in self.items])
        self.items = []
        for ordered in config.get("items", []):
            try:
                item = original.pop(ordered["name"])
            except KeyError:
                pass
            else:
                self.items.append(item)
                item.apply_config(ordered)
        self.items.extend(original.values())

    def create_text(self, name, anchor=None):
        """Create a new empty text inside the anchor if it is a section,
        or after anchor if it is a text.
        Raise ValueError if there is a problem.
        """
        check_invalid_characters(name)
        if anchor is None:
            section = self
        elif anchor.is_text:
            section = anchor.parent
        else:
            section = anchor
        fullpath = os.path.join(section.abspath, name + constants.MARKDOWN_EXT)
        if os.path.exists(fullpath):
            raise ValueError(f"The name is already in use within '{section.fullname}'.")
        with open(fullpath, "w") as outfile:
            pass
        new = Text(self, section, name)
        if anchor is None:
            section.items.append(new)
        elif anchor.is_text:
            section.items.insert(anchor.index + 1, new)
        else:
            section.items.append(new)
        self.lookup[new.fullname] = new
        return new

    def create_section(self, anchor, name):
        """Create a new empty section inside the anchor if it is a section,
        or after anchor if it is a text.
        Raise ValueError if there is a problem.
        """
        check_invalid_characters(name)
        if anchor.is_text:
            section = anchor.parent
        else:
            section = anchor
        fullpath = os.path.join(section.abspath, name)
        if os.path.exists(fullpath):
            raise ValueError(f"The name is already in use within '{section.fullname}'.")
        os.mkdir(fullpath)
        new = Section(self, section, name)
        if anchor.is_text:
            section.items.insert(anchor.index + 1, new)
        else:
            section.items.append(new)
        self.lookup[new.fullname] = new
        return new

    def archive(self, sources=None):
        """Write all files for texts to a gzipped tar file.
        Optionally include items from other sources, using the name of each
        source as prefix; effectively a subdirectory.
        Return the number of items written.
        Raise an OSError if any error.
        """
        filename = time.strftime(constants.TIME_ISO_FORMAT, time.localtime()) + ".tgz"
        archivefilepath = os.path.join(
            self.absdirpath, constants.ARCHIVE_DIRNAME, filename
        )
        with tarfile.open(archivefilepath, "x:gz") as archivefile:
            # By looping over top-level items, the special directories are avoided.
            for item in self.items:
                archivefile.add(item.abspath, arcname=item.filename(), recursive=True)

            if sources:
                if not isinstance(sources, list):
                    sources = [sources]
                for source in sources:
                    archivefile.add(source.abspath, arcname=source.name, recursive=True)
        with tarfile.open(archivefilepath) as archivefile:
            result = len(archivefile.getnames())
        return result

    def check_integrity(self):
        assert os.path.exists(self.abspath), (self, self.abspath)
        assert os.path.isdir(self.abspath), (self, self.abspath)
        assert len(self.lookup) == len(self.all_items), (self, len(self.lookup), len(self.all_items))
        for item in self.all_items:
            assert item.source is self, (self, item)
            assert isinstance(item, Text) or isinstance(item, Section), (self, item)
            item.check_integrity()
        for text in self.all_texts:
            assert isinstance(text, Text), (self, text)
        # XXX Check that no extra files/dirs exist.


class Item:
    "Abstract class for sections and texts."

    def __init__(self, source, parent, name):
        self.source = source
        self.parent = parent
        self.name = name
        self.read()

    def __str__(self):
        return self.name

    def __repr__(self):
        return f"{self.__class__.__name__}('{self.fullname}')"

    @property
    def fullname(self):
        if isinstance(self.parent, Source):
            return self.name
        else:
            return os.path.join(self.parent.fullname, self.name)

    @property
    def depth(self):
        result = 0
        parent = self.parent
        while parent is not None:
            result += 1
            parent = parent.parent
        return result

    @property
    def is_text(self):
        return isinstance(self, Text)

    @property
    def is_section(self):
        return isinstance(self, Section)

    @property
    def index(self):
        "The index of this item among its siblings."
        for result, item in enumerate(self.parent.items):
            if item is self:
                return result

    @property
    def prev(self):
        "Previous sibling or None."
        index = self.index
        if index == 0:
            return None
        return self.parent.items[index - 1]

    @property
    def next(self):
        "Next sibling or None."
        try:
            return self.parent.items[self.index + 1]
        except IndexError:
            return None

    @property
    def parentpath(self):
        if isinstance(self.parent, Source):
            return ""
        else:
            return self.parent.fullname

    def filename(self, newname=None):
        "To be implemented by inheriting classes."
        raise NotImplementedError

    @property
    def abspath(self):
        return os.path.join(self.parent.abspath, self.filename())

    @property
    def age(self):
        "Get the age of the file."
        now = datetime.datetime.today()
        modified = datetime.datetime.fromtimestamp(os.path.getmtime(self.abspath))
        age = now - modified
        if age.days >= 365.25:
            value = age.days / 365.25
            unit = "yrs"
        elif age.days >= 30.5:
            value = age.days / 30.5
            unit = "mths"
        elif age.days >= 1:
            value = age.days + age.seconds / 86400.0
            unit = "days"
        elif age.seconds >= 3600.0:
            value = age.seconds / 3600.0
            unit = "hrs"
        elif age.seconds >= 60.0:
            value = age.seconds / 60.0
            unit = "mins"
        else:
            value = age.seconds + age.microseconds / 1000000.0
            unit = "secs"
        return f"{value:.0f} {unit}"

    @property
    def shown(self):
        "Are all parent sections open?"
        parent = self.parent
        while parent is not self.source:
            if not parent.open:
                return False
            parent = parent.parent
        return True

    def read(self):
        "To be implemented by inheriting classes."
        raise NotImplementedError

    def get_config(self):
        "To be implemented by inheriting classes."
        raise NotImplementedError

    def apply_config(self, config):
        "To be implemented by inheriting classes."
        raise NotImplementedError

    def rename(self, newname):
        """Rename the item.
        Raise ValueError if any problem.
        """
        if newname == self.name:
            return
        if not newname:
            raise ValueError("Empty string given for name.")
        check_invalid_characters(newname)
        newabspath = os.path.join(self.parent.abspath, self.filename(newname))
        if os.path.exists(newabspath):
            raise ValueError("The name is already in use.")
        oldfullnames = [self.fullname] + [i.fullname for i in self.all_items]
        oldabspath = self.abspath
        self.name = newname
        os.rename(oldabspath, self.abspath)
        self.replace_in_lookup(oldfullnames)

    def replace_in_lookup(self, oldfullnames):
        for oldfullname in oldfullnames:
            item = self.source.lookup.pop(oldfullname)
            self.source.lookup[item.fullname] = item

    def move_up(self):
        """Move this item one step towards the beginning of its list of sibling items.
        Raise ValueError if no movement was possible; already at the start of the list.
        """
        pos = self.parent.items.index(self)
        if pos == 0:
            raise ValueError("Item already at the start of the list.")
        self.parent.items.insert(pos - 1, self.parent.items.pop(pos))

    def move_down(self):
        """Move this item one step down towards the end of its list of sibling items.
        Raise ValueError if no movement was possible; already at the end of the list.
        """
        pos = self.parent.items.index(self)
        if pos == len(self.parent.items) - 1:
            raise ValueError("Item already at the end of the list.")
        self.parent.items.insert(pos + 1, self.parent.items.pop(pos))

    def move_to_parent(self):
        """Move this item one level up to the parent.
        It is placed after the old parent.
        Raise ValueError if any problem.
        """
        if self.parent == self.source:
            raise ValueError("Item is already at the top level.")
        newabspath = os.path.join(self.parent.parent.abspath, self.filename())
        if os.path.exists(newabspath):
            raise ValueError("Item cannot be moved up due to name collision.")
        oldabspath = self.abspath
        oldfullnames = [self.fullname] + [i.fullname for i in self.all_items]
        before = self.parent.next
        self.parent.items.remove(self)
        if before:
            self.parent.parent.items.insert(before.index, self)
        else:
            self.parent.parent.items.append(self)
        self.parent = self.parent.parent
        os.rename(oldabspath, self.abspath)
        self.replace_in_lookup(oldfullnames)

    def move_to_section(self, section):
        """Move this item one level down to the given section.
        It is placed last among the items of the section.
        Raise ValueError if any problem.
        """
        if not isinstance(section, Section):
            raise ValueError("Cannot move down into a non-section.")
        if section in self.all_items:
            raise ValueError("Cannot move down into a subsection of this section.")
        newabspath = os.path.join(section.abspath, self.filename())
        if os.path.exists(newabspath):
            raise ValueError("Item cannot be moved down due to name collision.")
        oldabspath = self.abspath
        oldfullnames = [self.fullname] + [i.fullname for i in self.all_items]
        self.parent.items.remove(self)
        section.items.append(self)
        self.parent = section
        os.rename(oldabspath, self.abspath)
        self.replace_in_lookup(oldfullnames)

    def copy(self, newname):
        "Common code for section and text copy operations."
        if newname == self.name:
            raise ValueError("Cannot copy to the same name.")
        if not newname:
            raise ValueError("Empty string given for name.")
        check_invalid_characters(newname)
        newabspath = os.path.join(self.parent.abspath, self.filename(newname))
        if os.path.exists(newabspath):
            raise ValueError("The name is already in use.")
        return newabspath

    def delete(self):
        "To be implemented by inheriting classes."
        raise NotImplementedError

    def check_integrity(self):
        assert isinstance(self.source, Source), self
        assert self in self.parent.items, self
        assert self.fullname in self.source.lookup, self
        assert os.path.exists(self.abspath), self


class Section(Item):
    "Directory."

    def __init__(self, source, parent, name):
        self.items = []
        self.open = False
        super().__init__(source, parent, name)

    def __len__(self):
        return sum([len(i) for i in self.all_items])

    @property
    def all_items(self):
        "Return list of all sub-items. Self is not included."
        result = []
        for item in self.items:
            result.append(item)
            result.extend(item.all_items)
        return result

    @property
    def all_texts(self):
        "Return list of all sub-items that are texts."
        result = []
        for item in self.items:
            result.extend(item.all_texts)
        return result

    def filename(self, newname=None):
        if newname:
            return newname
        else:
            return self.name

    def read(self):
        for itemname in sorted(os.listdir(self.abspath)):
            itempath = os.path.join(self.abspath, itemname)
            if os.path.isdir(itempath):
                self.items.append(Section(self.source, self, itemname))
            elif itemname.endswith(constants.MARKDOWN_EXT):
                self.items.append(Text(self.source, self, itemname))
            else:
                pass

    def get_config(self):
        return dict(
            type="section",
            name=self.name,
            open=self.open,
            items=[i.get_config() for i in self.items],
        )

    def apply_config(self, config):
        assert config["type"] == "section"
        self.open = bool(config.get("open"))
        original = dict([(i.name, i) for i in self.items])
        self.items = []
        for ordered in config["items"]:
            try:
                item = original.pop(ordered["name"])
            except KeyError:
                pass
            else:
                self.items.append(item)
                item.apply_config(ordered)
        self.items.extend(original.values())

    def copy(self, newname):
        newabspath = super().copy(newname)
        shutil.copytree(self.abspath, newabspath)
        new = Section(self.source, self.parent, newname)
        self.parent.items.append(new)
        for item in new.all_items:
            self.source.lookup[item.fullname] = item
        return new

    def delete(self):
        shutil.rmtree(self.abspath)
        for item in self.all_items:
            self.source.lookup.pop(item.fullname)
        self.source.lookup.pop(self.fullname)
        self.parent.items.remove(self)
        self.source = None
        self.parent = None

    def check_integrity(self):
        super().check_integrity()
        assert os.path.isdir(self.abspath), self


class Text(Item):
    "Markdown file."

    def __init__(self, source, parent, name):
        name, ext = os.path.splitext(name)
        assert not ext or ext == constants.MARKDOWN_EXT
        super().__init__(source, parent, name)

    def __len__(self):
        return 1

    def __getitem__(self, key):
        return self.frontmatter[key]

    def __setitem__(self, key, value):
        self.frontmatter[key] = value

    def __contains__(self, key):
        return key in self.frontmatter

    @property
    def all_items(self):
        "Return list of all sub-items. Self is *not* included."
        return []

    @property
    def all_texts(self):
        "Return list of all sub-items that are texts. Self *is* included."
        return [self]

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def pop(self, key, default=None):
        return self.frontmatter.pop(key, default)

    def get_status(self):
        return constants.Status.lookup(self.get("status"), default=constants.STARTED)

    def set_status(self, status):
        if type(status) == str:
            status = constants.Status.lookup(status)
            if status is None:
                raise ValueError("Invalid status value.")
        elif not isinstance(status, constants.Status):
            raise ValueError("Invalid status instance.")
        self.frontmatter["status"] = repr(status)

    status = property(get_status, set_status)

    def filename(self, newname=None):
        if newname:
            return newname + constants.MARKDOWN_EXT
        else:
            return self.name + constants.MARKDOWN_EXT

    def read(self):
        with open(self.abspath) as infile:
            content = infile.read()
        match = FRONTMATTER.match(content)
        if match:
            self.frontmatter = yaml.safe_load(match.group(1))
            content = content[match.start(2) :]
        else:
            self.frontmatter = {}
        self.ast = parser.convert(content)

    def get_config(self):
        return dict(type="text", name=self.name, status=repr(self.status))

    def apply_config(self, config):
        assert config["type"] == "text"

    def copy(self, newname):
        newabspath = super().copy(newname)
        shutil.copy2(self.abspath, newabspath)
        new = Text(self.source, self.parent, newname + constants.MARKDOWN_EXT)
        self.parent.items.append(new)
        self.source.lookup[new.fullname] = new
        return new

    def delete(self):
        os.remove(self.abspath)
        self.source.lookup.pop(self.fullname)
        self.parent.items.remove(self)
        self.source = None
        self.parent = None

    def write(self, content=None):
        "Write the text, with current frontmatter and the given Markdown content."
        with open(self.abspath, "w") as outfile:
            outfile.write("---\n")
            outfile.write(yaml.dump(self.frontmatter))
            outfile.write("---\n")
            if content:
                outfile.write(content)

    def check_integrity(self):
        super().check_integrity()
        assert os.path.isfile(self.abspath)


class Indexed(marko.inline.InlineElement):
    "Markdown extension for indexed term."

    pattern = re.compile(r"\[#(.+?)(\|(.+?))?\]")  # I know, this isn't quite right.
    parse_children = False

    def __init__(self, match):
        self.term = match.group(1).strip()
        if match.group(3):  # Because of the not-quite-right regexp...
            self.canonical = match.group(3).strip()
        else:
            self.canonical = self.term


class Reference(marko.inline.InlineElement):
    "Markdown extension for reference."

    pattern = re.compile(r"\[@(.+?)\]")
    parse_children = False

    def __init__(self, match):
        self.reference = match.group(1).strip()


parser = marko.Markdown(renderer=marko.ast_renderer.ASTRenderer)
parser.use("footnote")
parser.use(
    marko.helpers.MarkoExtension(
        elements=[
            marko.ext.gfm.elements.Table,
            marko.ext.gfm.elements.TableRow,
            marko.ext.gfm.elements.TableCell,
        ]
    )
)
parser.use(marko.helpers.MarkoExtension(elements=[Indexed, Reference]))


def check_invalid_characters(name):
    """Raise ValueError if name contains any invalid characters;
    those with special meaning in file system.
    """
    invalids = [os.extsep, os.sep]
    if os.altsep:
        invalids.append(os.altsep)
    for invalid in invalids:
        if invalid in name:
            raise ValueError(f"The name may not contain the character '{invalid}'.")


def test(keep=False):
    import tempfile

    content = "# Very basic Markdown.\n\n**Bold**.\n"
    dirpath = tempfile.mkdtemp()
    for filename in ["text1.md", "text2.md", "text3.md"]:
        with open(os.path.join(dirpath, filename), "w") as outfile:
            outfile.write(content)
    subdirpath = os.path.join(dirpath, "section1")
    os.mkdir(subdirpath)
    for filename in ["text1.md", "text2.md", "text3.md"]:
        with open(os.path.join(subdirpath, filename), "w") as outfile:
            outfile.write(content)

    source = Source(dirpath)
    source.check_integrity()
    section = source["section1"]
    section.copy("section2")
    source.check_integrity()
    section.rename("subsection")
    source.check_integrity()
    section.move_to_section(source["section2"])
    source.check_integrity()
    source["section2"].delete()
    source.check_integrity()
    if not keep:
        shutil.rmtree(dirpath)


if __name__ == "__main__":
    import json

    test()
    source = Source("/home/pekrau/Att konfrontera lejonen")
    with open("config.json") as infile:
        config = json.loads(infile.read())
    source.apply_config(config)
    ic(source.get_config())
    with open("config.json", "w") as outfile:
        outfile.write(json.dumps(source.get_config(), indent=2))
    item = source["subsection/kommentarer2/new text"]
    ic(item, item.parentpath)
