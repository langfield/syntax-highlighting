import os
import sys
import types

from pygments import highlight
from pygments.util import ClassNotFound
from pygments.lexers import get_all_lexers
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter


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


ERR_LEXER = ("<b>Error</b>: Selected language not found.<br>"
             "A common source of errors: When you update the add-on Anki keeps your user settings"
             " but an update of the add-on might include a new version of the Pygments library"
             " which sometimes renames languages. This means a setting that used to work no longer"
             " works with newer versions of this add-on.")

ERR_STYLE = ("<b>Error</b>: Selected style not found.<br>"
             "A common source of errors: When you update the add-on Anki keeps your user settings"
             " but an update of the add-on might include a new version of the Pygments library"
             " which sometimes renames languages. This means a setting that used to work no longer"
             " works with newer versions of this add-on.")


def hilcd(ed, code, langAlias, config: types.SimpleNamespace):
    linenos = config.linenos
    centerfragments = config.centerfragments

    noclasses = not config.cssclasses
    if noclasses:
        msg = (
            "The version from 2021-03 only applies the styling with classes and no longer "
            "supports applying inline styling (the old default).\nThe reason is twofold: "
            "It seems as if loading custom css into the editor will soon be officially "
            "supported, see https://github.com/ankitects/anki/pull/1049. This also reduces "
            "the add-on complexity.\nIf you don't like this change you could use the "
            "original Syntax Highlighting add-on.\nTo avoid seeing this info open the "
            "add-on config once and save it."
        )
        print(msg)
        noclasses = False

    try:
        my_lexer = get_lexer_by_name(
            langAlias,
            stripall=not config.remove_leading_spaces_if_possible,
        )
    except ClassNotFound as e:
        print(e)
        print(ERR_LEXER)
        return ""

    try:
        # http://pygments.org/docs/formatters/#HtmlFormatter
        my_formatter = HtmlFormatter(
            # cssclass=css_class,
            font_size=16,
            linenos=linenos,
            lineseparator="<br>",
            nobackground=False,  # True would solve night mode problem without any config (as long as no line numbers are used)
            noclasses=noclasses,
            style=config.style,
            wrapcode=True,
        )
    except ClassNotFound as e:
        print(e)
        print(ERR_STYLE)
        return ""

    pygmntd = highlight(code, my_lexer, my_formatter).rstrip()
    if linenos:
        pretty_code = pygmntd + "<br>"
    else:
        pretty_code = "".join(
            [
                f'<table style="text-align: center;" class="highlighttable"><tbody><tr><td>',
                pygmntd,
                "</td></tr></tbody></table><br>",
            ]
        )

    if centerfragments:
        soup = BeautifulSoup(pretty_code, "html.parser")
        tablestyling = "margin: 0 auto;"
        for t in soup.findAll("table"):
            if t.has_attr("style"):
                t["style"] = tablestyling + t["style"]
            else:
                t["style"] = tablestyling
        pretty_code = str(soup)
    return pretty_code
