"Utility functions."

import os
import time

import constants
import latex_utf8
import translation


try:
    Tr = translation.Translation(os.path.join(os.path.dirname(__file__),
                                              constants.TRANSLATION_FILE))
except OSError:
    Tr = lambda t: t

def cleanup(value):
    "Convert LaTeX characters to UTF-8, remove newlines and normalize blanks."
    return latex_utf8.from_latex_to_utf8(" ".join(value.split()))

def shortname(name):
    "Return the person name in short form; given names as initials."
    parts = [p.strip() for p in name.split(",")]
    initials = [p.strip()[0] for p in parts.pop().split(" ")]
    parts.append("".join([f"{i}." for i in initials]))
    return ", ".join(parts)

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
