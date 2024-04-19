"Utility functions."

from icecream import ic

import datetime
import os.path
import re
import time

import marko
import marko.ast_renderer
import marko.inline
import marko.helpers
import yaml

import constants

FRONTMATTER = re.compile(r"^---([\n\r].*?[\n\r])---[\n\r](.*)$", re.DOTALL)

class ReferenceLink(marko.inline.InlineElement):
    "Link to a reference."

    pattern = re.compile(r"\[@(.+?)\]")
    parse_children = False

    def __init__(self, match):
        self.target = match.group(1).strip()


def get_frontmatter_ast(filepath):
    "Read the file, returning a tuple of the YAML frontmatter and Markdown AST data."
    with open(filepath) as infile:
        content = infile.read()
    match = FRONTMATTER.match(content)
    if match:
        frontmatter = yaml.safe_load(match.group(1))
        content = content[match.start(2):]
    else:
        frontmatter = dict()
    parser = marko.Markdown(renderer=marko.ast_renderer.ASTRenderer,
                            extensions=["footnote"])
    parser.use(marko.helpers.MarkoExtension(elements=[ReferenceLink]))
    return frontmatter, parser.convert(content)

def get_now():
    "Get formatted string for the current local time."
    return time.strftime(constants.TIME_FORMAT, time.localtime())

def get_timestamp(value=None):
    "Get formatted string for the modification timestamp of the given file."
    return time.strftime(constants.TIME_FORMAT,
                         time.localtime(os.path.getmtime(value)))

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
    return (f"{value:.1f}", unit)

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
