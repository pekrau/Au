"Utility functions."

import os.path

import constants
import latex_utf8
import translator


# A global instance of the language translator.
try:
    path = os.path.join(os.path.dirname(__file__), constants.TRANSLATIONS_FILE)
    Tr = translator.Translator(path)
except OSError:
    Tr = lambda t: t


def cleanup(value):
    "Convert LaTeX characters to UTF-8, remove newlines and normalize blanks."
    return latex_utf8.from_latex_to_utf8(" ".join(value.split()))


def shortname(name):
    "Return the person name in short form; given names as initials."
    parts = [p.strip() for p in name.split(",")]
    if len(parts) == 1:
        return name
    initials = [p.strip()[0] for p in parts.pop().split(" ")]
    parts.append("".join([f"{i}." for i in initials]))
    return ", ".join(parts)


def get_normalized_mark(value):
    "Return a valid tk.Text mark."
    return value.replace(" ", "_").replace(".", "_")


if __name__ == "__main__":
    print(cleanup("Zuberb\xFChler, Klaus"))
    
