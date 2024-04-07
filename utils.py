"Utility functions."

import time

import marko
import marko.ast_renderer

import constants


def get_markdown_to_ast(markdown_text):
    "Convert Markdown to AST."
    return marko.Markdown(renderer=marko.ast_renderer.ASTRenderer).convert(markdown_text)
def get_timestamp(timevalue=None):
    "Get formatted string for the given time; if None, current local time."
    return time.strftime(constants.TIME_FORMAT, timevalue or time.localtime())
