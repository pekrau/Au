"Constants."

import functools
import os

VERSION = (0, 14, 3)

AU64 = "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAABhGlDQ1BJQ0MgcHJvZmlsZQAAKJF9kT1Iw0AcxV/TSkWqDnaQ4pChOlkQleKoVShChVArtOpgcv2EJg1Jiouj4Fpw8GOx6uDirKuDqyAIfoA4OzgpukiJ/0sKLWI8OO7Hu3uPu3eA0Kwy1QxMAKpmGelkQszmVsXgKwLwYwBxRGRm6nOSlILn+LqHj693MZ7lfe7P0Z8vmAzwicSzTDcs4g3i+Kalc94nDrOynCc+Jx436ILEj1xXXH7jXHJY4JlhI5OeJw4Ti6UuVrqYlQ2VeJo4mlc1yheyLuc5b3FWq3XWvid/YaigrSxzneYIkljEEiSIUFBHBVVYiNGqkWIiTfsJD3/E8UvkUshVASPHAmpQITt+8D/43a1ZnJp0k0IJoOfFtj9GgeAu0GrY9vexbbdOAP8zcKV1/LUmMPNJeqOjRY+AwW3g4rqjKXvA5Q4w/KTLhuxIfppCsQi8n9E35YChW6Bvze2tvY/TByBDXaVugINDYKxE2ese7+7t7u3fM+3+fgBwYnKmw5NibQAAAAZiS0dEAP8A/wD/oL2nkwAAAAlwSFlzAAAuIwAALiMBeKU/dgAAAAd0SU1FB+gEAw45EiZV65kAAAAZdEVYdENvbW1lbnQAQ3JlYXRlZCB3aXRoIEdJTVBXgQ4XAAADoklEQVR42u2aWUiUURTHf5qVLa6kIVZQUBptRLtKYVBhQUFky0NZ2fbQQ1ESREbLQxJCEe0RVIhJRSumJZGV5qRmlla2SZstlo6mUKk5PXz5kN77+c1iOTP3wMcM93/u3Lm/Ofeeew/jYXmKBTc2T9zcFAAFQAFQABQABUABUAAUAAVAAVAAFAAFQAFwP/OypVNlFfSNat+vygSBfi4YAaaHxvzyH7ngEmhuhlMXjPmmXgFLJ684elhbFH3+GsJijPuXZ8HAfi4UAbfyrfO/U+hCS+DHT9h70roBDqVCQ6OLAHhYBk/Kxdq4YZINswRKX7gIgPRsubZ/q1y7dse6LxW/GTyGip/qGtv71tbbAaDKDDsPi7V1i2H8SFg5T6zvOgI1dU4eASadnD57qvY6d7pYr/sOhSWOylv/AYDFAqmX5froP+t/7HC5T1q6E0dA+TtIvSrWtq8Ffx/tfZ8ASFgm9jt+Ht5+6HQBYAzA7QK5NqPVnWBWtNw3574TLoGfDbA/Raz1C4YRYa2Ww1Dw6SH2P5wGjU1OFgElz6GoTKxtXA49vf9u8+0Nm1ZKToVF8PSVk0VApk4Oj54obp8WKe+TlWvn/P8lAPM3SNwnP/mFDxJrI4bAoFCxtvsYfKt3kixQoJP71yyCbl3FWg9vWL9UUkypgfuPOw8A3YrQaZ3cHb9Fe2yxc5kQPcG2vu3VF76YHRQBryvgxMWOoX4wDSo+29b31y+51tQE94odBCCng+/xd4vkWvdu+mlZZhWV2hKzG0Bjo5azO9KOnYEmya8ZoFNI/Wp2XLFGCqD0JeQWdyyALBM8k9QWQvvK+900idtfvIG1Oxy0CV7P0TnOpkDkGOMDZOdDdJxYu5EHwwa3bZelV4B1SRAUCDFTtENXXT0UlsKGJO3WafW5onVRtLYe+k+Wf1j1PQjwNT7AVzMERciP0mUZ0Ktnq528GoIjHR91NQXg17udJVBYIp/8+iXWTb7lhrgqVqy9r4SiJ23bgwIhOcH6CR5IhLg5du4BZzKM3/yM2swpcu1Clrh9RSzMiDA+RnICrJoPXTztAPDuIxw9K3ceGWYbgFHhcm3PKfj0pW27nw+kJMujp8WC/eHSAe3k6eVl5yaYq5ObF8ZASLBtAAaEQEwUZEg217sPxOW0PgFwcBusXgB5xWAqhkfPoH+I9mNEjYFJo61flrqboLuZ+n+AAqAAKAAKgAKgACgACoACoAAoAAqAAqAAuJ/9BkYG9/zutbrRAAAAAElFTkSuQmCC"

DEFAULT_ROOT_GEOMETRY = "1500x400+700+0"

CONFIG_SAVE_DELAY = 2000
AGES_UPDATE_DELAY = 2000

MARKDOWN_EXT = ".md"
CONFIG_FILENAME = "config.json"
ARCHIVE_DIRNAME = "au_archive"
assert os.extsep not in ARCHIVE_DIRNAME
REFERENCES_DIRNAME = "au_references"
assert os.extsep not in REFERENCES_DIRNAME
TRANSLATIONS_FILE = "translations.csv"

TEXT_COLOR = "oldlace"
EDIT_COLOR = "lavenderblush"
MODIFIED_COLOR = "lightpink"

ITEM = "item"
ITEM_PREFIX = "item-"
SECTION = "section"
SECTION_COLOR = "gainsboro"

TIME_ISO_FORMAT = "%Y-%m-%d %H:%M:%S"
EM_DASH = "\u2014"


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

BOLD = "bold"
ITALIC = "italic"
NORMAL = "normal"
UNDERLINE = "underline"
THEMATIC_BREAK = "thematic_break"

FONT = "Arial"
FONT_NORMAL_SIZE = 12
FONT_LARGE_SIZE = FONT_NORMAL_SIZE + 2
FONT_TITLE_SIZE = 28
FONT_NORMAL = (FONT, FONT_NORMAL_SIZE)
FONT_ITALIC = (FONT, FONT_NORMAL_SIZE, ITALIC)
FONT_BOLD = (FONT, FONT_NORMAL_SIZE, BOLD)
FONT_LARGE_BOLD = (FONT, FONT_LARGE_SIZE, BOLD)
FONT_SMALL_SIZE = FONT_NORMAL_SIZE - 2
FONT_SMALL = (FONT, FONT_SMALL_SIZE)

TEXT_PADX = 5
TEXT_SPACING1 = 0
TEXT_SPACING2 = 4
TEXT_SPACING3 = 0

H1 = dict(
    tag="h1",
    font=(FONT, FONT_LARGE_SIZE + 10, BOLD),
    left_margin=40,
    spacing=30,
    klass="mt-5",
)
H2 = dict(
    tag="h2",
    font=(FONT, FONT_LARGE_SIZE + 5, BOLD),
    left_margin=30,
    spacing=20,
    klass="mt-5",
)
H3 = dict(
    tag="h3",
    font=(FONT, FONT_LARGE_SIZE + 3, BOLD),
    left_margin=20,
    spacing=15,
    klass="mt-4",
)
H4 = dict(
    tag="h4",
    font=(FONT, FONT_NORMAL_SIZE, BOLD),
    left_margin=15,
    spacing=10,
    klass="mt-3",
)
H5 = dict(
    tag="h5",
    font=(FONT, FONT_NORMAL_SIZE, BOLD),
    left_margin=10,
    spacing=5,
    klass="mt-2",
)
H6 = dict(tag="h6", font=(FONT, FONT_NORMAL_SIZE), left_margin=10, spacing=5,    klass="mt-2",
)
H_LOOKUP = dict([(1, H1), (2, H2), (3, H3), (4, H4), (5, H5), (6, H6)])
MAX_H_LEVEL = max(H_LOOKUP)

QUOTE = "quote"
QUOTE_LEFT_INDENT = 30
QUOTE_RIGHT_INDENT = 70
QUOTE_SPACING1 = 4
QUOTE_SPACING2 = 4
QUOTE_FONT = "Verdana"

CODE_SPAN = "code_span"
CODE_BLOCK = "code_block"
FENCED_CODE = "fenced_code"
CODE_FONT = "FreeMono"
CODE_INDENT = 30

LIST_PREFIX = "list-"
LIST_ITEM_PREFIX = "list_item-"
LIST_BULLET_PREFIX = "list_bullet-"
LIST_INDENT = 16

LINK = "link"
LINK_PREFIX = "link-"
LINK_COLOR = "blue"
LINK_CURSOR = "hand2"

REFERENCE = "reference"
REFERENCE_PREFIX = "reference-"
REFERENCE_COLOR = "magenta"
REFERENCE_SPACING = 12
REFERENCE_INDENT = 20
REFERENCE_CURSOR = "target"
REFERENCE_MAX_AUTHORS = 5
REFERENCE_LINKS = [
    ("doi", "DOI", "https://doi.org/{value}"),
    ("pmid", "PubMed", "https://pubmed.ncbi.nlm.nih.gov/{value}"),
    ("isbn", "ISBN", "https://isbnsearch.org/isbn/{value}"),
]
ARTICLE = "article"
BOOK = "book"
REFERENCE_TYPES = (ARTICLE, BOOK, LINK)
REFERENCE_GENERAL_KEYS = ("title", "language", "year")
REFERENCE_TYPE_KEYS = {
    ARTICLE: ("journal", "month", "volume", "number", "pages", "issn", "doi", "pmid"),
    BOOK: ("publisher", "pages", "isbn"),
    LINK: ("url", "accessed"),
}
REFERENCE_LANGUAGES = ("en", "sv")

INDEXED = "indexed"
INDEXED_PREFIX = "indexed-"
INDEXED_SPACING = 8
INDEXED_INDENT = 15
INDEXED_CURSOR = "hand2"
INDEXED_FONT = (FONT, FONT_NORMAL_SIZE, BOLD)
INDEXED_XREF_FONT = (FONT, FONT_SMALL_SIZE)

XREF = "xref"
XREF_PREFIX = "xref-"
XREF_COLOR = "seagreen"
XREF_CURSOR = "hand2"

FOOTNOTE_REF = "footnote_ref"
FOOTNOTE_REF_PREFIX = "footnote_ref-"
FOOTNOTE_REF_COLOR = "red"
FOOTNOTE_DEF = "footnote_def"
FOOTNOTE_DEF_PREFIX = "footnote_def-"
FOOTNOTE_DEF_COLOR = "#ffdddd"
FOOTNOTE_MARGIN = 4
FOOTNOTE_CURSOR = "exchange"

HIGHLIGHT = "highlight"
HIGHLIGHT_COLOR = "yellow"

SEARCH = "search"
SEARCH_PREFIX = "search-"
SEARCH_FRAGMENT = 24
SEARCH_INDENT = 10

WRITE_CURSOR = "watch"
