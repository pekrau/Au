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
    "Get the size of the text file by counting the characters in the AST."
    with open(absfilepath) as infile:
        ast = get_ast(infile.read())
    return count_characters(ast)

def count_characters(ast):
    "Count the printable characters in the AST. Approximate value only."
    if ast["element"] == "raw_text":
        return len(ast["children"].strip())
    elif ast["element"] == "line_break":
        return 0
    result = 0
    if "children" in ast:
        for child in ast["children"]:
            result += count_characters(child)
    return result

def split_all(filepath):
    "Return list of all components of the given filepath."
    result = []
    while filepath:
        parent, child = os.path.split(filepath)
        result.append(child)
        filepath = parent
    return list(reversed(result))
