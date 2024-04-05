class InternalLink(marko.inline.InlineElement):
    "Link to another note."
    pattern = re.compile(r"(?<!!)\[\[(.+?)(?:\|(.+?))?\]\]")
    parse_children = False

    def __init__(self, match):
        self.target = match.group(1).strip()
        if match.group(2):
            self.description = match.group(2).strip()
        else:
            self.description = None

class InternalLinkRenderer:
    def render_internal_link(self, element):
        try:
            note = VAULT.get_note(element.target)
        except KeyError:
            return str(tags.span(element.description or element.target,
                                 cls="text-danger"))
        else:
            if element.description:
                return str(tags.a(element.description,
                                  href=note.url,
                                  title=element.target))
            else:
                return str(tags.a(element.target, href=note.url))


class EmbedLink(marko.inline.InlineElement):
    "Embed the contents of another file."
    pattern = re.compile(r"\!\[\[(.+?)(?:\|(.+?))?\]\]")
    parse_children = False

    def __init__(self, match):
        self.target = match.group(1).strip()
        if match.group(2):
            self.data = match.group(2).strip()
        else:
            self.data = None

class EmbedLinkRenderer:
    def render_embed_link(self, element):
        try:
            note = VAULT.get_note(element.target)
        except KeyError:
            if element.target in VAULT.files_lookup:
                ext = os.path.splitext(element.target)[1]
                if ext in IMAGE_FILES:
                    url = VAULT.get_file_url(element.target)
                    return str(tags.img(src=url_escape(url)))
                else:
                    url = VAULT.get_file_url(element.target)
                    return str(tags.a(element.target, href=url_escape(url)))
            return str(tags.span(element.target, cls="text-danger"))
        else:
            parser = get_markdown_to_html()
            return str(dominate.util.raw(parser.convert(note.md)))

class BareUrl(marko.inline.InlineElement):
    "A bare URL in the note text converted automatically to a link."
    pattern = re.compile(r"\b(https?://\S+)")
    parse_children = False

    def __init__(self, match):
        self.url = match.group(1)

class BareUrlRenderer:
    def render_bare_url(self, element):
        return str(tags.a(url_escape(element.url),
                          tags.span(cls="bi-box-arrow-up-right"),
                          href=url_escape(element.url),
                          target="_blank"))

class BareEmail(marko.inline.InlineElement):
    "A bare email address in the note text converted automatically to a link."
    pattern = re.compile(r"\b(mailto:\S+?@\S+)")
    parse_children = False

    def __init__(self, match):
        self.email = match.group(1)

class BareEmailRenderer:
    def render_bare_email(self, element):
        return str(tags.a(url_escape(element.email),
                          tags.span(cls="bi-box-arrow-up-right"),
                          href=url_escape(element.email),
                          target="_blank"))

class Hashtag(marko.inline.InlineElement):
    "A hashtag in a note."
    pattern = re.compile(r"#([a-z0-9_-]+)")
    parse_children = False

    def __init__(self, match):
        self.hashtag = match.group(1)

class HashtagRenderer:
    def render_hashtag(self, element):
        url = f"{VAULT.settings['URL_BASE']}_hashtag/{element.hashtag}.html"
        return str(tags.a("#" + element.hashtag, href=url_escape(url)))

class HTMLRenderer(marko.html_renderer.HTMLRenderer):
    "Modify output for Bootstrap and other changes."

    def render_link(self, element):
        "Open new tab for external links."
        title = url_escape(element.title) if element.title else ""
        return str(tags.a(self.render_children(element),
                          tags.span(cls="bi-box-arrow-up-right"),
                          href=url_escape(element.dest),
                          title=title,
                          target="_blank"))

    def render_quote(self, element):
        "Add blockquote output class for Bootstrap."
        return '<blockquote class="blockquote border-start border-4 ms-2 ps-4">\n{}</blockquote>\n'.format(
            self.render_children(element)
        )

class HtmlExtensions:
    elements = [InternalLink, EmbedLink, BareUrl, BareEmail, Hashtag]
    renderer_mixins = [
        InternalLinkRenderer,
        EmbedLinkRenderer,
        BareUrlRenderer,
        BareEmailRenderer,
        HashtagRenderer
    ]

def get_markdown_to_html():
    "Get a new instance of the Markdown-to-HTML converter."
    return marko.Markdown(extensions=[HtmlExtensions], renderer=HTMLRenderer)

class AstExtensions:
    elements = [InternalLink, EmbedLink, BareUrl, BareEmail, Hashtag]

def get_markdown_to_json():
    "Get a new instance of the Markdown-to-JSON converter."
    return marko.Markdown(extensions=[AstExtensions], 
                          renderer=marko.ast_renderer.ASTRenderer)
