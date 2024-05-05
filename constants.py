"Constants."

import functools
import os

VERSION = (0, 8, 5)

AU64 = "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAABhGlDQ1BJQ0MgcHJvZmlsZQAAKJF9kT1Iw0AcxV/TSkWqDnaQ4pChOlkQleKoVShChVArtOpgcv2EJg1Jiouj4Fpw8GOx6uDirKuDqyAIfoA4OzgpukiJ/0sKLWI8OO7Hu3uPu3eA0Kwy1QxMAKpmGelkQszmVsXgKwLwYwBxRGRm6nOSlILn+LqHj693MZ7lfe7P0Z8vmAzwicSzTDcs4g3i+Kalc94nDrOynCc+Jx436ILEj1xXXH7jXHJY4JlhI5OeJw4Ti6UuVrqYlQ2VeJo4mlc1yheyLuc5b3FWq3XWvid/YaigrSxzneYIkljEEiSIUFBHBVVYiNGqkWIiTfsJD3/E8UvkUshVASPHAmpQITt+8D/43a1ZnJp0k0IJoOfFtj9GgeAu0GrY9vexbbdOAP8zcKV1/LUmMPNJeqOjRY+AwW3g4rqjKXvA5Q4w/KTLhuxIfppCsQi8n9E35YChW6Bvze2tvY/TByBDXaVugINDYKxE2ese7+7t7u3fM+3+fgBwYnKmw5NibQAAAAZiS0dEAP8A/wD/oL2nkwAAAAlwSFlzAAAuIwAALiMBeKU/dgAAAAd0SU1FB+gEAw45EiZV65kAAAAZdEVYdENvbW1lbnQAQ3JlYXRlZCB3aXRoIEdJTVBXgQ4XAAADoklEQVR42u2aWUiUURTHf5qVLa6kIVZQUBptRLtKYVBhQUFky0NZ2fbQQ1ESREbLQxJCEe0RVIhJRSumJZGV5qRmlla2SZstlo6mUKk5PXz5kN77+c1iOTP3wMcM93/u3Lm/Ofeeew/jYXmKBTc2T9zcFAAFQAFQABQABUABUAAUAAVAAVAAFAAFQAFwP/OypVNlFfSNat+vygSBfi4YAaaHxvzyH7ngEmhuhlMXjPmmXgFLJ684elhbFH3+GsJijPuXZ8HAfi4UAbfyrfO/U+hCS+DHT9h70roBDqVCQ6OLAHhYBk/Kxdq4YZINswRKX7gIgPRsubZ/q1y7dse6LxW/GTyGip/qGtv71tbbAaDKDDsPi7V1i2H8SFg5T6zvOgI1dU4eASadnD57qvY6d7pYr/sOhSWOylv/AYDFAqmX5froP+t/7HC5T1q6E0dA+TtIvSrWtq8Ffx/tfZ8ASFgm9jt+Ht5+6HQBYAzA7QK5NqPVnWBWtNw3574TLoGfDbA/Raz1C4YRYa2Ww1Dw6SH2P5wGjU1OFgElz6GoTKxtXA49vf9u8+0Nm1ZKToVF8PSVk0VApk4Oj54obp8WKe+TlWvn/P8lAPM3SNwnP/mFDxJrI4bAoFCxtvsYfKt3kixQoJP71yyCbl3FWg9vWL9UUkypgfuPOw8A3YrQaZ3cHb9Fe2yxc5kQPcG2vu3VF76YHRQBryvgxMWOoX4wDSo+29b31y+51tQE94odBCCng+/xd4vkWvdu+mlZZhWV2hKzG0Bjo5azO9KOnYEmya8ZoFNI/Wp2XLFGCqD0JeQWdyyALBM8k9QWQvvK+900idtfvIG1Oxy0CV7P0TnOpkDkGOMDZOdDdJxYu5EHwwa3bZelV4B1SRAUCDFTtENXXT0UlsKGJO3WafW5onVRtLYe+k+Wf1j1PQjwNT7AVzMERciP0mUZ0Ktnq528GoIjHR91NQXg17udJVBYIp/8+iXWTb7lhrgqVqy9r4SiJ23bgwIhOcH6CR5IhLg5du4BZzKM3/yM2swpcu1Clrh9RSzMiDA+RnICrJoPXTztAPDuIxw9K3ceGWYbgFHhcm3PKfj0pW27nw+kJMujp8WC/eHSAe3k6eVl5yaYq5ObF8ZASLBtAAaEQEwUZEg217sPxOW0PgFwcBusXgB5xWAqhkfPoH+I9mNEjYFJo61flrqboLuZ+n+AAqAAKAAKgAKgACgACoACoAAoAAqAAqAAuJ/9BkYG9/zutbrRAAAAAElFTkSuQmCC"

DEFAULT_ROOT_GEOMETRY = "400x400+700+0"
DEFAULT_TEXT_WIDTH = 80
DEFAULT_TEXT_HEIGHT = 30

CONFIG_FILENAME = "config.json"
ARCHIVE_DIRNAME = "au_archive"
assert os.extsep not in ARCHIVE_DIRNAME # Code relies on this!
TODO_DIRNAME = "au_todo"
assert os.extsep not in TODO_DIRNAME # Code relies on this!
REFERENCES_DIRNAME = "au_references"
assert os.extsep not in REFERENCES_DIRNAME # Code relies on this!

MARKDOWN_EXT = ".md"

TEXT_COLOR = "linen"
MODIFIED_COLOR = "lightpink"

ITEM = "item"
ITEM_PREFIX = "item-"
SECTION = "section"
SECTION_COLOR = "gainsboro"

TIME_ISO_FORMAT = "%Y-%m-%d %H:%M:%S"

@functools.total_ordering
class Status:
    @classmethod
    def lookup(cls, name, default=None):
        return STATUS_LOOKUP.get(name) or default
    def __init__(self, name, ordinal):
        self.name = name
        self.ordinal = ordinal
    def __str__(self):
        return self.name.capitalize()
    def __repr__(self):
        return self.name
    def __eq__(self, other):
        return self.name == other.name
    def __ne__(self, other):
        return other is None or self.name != other.name
    def __lt__(self, other):
        return self.ordinal < other.ordinal

STARTED = Status("started", 0)
OUTLINE = Status("outline", 1)
INCOMPLETE = Status("incomplete", 2)
DRAFT = Status("draft", 3)
WRITTEN = Status("written", 4)
REVISED = Status("revised", 5)
DONE = Status("done", 6)
PROOFS = Status("proofs", 7)
FINAL = Status("final", 8)
STATUSES = (STARTED, OUTLINE, INCOMPLETE, DRAFT, WRITTEN, REVISED, DONE, PROOFS, FINAL)
STATUS_LOOKUP = dict([(s.name, s) for s in STATUSES])

PANE_MINSIZE = 300
TREEVIEW_PANE_WIDTH = 400
TEXTS_PANE_WIDTH = 800
META_PANE_WIDTH = 400

BOLD = "bold"
ITALIC = "italic"
THEMATIC_BREAK = "thematic_break"

FONT_NORMAL_FAMILY = "Arial"
FONT_NORMAL_SIZE = 12
FONT_LARGE_SIZE = FONT_NORMAL_SIZE + 2
FONT_NORMAL = (FONT_NORMAL_FAMILY, FONT_NORMAL_SIZE)
FONT_ITALIC = (FONT_NORMAL_FAMILY, FONT_NORMAL_SIZE, ITALIC)
FONT_BOLD = (FONT_NORMAL_FAMILY, FONT_NORMAL_SIZE, BOLD)
FONT_LARGE_BOLD = (FONT_NORMAL_FAMILY, FONT_LARGE_SIZE, BOLD)
FONT_SMALL_SIZE = FONT_NORMAL_SIZE - 2
FONT_SMALL = (FONT_NORMAL_FAMILY, FONT_SMALL_SIZE)

TEXT_PADX = 5
TEXT_SPACING1 = 0
TEXT_SPACING2 = 4
TEXT_SPACING3 = 0

TITLE = "title"
TITLE_FONT = (FONT_NORMAL_FAMILY, FONT_LARGE_SIZE + 8, BOLD)
TITLE_LEFT_MARGIN = 40
H1 = "h1"
H1_FONT = (FONT_NORMAL_FAMILY, FONT_LARGE_SIZE + 6, BOLD)
H2 = "h2"
H2_FONT = (FONT_NORMAL_FAMILY, FONT_LARGE_SIZE + 3, BOLD)
H3 = "h3"
H3_FONT = (FONT_NORMAL_FAMILY, FONT_LARGE_SIZE, BOLD)
H4 = "h4"
H4_FONT = (FONT_NORMAL_FAMILY, FONT_NORMAL_SIZE, BOLD)
H = dict([(1, H1), (2, H2), (3, H3), (4, H4)])
H_LEFT_MARGIN = 20

QUOTE = "quote"
QUOTE_LEFT_INDENT = 30
QUOTE_RIGHT_INDENT = 70
QUOTE_SPACING1 = 4
QUOTE_SPACING2 = 4
QUOTE_FONT = "Verdana"

LIST = "list"
LIST_BULLET = "list_bullet"
LIST_PREFIX = "list-"
LIST_BULLETS = ["\u2022", "\u25e6", "\u2043", "\u2043"]
LIST_MAX_DEPTH = len(LIST_BULLETS)
LIST_INDENT = 20

INDEXED = "indexed"
INDEXED_PREFIX = "indexed-"
INDEXED_SPACING = 8
INDEXED_INDENT = 15

REFERENCE = "reference"
REFERENCE_PREFIX = "reference-"
REFERENCE_COLOR = "magenta"

LINK = "link"
LINK_PREFIX = "link-"
LINK_COLOR = "blue"

FOOTNOTE_REF = "footnote_ref"
FOOTNOTE_REF_PREFIX = "footnote_ref-"
FOOTNOTE_REF_COLOR = "red"
FOOTNOTE_DEF = "footnote_def"
FOOTNOTE_DEF_PREFIX = "footnote_def-"
FOOTNOTE_DEF_COLOR = "#ffdddd"
FOOTNOTE_MARGIN = 4

HIGHLIGHT = "highlight"
HIGHLIGHT_COLOR = "yellow"

SEARCH = "search"
SEARCH_PREFIX = "search-"
SEARCH_FRAGMENT = 24
SEARCH_INDENT = 10

CONFIG_UPDATE_DELAY = 1000
AGES_UPDATE_DELAY = 2000

DOCX_PAGEBREAK_LEVEL = 1
