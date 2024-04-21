"Constants."

import functools
import string

AU64 = "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAABhGlDQ1BJQ0MgcHJvZmlsZQAAKJF9kT1Iw0AcxV/TSkWqDnaQ4pChOlkQleKoVShChVArtOpgcv2EJg1Jiouj4Fpw8GOx6uDirKuDqyAIfoA4OzgpukiJ/0sKLWI8OO7Hu3uPu3eA0Kwy1QxMAKpmGelkQszmVsXgKwLwYwBxRGRm6nOSlILn+LqHj693MZ7lfe7P0Z8vmAzwicSzTDcs4g3i+Kalc94nDrOynCc+Jx436ILEj1xXXH7jXHJY4JlhI5OeJw4Ti6UuVrqYlQ2VeJo4mlc1yheyLuc5b3FWq3XWvid/YaigrSxzneYIkljEEiSIUFBHBVVYiNGqkWIiTfsJD3/E8UvkUshVASPHAmpQITt+8D/43a1ZnJp0k0IJoOfFtj9GgeAu0GrY9vexbbdOAP8zcKV1/LUmMPNJeqOjRY+AwW3g4rqjKXvA5Q4w/KTLhuxIfppCsQi8n9E35YChW6Bvze2tvY/TByBDXaVugINDYKxE2ese7+7t7u3fM+3+fgBwYnKmw5NibQAAAAZiS0dEAP8A/wD/oL2nkwAAAAlwSFlzAAAuIwAALiMBeKU/dgAAAAd0SU1FB+gEAw45EiZV65kAAAAZdEVYdENvbW1lbnQAQ3JlYXRlZCB3aXRoIEdJTVBXgQ4XAAADoklEQVR42u2aWUiUURTHf5qVLa6kIVZQUBptRLtKYVBhQUFky0NZ2fbQQ1ESREbLQxJCEe0RVIhJRSumJZGV5qRmlla2SZstlo6mUKk5PXz5kN77+c1iOTP3wMcM93/u3Lm/Ofeeew/jYXmKBTc2T9zcFAAFQAFQABQABUABUAAUAAVAAVAAFAAFQAFwP/OypVNlFfSNat+vygSBfi4YAaaHxvzyH7ngEmhuhlMXjPmmXgFLJ684elhbFH3+GsJijPuXZ8HAfi4UAbfyrfO/U+hCS+DHT9h70roBDqVCQ6OLAHhYBk/Kxdq4YZINswRKX7gIgPRsubZ/q1y7dse6LxW/GTyGip/qGtv71tbbAaDKDDsPi7V1i2H8SFg5T6zvOgI1dU4eASadnD57qvY6d7pYr/sOhSWOylv/AYDFAqmX5froP+t/7HC5T1q6E0dA+TtIvSrWtq8Ffx/tfZ8ASFgm9jt+Ht5+6HQBYAzA7QK5NqPVnWBWtNw3574TLoGfDbA/Raz1C4YRYa2Ww1Dw6SH2P5wGjU1OFgElz6GoTKxtXA49vf9u8+0Nm1ZKToVF8PSVk0VApk4Oj54obp8WKe+TlWvn/P8lAPM3SNwnP/mFDxJrI4bAoFCxtvsYfKt3kixQoJP71yyCbl3FWg9vWL9UUkypgfuPOw8A3YrQaZ3cHb9Fe2yxc5kQPcG2vu3VF76YHRQBryvgxMWOoX4wDSo+29b31y+51tQE94odBCCng+/xd4vkWvdu+mlZZhWV2hKzG0Bjo5azO9KOnYEmya8ZoFNI/Wp2XLFGCqD0JeQWdyyALBM8k9QWQvvK+900idtfvIG1Oxy0CV7P0TnOpkDkGOMDZOdDdJxYu5EHwwa3bZelV4B1SRAUCDFTtENXXT0UlsKGJO3WafW5onVRtLYe+k+Wf1j1PQjwNT7AVzMERciP0mUZ0Ktnq528GoIjHR91NQXg17udJVBYIp/8+iXWTb7lhrgqVqy9r4SiJ23bgwIhOcH6CR5IhLg5du4BZzKM3/yM2swpcu1Clrh9RSzMiDA+RnICrJoPXTztAPDuIxw9K3ceGWYbgFHhcm3PKfj0pW27nw+kJMujp8WC/eHSAe3k6eVl5yaYq5ObF8ZASLBtAAaEQEwUZEg217sPxOW0PgFwcBusXgB5xWAqhkfPoH+I9mNEjYFJo61flrqboLuZ+n+AAqAAKAAKgAKgACgACoACoAAoAAqAAqAAuJ/9BkYG9/zutbrRAAAAAElFTkSuQmCC"

DEFAULT_ROOT_GEOMETRY = "400x400+700+0"
DEFAULT_TEXT_WIDTH = 80
DEFAULT_TEXT_HEIGHT = 30

CONFIGURATION_FILENAME = "configuration.json"
HELP_FILENAME = "help.md"
ARCHIVE_DIRNAME = "au_archive"
REFERENCES_DIRNAME = "au_references"

@functools.total_ordering
class Status:
    @classmethod
    def lookup(cls, name):
        return STATUS_LOOKUP.get(name)
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
QUOTE = "quote"

INDEXED = "indexed"

REFERENCE = "reference"
REFERENCE_COLOR = "magenta"

LINK = "link"
LINK_PREFIX = "link-"
LINK_COLOR = "blue"

FOOTNOTE = "[footnote]"
FOOTNOTE_REF = "footnote_ref"
FOOTNOTE_REF_COLOR = "red"
FOOTNOTE_DEF = "footnote_def"
FOOTNOTE_DEF_COLOR = "linen"
FOOTNOTE_REF_PREFIX = "footnote_ref-"
FOOTNOTE_DEF_PREFIX = "footnote_def-"
FOOTNOTE_DEF_MARGIN = 5

FONT_FAMILY_NORMAL = "Arial"
FONT_NORMAL_SIZE = 12
FONT_LARGE_SIZE = 14
FONT_NORMAL = (FONT_FAMILY_NORMAL, FONT_NORMAL_SIZE)
FONT_ITALIC = (FONT_FAMILY_NORMAL, FONT_NORMAL_SIZE, "italic")
FONT_BOLD = (FONT_FAMILY_NORMAL, FONT_NORMAL_SIZE, "bold")
FONT_LARGE_BOLD = (FONT_FAMILY_NORMAL, FONT_LARGE_SIZE, "bold")

MODIFIED_COLOR = "lightpink"
SECTION_COLOR = "gainsboro"

QUOTE_LEFT_INDENT = 30
QUOTE_RIGHT_INDENT = 70
FONT_FAMILY_QUOTE = "Verdana"

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# Add Return, Backspace, Delete.
AFFECTS_CHARACTER_COUNT = frozenset(string.printable + "\r" + "\x08" + "\x7f")

DOCX_PAGEBREAK_LEVEL = 1
