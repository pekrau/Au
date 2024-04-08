"Utility functions."

import os.path
import time

import marko
import marko.ast_renderer

import constants


def get_markdown_to_ast(markdown_text):
    "Convert Markdown to AST."
    return marko.Markdown(renderer=marko.ast_renderer.ASTRenderer).convert(markdown_text)
def get_timestamp(value=None):
    """Get formatted string for the given time.
    If a string, then interpret as a filepath and get its modification timestamp.
    If None, current local time.
    """
    if value is None:
        return time.strftime(constants.TIME_FORMAT, time.localtime())
    elif type(value) == str:
        return time.strftime(constants.TIME_FORMAT, time.localtime(os.path.getmtime(value)))
    else:
        raise ValueError("invalid argument")
