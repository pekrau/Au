"Utility functions."

from icecream import ic

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

def get_time(value=None):
    """Get formatted string for the given time.
    If a string, then interpret as a filepath and get its modification timestamp.
    If None, current local time.
    """
    if value is None:
        return time.strftime(constants.TIME_FORMAT, time.localtime())
    elif type(value) == str:
        return time.strftime(constants.TIME_FORMAT,
                             time.localtime(os.path.getmtime(value)))
    else:
        raise ValueError("invalid argument")

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
