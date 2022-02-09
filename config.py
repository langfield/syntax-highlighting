import os

from aqt import mw


addon_folder_abs_path = os.path.dirname(__file__)
css_folder = os.path.join(addon_folder_abs_path, "css")
user_files_folder = os.path.join(addon_folder_abs_path, "user_files")


def get_anki_version():
    try:
        # 2.1.50+ because of bdd5b27715bb11e4169becee661af2cb3d91a443, https://github.com/ankitects/anki/pull/1451
        from anki.utils import point_version
    except:
        try:
            # introduced with 66714260a3c91c9d955affdc86f10910d330b9dd in 2020-01-19, should be in 2.1.20+
            from anki.utils import pointVersion
        except:
            # <= 2.1.19
            from anki import version as anki_version
            out = int(anki_version.split(".")[-1]) 
        else:
            out = pointVersion()
    else:
        out = point_version()
    return out
anki_point_version = get_anki_version()


def gc(arg, fail=False):
    conf = mw.addonManager.getConfig(__name__)
    if conf:
        return conf.get(arg, fail)
    else:
        return fail


# Syntax Highlighting (Enhanced Fork) has the id 1972239816 which 
# is loaded after "extended html editor for fields and card templates (with some versioning)"
# with the id 1043915942
try:
    ex_html_edi = __import__("1043915942").dialog_cm.CmDialogBase
except:
    ex_html_edi = False
