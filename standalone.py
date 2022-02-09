def hilcd(ed, code, langAlias):
    global LASTUSED
    linenos = gc("linenos")
    centerfragments = gc("centerfragments")

    noclasses = not gc("cssclasses")
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
        showInfo(msg)
        noclasses = False

    try:
        my_lexer = pyg__get_lexer_by_name(
            langAlias, stripall=not gc("remove leading spaces if possible", True)
        )
    except pyg__ClassNotFound as e:
        print(e)
        print(ERR_LEXER)
        showError(ERR_LEXER, parent=ed.parentWindow)
        return False
    try:
        # http://pygments.org/docs/formatters/#HtmlFormatter
        my_formatter = pyg__HtmlFormatter(
            # cssclass=css_class,
            font_size=16,
            linenos=linenos,
            lineseparator="<br>",
            nobackground=False,  # True would solve night mode problem without any config (as long as no line numbers are used)
            noclasses=noclasses,
            style=gc("style"),
            wrapcode=True,
        )
    except pyg__ClassNotFound as e:
        print(e)
        print(ERR_STYLE)
        showError(ERR_STYLE, parent=ed.parentWindow)
        return False

    pygmntd = pyg__highlight(code, my_lexer, my_formatter).rstrip()
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

    ed.web.eval(f"setFormat('inserthtml', {json.dumps(pretty_code)});")
    LASTUSED = langAlias
