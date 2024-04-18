"Utility functions."

from icecream import ic

import datetime
import os.path
import time

import marko
import marko.ast_renderer

import constants


def get_ast(markdown):
    "Convert Markdown text to AST."
    parser = marko.Markdown(renderer=marko.ast_renderer.ASTRenderer,
                            extensions=["footnote"])
    return parser.convert(markdown)

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
        unit = "months"
    elif age.days >= 1:
        value = age.days + age.seconds / 86400.0
        unit = "days"
    elif age.seconds >= 86400.0:
        value = age.seconds / 86400.0
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
    import os
    for filepath in os.listdir("."):
        print(filepath,
              get_age(filepath),
              datetime.datetime.fromtimestamp(os.path.getmtime(filepath)))
