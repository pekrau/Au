"Utility functions."

from icecream import ic

import os
import time

import constants


def get_now():
    "Get ISO formatted string for the current local time."
    return time.strftime(constants.TIME_ISO_FORMAT, time.localtime())

def get_normalized_mark(value):
    "Return a valid tk.Text mark."
    return value.replace(" ", "_").replace(".", "_")

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


if __name__ == "__main__":
    frontmatter, ast = get_frontmatter_ast("test.md")
    ic(frontmatter, ast)
