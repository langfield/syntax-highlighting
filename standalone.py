"""A standalone module for generating syntax highlighted code blocks in HTML."""
import types

import bs4
from pygments import highlight
from pygments.util import ClassNotFound
from pygments.lexers import get_all_lexers
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter # pylint: disable=no-name-in-module


# This code sets a correspondence between:
#  The "language names": long, descriptive names we want
#                        to show the user AND
#  The "language aliases": short, cryptic names for internal
#                          use by HtmlFormatter
# get_all_lexers is a generator that returns name, aliases, filenames, mimetypes
# since pygments 2.8 from 2021-02 for some lexers the tuple aliases is empty
# so the old code fails:
#   LANG_MAP = {lex[0]: lex[1][0] for lex in get_all_lexers()}
LANG_MAP = {}
for lex in get_all_lexers():
    try:
        LANG_MAP[lex[0]] = lex[1][0]
    except:
        pass
        # for 2.8.1 affected lexers are:
        # - JsonBareObject but changelog for 2.7.3 says "Deprecated JsonBareObjectLexer,
        #   which is now identical to JsonLexer (#1600)"
        # - "Raw token data" no longer has the "raw" alias - see
        #   https://github.com/pygments/pygments/commit/a169fef00bb998d27bbbe57642a367cb951b60a4
        #   the comment was "was broken until 2.7.4, so it seems pretty much unused"


def hilcd(code: str, language_alias: str, config: types.SimpleNamespace) -> str:
    """Highlight a code block."""
    # Get the pygments lexer.
    lexer = get_lexer_by_name(
        language_alias,
        stripall=not config.remove_leading_spaces_if_possible,
    )

    # http://pygments.org/docs/formatters/#HtmlFormatter
    # Setting ``nobackground=True`` would solve night mode problem without
    # any config (as long as no line numbers are used).
    formatter = HtmlFormatter(
        # cssclass=css_class,
        font_size=16,
        linenos=config.linenos,
        lineseparator="<br>",
        nobackground=False,
        noclasses=False,
        style=config.style,
        wrapcode=True,
    )

    # Syntax-highlight the code.
    pygmntd = highlight(code, lexer, formatter).rstrip()
    if config.linenos:
        pretty_code = pygmntd + "<br>"
    else:
        pretty_code = "".join(
            [
                '<table style="text-align: center;" class="highlighttable"><tbody><tr><td>',
                pygmntd,
                "</td></tr></tbody></table><br>",
            ]
        )

    # Optionally center the code block in the Anki note field.
    if config.centerfragments:
        soup = bs4.BeautifulSoup(pretty_code, "html.parser")
        tablestyling = "margin: 0 auto;"
        for t in soup.findAll("table"):
            if t.has_attr("style"):
                t["style"] = tablestyling + t["style"]
            else:
                t["style"] = tablestyling
        pretty_code = str(soup)

    return pretty_code
