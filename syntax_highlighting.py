import json
import os
import sys
import re
import shutil

from bs4 import BeautifulSoup

import aqt
from aqt.qt import *
from .config import anki_point_version
if anki_point_version >= 24:
    from aqt.gui_hooks import (
        editor_will_load_note,
        webview_will_set_content,
    )
from aqt import mw
from aqt.editor import Editor
from aqt.utils import showWarning, showInfo
from anki import version as anki_version
from anki.hooks import addHook, wrap

from .config import gc
from .fuzzy_panel import FilterDialog
from .pygments_helper import (
    LANG_MAP,
    pyg__highlight,
    pyg__get_lexer_by_name,
    pyg__HtmlFormatter,
    pyg__ClassNotFound,
)
from .settings import MyConfigWindow
from .supplementary import wrap_in_tags


############################################
########## gui config and auto loading #####

def set_some_paths():
    global addon_path
    global addonfoldername
    global addonname
    global css_templates_folder
    global mediafolder
    global css_file_in_media
    addon_path = os.path.dirname(__file__)
    addonfoldername = os.path.basename(addon_path)
    addonname = mw.addonManager.addonName(addonfoldername)
    css_templates_folder = os.path.join(addon_path, "css")
    mediafolder = os.path.join(mw.pm.profileFolder(), "collection.media")
    css_file_in_media = os.path.join(mediafolder, "_styles_for_syntax_highlighting.css")
addHook("profileLoaded", set_some_paths)


insertscript = """<script>
function MyInsertHtml(content) {
    var s = window.getSelection();
    var r = s.getRangeAt(0);
    r.collapse(true);
    var mydiv = document.createElement("div");
    mydiv.innerHTML = content;
    r.insertNode(mydiv);
    // Move the caret
    r.setStartAfter(mydiv);
    r.collapse(true);
    s.removeAllRanges();
    s.addRange(r);
}
</script>
"""

# only for <41:
def profileLoaded():
    editor_style = ""
    if os.path.isfile(css_file_in_media):
        with open(css_file_in_media, "r") as css_file:
            css = css_file.read()
            editor_style = "<style>\n{}\n</style>".format(css.replace("%", "%%"))
    aqt.editor._html = editor_style + insertscript + aqt.editor._html


# for 42-49:
# https://github.com/ijgnd/anki__editor__apply__font_color__background_color__custom_class__custom_style/commit/8cfea36d0077e33c31045b7f64dee5eeeaca86a6
def append_css_to_Editor__42_49(js, note, editor) -> str:
    newjs = ""
    if os.path.isfile(css_file_in_media):
        with open(css_file_in_media, "r") as css_file:
            css = css_file.read()
            newjs = """
var userStyle = document.createElement("style");
userStyle.rel = "stylesheet";
userStyle.textContent = `USER_STYLE`;
userStyle.id = "syntax_highlighting_fork";
forEditorField([], (field) => {
    var sr = field.editingArea.shadowRoot;
    var syntax_highlighting_fork = sr.getElementById("syntax_highlighting_fork");
    if (syntax_highlighting_fork) {
        syntax_highlighting_fork.parentElement.replaceChild(userStyle, syntax_highlighting_fork)
    }
    else {
        sr.insertBefore(userStyle.cloneNode(true), field.editingArea.editable)
    }
});
        """.replace("USER_STYLE", css)
    return js + newjs


if anki_point_version >= 50:
    # this (and web/shf_injector.js) is taken from kleinerpirat's CSS Injector Version 2022-01-20
    # it has this copyright notice on top:
    #     inspired by Henrik Giesel: https://forums.ankiweb.net/t/access-to-dom-element-in-editorfield/8782/8
    #     published for https://forums.ankiweb.net/t/change-default-html-css-template-in-editing-mode/9902
    #     2021 - Matthias Metelka @kleinerpirat
    mw.addonManager.setWebExports(__name__, r"web[/\\]shf_injector.js") 
    def append_webcontent(webcontent, context):
        if isinstance(context, Editor):
            addon_package = context.mw.addonManager.addonFromModule(__name__)
            base_path = f"/_addons/{addon_package}"
            rel_path = f"{base_path}/web/shf_injector.js"
            webcontent.js.append(rel_path)

    def append_css_to_Editor__50(js, note, editor) -> str:
        path = "_styles_for_syntax_highlighting.css"
        return js + f"shf_StyleInjector.inject('{path}', {note.mid});"


if anki_point_version < 41:
    addHook("profileLoaded", profileLoaded)
elif anki_point_version <= 49:
    editor_will_load_note.append(append_css_to_Editor__42_49)
else:
    webview_will_set_content.append(append_webcontent)
    editor_will_load_note.append(append_css_to_Editor__50)







def update_templates(templatenames):
    for m in mw.col.models.all():
        if m['name'] in templatenames:
            # https://github.com/trgkanki/cloze_hide_all/issues/43
            lines = [
                """@import url("_styles_for_syntax_highlighting.css");""",
                """@import url(_styles_for_syntax_highlighting.css);""",
            ]
            for l in lines:
                if l in m['css']:
                    break
            else:
                model = mw.col.models.get(m['id'])
                model['css'] = l + "\n\n" + model['css']
                mw.col.models.save(model)


def css_for_style(style):
    template_file = os.path.join(css_templates_folder, style + ".css")
    with open(template_file) as f:
        css = f.read()
    font = gc("font", "Droid Sans Mono")
    css = css % (font, font, font)
    if gc('centerfragments'):
        css += """\ntable.highlighttable("margin: 0 auto;")\n"""
    return css


def update_cssfile_in_mediafolder(style):
    css = css_for_style(style)
    with open(css_file_in_media, "w") as f:
        f.write(css)


def onMySettings():
    dialog = MyConfigWindow(mw, mw.addonManager.getConfig(__name__))
    dialog.activateWindow()
    dialog.raise_()
    if dialog.exec():
        mw.addonManager.writeConfig(__name__, dialog.config)
        mw.progress.start(immediate=True)
        if hasattr(dialog, "templates_to_update"):
            update_templates(dialog.templates_to_update)
        update_cssfile_in_mediafolder(dialog.config["style"])
        mw.progress.finish()
        showInfo("You need to restart Anki so that all changes take effect.")
mw.addonManager.setConfigAction(__name__, onMySettings)


#######END gui config and auto loading #####
############################################


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

LASTUSED = ""


def showError(msg, parent):
    showWarning(msg, title="Code Formatter Error", parent=parent)


def get_deck_name(editor):
    if isinstance(editor.parentWindow, aqt.addcards.AddCards):
        return editor.parentWindow.deckChooser.deckName()
    elif isinstance(editor.parentWindow, (aqt.browser.Browser, aqt.editcurrent.EditCurrent)):
        return mw.col.decks.name(editor.card.did)
    else:
        return None  # Error


def get_default_lang(editor):
    lang = gc('defaultlang')
    if gc('defaultlangperdeck'):
        deck_name = get_deck_name(editor)
        if deck_name and deck_name in gc('deckdefaultlang'):
            lang = gc('deckdefaultlang')[deck_name]
    return lang


def hilcd(ed, code, langAlias):
    global LASTUSED
    linenos = gc('linenos')
    centerfragments = gc('centerfragments')
    
    noclasses = not gc('cssclasses')
    if noclasses:
        msg = ("The version from 2021-03 only applies the styling with classes and no longer "
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
        my_lexer = pyg__get_lexer_by_name(langAlias, stripall=not gc("remove leading spaces if possible", True))
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
            wrapcode=True)
    except pyg__ClassNotFound as e:
        print(e)
        print(ERR_STYLE)
        showError(ERR_STYLE, parent=ed.parentWindow)
        return False

    pygmntd = pyg__highlight(code, my_lexer, my_formatter).rstrip()
    if linenos:
        pretty_code = pygmntd + "<br>"
    else:
        pretty_code = "".join([f'<table style="text-align: center;" class="highlighttable"><tbody><tr><td>',
                                pygmntd,
                                "</td></tr></tbody></table><br>"])

    if centerfragments:
        soup = BeautifulSoup(pretty_code, 'html.parser')
        tablestyling = "margin: 0 auto;"
        for t in soup.findAll("table"):
            if t.has_attr('style'):
                t['style'] = tablestyling + t['style']
            else:
                t['style'] = tablestyling
        pretty_code = str(soup)

    ed.web.eval(f"setFormat('inserthtml', {json.dumps(pretty_code)});")
    LASTUSED = langAlias


basic_stylesheet = """
QMenu::item {
    padding-top: 16px;
    padding-bottom: 16px;
    padding-right: 75px;
    padding-left: 20px;
    font-size: 15px;
}
QMenu::item:selected {
    background-color: #fd4332;
}
"""


class keyFilter(QObject):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Space:
                self.parent.alternative_keys(self.parent, Qt.Key.Key_Return)
                return True
            elif event.key() == Qt.Key.Key_T:
                self.parent.alternative_keys(self.parent, Qt.Key.Key_Left)
                return True
            elif event.key() == Qt.Key.Key_B:
                self.parent.alternative_keys(self.parent, Qt.Key.Key_Down)
                return True
            elif event.key() == Qt.Key.Key_G:
                self.parent.alternative_keys(self.parent, Qt.Key.Key_Up)
                return True
            # elif event.key() == :
            #     self.parent.alternative_keys(self.parent, Qt.Key.Key_Right)
            #     return True
        return False


def alternative_keys(self, key):
    # https://stackoverflow.com/questions/56014149/mimic-a-returnpressed-signal-on-qlineedit
    keyEvent = QKeyEvent(QEvent.KeyPress, key, Qt.KeyboardModifier.NoModifier)
    QCoreApplication.postEvent(self, keyEvent)


def onAll(editor, code):
    d = FilterDialog(editor.parentWindow, LANG_MAP)
    if d.exec():
        hilcd(editor, code, d.selvalue)


def illegal_info(val):
    msg = ('Illegal value ("{}") in the config of the add-on {}.\n'
           "A common source of errors: When you update the add-on Anki keeps your "
           "user settings but an update of the add-on might include a new version of "
           "the Pygments library which sometimes renames languages. This means a "
           "setting that used to work no longer works with newer versions of this "
           "add-on.".format(val, addonname))
    showInfo(msg)


def remove_leading_spaces(code):
    #https://github.com/hakakou/syntax-highlighting/commit/f5678c0e7dfeb926a5d7f0b780d8dce6ffeaa9d9
    
    # Search in each line for the first non-whitespace character,
    # and calculate minimum padding shared between all lines.
    lines = code.splitlines()
    starting_space = sys.maxsize

    for l in lines:
        # only interested in non-empty lines
        if len(l.strip()) > 0:
            # get the index of the first non whitespace character
            s = len(l) - len(l.lstrip())
            # is it smaller than anything found?
            if s < starting_space:
                starting_space = s

    # if we found a minimum number of chars we can strip off each line, do it.
    if (starting_space < sys.maxsize):
        code = '';    
        for l in lines:
            code = code + l[starting_space:] + '\n'
    return code



'''
Notes about wrapping with pre or code

pre is supposed to be "preformatted text which is to be presented exactly as written 
in the HTML file.", https://developer.mozilla.org/en-US/docs/Web/HTML/Element/pre, 


there are some differences: pre is a block element, see https://www.w3schools.com/html/html_blocks.asp
so code is an inline element, then I could use the "Custom Styles" add-on,
https://ankiweb.net/shared/info/1899278645 to apply the code tag?


### "Mini Format Pack supplementary" approach, https://ankiweb.net/shared/info/476705431?
# wrap_in_tags(editor, code, "pre")) 
# wrap_in_tags(editor, code, "code"))
# My custom version depends on deleting the selection first



### combine execCommands delete and insertHTML
# I remove the selection when opening the helper menu
#     editor.web.evalWithCallback("document.execCommand('delete');", lambda 
#                                 _, e=editor, c=code: _openHelperMenu(e, c, True))
# then in theory this should work:
#   editor.web.eval(f"""document.execCommand('insertHTML', false, %s);""" % json.dumps(code))
# but it often doesn't work in Chrome
# e.g.
#      code = f"<table><tbody><tr><td><pre>{code}</pre></td></tr></tbody></table>"  # works
#      code = f"<p><pre>{code}</pre></p>"  # doesn't work
#      code = f'<pre id="{uuid.uuid4().hex}">{code}</pre>'  # doesn't work
#      code = f'<pre style="" id="{uuid.uuid4().hex}">{code}</pre>'  # doesn't work
#      code = '<pre class="shf_pre">' + code + "</pre>"  # doesn't work
#      code = '<div class="city">' + code + "</div>"     # doesn't work
#      code = """<span style=" font-weight: bold;">code </span>"""  # works
#      code = """<div style=" font-weight: bold;">code </div>"""  # partially: transformed into span?
# That's a known problem, see https://stackoverflow.com/questions/25941559/is-there-a-way-to-keep-execcommandinserthtml-from-removing-attributes-in-chr
# The top answer is to use a custom js inserter function


### MiniFormatPack approach
#     editor.web.eval("setFormat('formatBlock', 'pre')")
# setFormat is a thin Anki wrapper around document.execCommand
# but this formats the whole paragraph and not just the selection


### idea: move the selection to a separate block first. Drawback: in effect there's no undo
# undo in contenteditable is hard, works best if I just use document.execCommand, i.e.
# setFormat. So I have to decide what's more important for me, I think undo is more important


At the moment my version of the MiniFormatSupplementary mostly works so I keep it.
'''


def _openHelperMenu(editor, code, selected_text):
    global LASTUSED

    if gc("remove leading spaces if possible", True):
        code = remove_leading_spaces(code)

    menu = QMenu(editor.widget)
    menu.setStyleSheet(basic_stylesheet)
    # add small info if pasting
    label = QLabel("selection" if selected_text else "paste")
    action = QWidgetAction(editor.widget)
    action.setDefaultWidget(label)
    menu.addAction(action)

    menu.alternative_keys = alternative_keys
    kfilter = keyFilter(menu)
    menu.installEventFilter(kfilter)

    if gc("show pre/code", False):
        # TODO: Do I really need the custom code, couldn't I just wrap in newer versions
        # as with the mini format pack, see https://github.com/glutanimate/mini-format-pack/pull/13/commits/725bb8595631e4dbc56bf881427aeada848e43c9
        m_pre = menu.addAction("&unformatted (<pre>)")
        m_pre.triggered.connect(lambda _, a=editor, c=code: wrap_in_tags(a, c, tag="pre", class_name="shf_pre"))
        m_cod = menu.addAction("unformatted (<&code>)")
        m_cod.triggered.connect(lambda _, a=editor, c=code: wrap_in_tags(a, c, tag="code", class_name="shf_code"))

    defla = get_default_lang(editor)
    if defla in LANG_MAP:
        d = menu.addAction("&default (%s)" % defla)
        d.triggered.connect(lambda _, a=editor, c=code: hilcd(a, c, LANG_MAP[defla]))
    else:
        d = False
        illegal_info(defla)
        return
    
    if LASTUSED:
        l = menu.addAction("l&ast used")
        l.triggered.connect(lambda _, a=editor, c=code: hilcd(a, c, LASTUSED))

    favmenu = menu.addMenu('&favorites')
    favfilter = keyFilter(favmenu)
    favmenu.installEventFilter(favfilter)
    favmenu.alternative_keys = alternative_keys

    a = menu.addAction("&select from all")
    a.triggered.connect(lambda _, a=editor, c=code: onAll(a, c))
    for e in gc("favorites"):
        if e in LANG_MAP:
            a = favmenu.addAction(e)
            a.triggered.connect(lambda _, a=editor, c=code, l=LANG_MAP[e]: hilcd(a, c, l))
        else:
            illegal_info(e)
            return

    if d:
        menu.setActiveAction(d)
    menu.exec(QCursor.pos())


def openHelperMenu(editor):
    selected_text = editor.web.selectedText()
    if selected_text:
        #  Sometimes, self.web.selectedText() contains the unicode character
        # '\u00A0' (non-breaking space). This character messes with the
        # formatter for highlighted code.
        code = selected_text.replace('\u00A0', ' ')
        editor.web.evalWithCallback("document.execCommand('delete');", lambda 
                                    _, e=editor, c=code: _openHelperMenu(e, c, True))
    else:
        clipboard = QApplication.clipboard()
        code = clipboard.text()
        _openHelperMenu(editor, code, False)


def editorContextMenu(ewv, menu):
    e = ewv.editor
    a = menu.addAction("Syntax Highlighting")
    a.triggered.connect(lambda _, ed=e: openHelperMenu(ed))
addHook('EditorWebView.contextMenuEvent', editorContextMenu)


def keystr(k):
    key = QKeySequence(k)
    return key.toString(QKeySequence.SequenceFormat.NativeText)


def setupEditorButtonsFilter(buttons, editor):
    b = editor.addButton(
        os.path.join(addon_path, "icons", "button.png"),
        "syhl_linkbutton",
        openHelperMenu,
        tip="Syntax Highlighting for code ({})".format(keystr(gc("hotkey", ""))),
        keys=gc("hotkey", "")
        )
    buttons.append(b)
    return buttons
addHook("setupEditorButtons", setupEditorButtonsFilter)
