"Utility functions."

from icecream import ic

import collections
import datetime
import os
import re
import time

import marko
import marko.ast_renderer
import marko.inline
import marko.helpers
import marko.ext.gfm
import yaml

import constants

FRONTMATTER = re.compile(r"^---([\n\r].*?[\n\r])---[\n\r](.*)$", re.DOTALL)

Parsed = collections.namedtuple("Parsed", ["frontmatter", "ast"])


class Indexed(marko.inline.InlineElement):
    "Indexed term."

    pattern = re.compile(r"\[#(.+?)\]")
    parse_children = False

    def __init__(self, match):
        self.target = match.group(1).strip()


class Reference(marko.inline.InlineElement):
    "Source reference."

    pattern = re.compile(r"\[@(.+?)\]")
    parse_children = False

    def __init__(self, match):
        self.target = match.group(1).strip()


def parse(filepath):
    """Read and parse the file, returning a named tuple containing 
    the YAML frontmatter and Markdown AST data.
    """
    with open(filepath) as infile:
        content = infile.read()
    match = FRONTMATTER.match(content)
    if match:
        frontmatter = yaml.safe_load(match.group(1))
        content = content[match.start(2):]
    else:
        frontmatter = dict()
    parser = marko.Markdown(renderer=marko.ast_renderer.ASTRenderer)
    parser.use("footnote")
    parser.use(marko.helpers.MarkoExtension(elements=[
        marko.ext.gfm.elements.Table,
        marko.ext.gfm.elements.TableRow,
        marko.ext.gfm.elements.TableCell
    ]))
    parser.use(marko.helpers.MarkoExtension(elements=[Indexed, Reference]))
    return Parsed(frontmatter, parser.convert(content))

def get_now():
    "Get formatted string for the current local time."
    return time.strftime(constants.TIME_FORMAT, time.localtime())

def get_age(filepath):
    "Get the age of the file, as a tuple (value, unit)."
    now = datetime.datetime.today()
    modified = datetime.datetime.fromtimestamp(os.path.getmtime(filepath))
    age = now - modified
    if age.days >= 365.25:
        value = age.days / 365.25
        unit = "years"
    elif age.days >= 30.5:
        value = age.days / 30.5
        unit = "mnths"
    elif age.days >= 1:
        value = age.days + age.seconds / 86400.0
        unit = "days"
    elif age.seconds >= 3600.0:
        value = age.seconds / 3600.0
        unit = "hours"
    elif age.seconds >= 60.0:
        value = age.seconds / 60.0
        unit= "mins"
    else:
        value = age.seconds + age.microseconds / 1000000.0
        unit = "secs"
    return (f"{value:.0f}", unit)

def get_size(absfilepath):
    "Get the size of the text file. Approximate only; Markdown not taken into account."
    size = os.path.getsize(absfilepath)
    if abs(size) < 1024:
        return f"{size} B"
    size /= 1024.0
    for unit in ("K", "M", "G", "T", "P", "E", "Z"):
        if abs(size) < 1024.0:
            return f"{size:3.1f} {unit}B"
        size /= 1024.0
    return f"{size:.1f} YB"    

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

def split_all(filepath):
    "Return list of all components of the given filepath."
    result = []
    while filepath:
        parent, child = os.path.split(filepath)
        result.append(child)
        filepath = parent
    return list(reversed(result))


if __name__ == "__main__":
    frontmatter, ast = get_frontmatter_ast("test.md")
    ic(frontmatter, ast)
