import sys
import os
import re
import subprocess
import json
import cudatext_cmd as cmds
from cudatext import *

from cudax_lib import get_translation
_ = get_translation(__file__)  # i18n

fn_icon = os.path.join(os.path.dirname(__file__), 'icon.png')
fn_config = os.path.join(app_path(APP_DIR_SETTINGS), 'cuda_hotspots.ini')
fn_bookmarks = os.path.join(app_path(APP_DIR_SETTINGS), 'history files.json')
IS_WIN = os.name=='nt'
IS_MAC = sys.platform=='darwin'
THEME_TOOLBAR_MAIN = 'toolbar_main'
GIT_SHOW_UNTRACKED_FILES = False

def _git_status(filepath):
    params = ['git', 'status', "--porcelain", "--branch", "--untracked-files=all"]
    return __git(params, cwd=os.path.dirname(filepath))
def _git_toplevel(filepath):
    params = ['git', 'rev-parse', "--show-toplevel"]
    return __git(params, cwd=os.path.dirname(filepath))
def _git_add(filepath, cwd):
    params = ['git', 'add', filepath]
    return __git(params, cwd)
def _git_restore(filepath, cwd):
    params = ['git', 'restore', '--staged', '--worktree', filepath]
    return __git(params, cwd)
def _git_unstage(filepath, cwd):
    params = ['git', 'reset', '--mixed', filepath]
    return __git(params, cwd)
def _git_diff(filepath, cwd):
    params = ['git', 'diff', 'HEAD', filepath]
    return __git(params, cwd)

def __git(params, cwd=None):
    startupinfo = None
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    result = subprocess.run(params, capture_output=True, startupinfo=startupinfo, cwd=cwd)
    return result.returncode, result.stdout if result.returncode == 0 else result.stderr

def collect_hotspots(func):
    def wrapper(self, *args, **kwargs):
        func(self, *args, **kwargs)
        self.action_collect_hotspots()
    return wrapper

class Command:
    title_side = 'Hotspots'
    h_side = None

    def __init__(self):
        self.h_menu = None
        self.h_tree = None

    def upd_history_combo(self):
        self.input.set_prop(PROP_COMBO_ITEMS, '\n'.join(self.history))

    def init_forms(self):
        self.h_side = self.init_side_form()
        app_proc(PROC_SIDEPANEL_ADD_DIALOG, (self.title_side, self.h_side, fn_icon))

    def open_side_panel(self):
        #dont init form twice!
        if not self.h_side:
            self.init_forms()

        #dlg_proc(self.h_side, DLG_CTL_FOCUS, name='list')
        app_proc(PROC_SIDEPANEL_ACTIVATE, (self.title_side, True)) # True - set focus

    def init_side_form(self):
        h=dlg_proc(0, DLG_CREATE)

        n = dlg_proc(h, DLG_CTL_ADD, 'toolbar')
        dlg_proc(h, DLG_CTL_PROP_SET, index=n, prop={
            'name': 'bar',
            'align': ALIGN_TOP,
            'h': 24,
            'autosize': True,
        })

        self.h_toolbar = dlg_proc(h, DLG_CTL_HANDLE, index=n)
        self.h_imglist = toolbar_proc(self.h_toolbar, TOOLBAR_GET_IMAGELIST)
        self.set_imagelist_size(self.h_imglist)

        n=dlg_proc(h, DLG_CTL_ADD, 'treeview')
        dlg_proc(h, DLG_CTL_PROP_SET, index=n, prop={
            'name': 'list',
            'align': ALIGN_CLIENT,
            'on_click_dbl': self.callback_list_dblclick,
            'on_menu': self.context_menu,
        })
        self.h_tree = dlg_proc(h, DLG_CTL_HANDLE, index=n)
        tree_proc(self.h_tree, TREE_THEME)

        # fill toolbar
        dirname = os.path.join(os.path.dirname(__file__), THEME_TOOLBAR_MAIN)
        icon_collect = imagelist_proc(self.h_imglist, IMAGELIST_ADD, os.path.join(dirname, 'collect.png'))
        icon_toggle_untracked = imagelist_proc(self.h_imglist, IMAGELIST_ADD, os.path.join(dirname, 'untracked.png'))

        toolbar_proc(self.h_toolbar, TOOLBAR_THEME)
        self.toolbar_add_btn(self.h_toolbar, _('Collect hotspots'),
                             icon_collect, 'cuda_hotspots.action_collect_hotspots')
        self.toolbar_add_btn(self.h_toolbar, '-')

        def toggle_show_untracked_files():
            global GIT_SHOW_UNTRACKED_FILES
            GIT_SHOW_UNTRACKED_FILES = not GIT_SHOW_UNTRACKED_FILES
            self.action_collect_hotspots()
        self.toolbar_add_btn(self.h_toolbar, _('Git: Toggle untracked files'),
                             icon_toggle_untracked, toggle_show_untracked_files)

        toolbar_proc(self.h_toolbar, TOOLBAR_SET_WRAP, index=True)
        toolbar_proc(self.h_toolbar, TOOLBAR_UPDATE)

        #dlg_proc(h, DLG_SCALE)
        return h

    @collect_hotspots
    def on_save(self, ed_self):
        pass # decorator will trigger on_save

    def callback_list_dblclick(self, id_dlg, id_ctl, data='', info=''):
        id_item = tree_proc(self.h_tree, TREE_ITEM_GET_SELECTED)
        if id_item is not None:
            props = tree_proc(self.h_tree, TREE_ITEM_GET_PROPS, id_item)
            h_parent = props['parent']
            if h_parent:
                parent_data = tree_proc(self.h_tree, TREE_ITEM_GET_PROPS, h_parent)['data']
                data = props["data"].split('|')
                if parent_data == 'git':
                    top_level, fpathpart, _ = data
                    if " -> " in fpathpart:
                        fpathpart = fpathpart.split(" -> ")[1]
                    fpath = os.path.join(top_level, fpathpart)
                    if fpath and os.path.isfile(fpath):
                        file_open(fpath, options="/preview")
                        ed.focus()
                elif parent_data  == 'bm':
                    type, fpath, line = data
                    type = int(type)
                    if type == 1: # file
                        file_open(fpath, options="/preview")
                        ed.set_caret(0, int(line))
                    elif type == 2: # unsaved tab
                        handle = int(fpath)
                        for h in ed_handles():
                            if handle == h:
                                e = Editor(h)
                                e.focus()
                                e.set_caret(0, int(line))

    def set_imagelist_size(self, imglist):
        imagelist_proc(imglist, IMAGELIST_SET_SIZE, (24, 24))

    def toolbar_add_btn(self, h_bar, hint, icon=-1, command=''):
        toolbar_proc(h_bar, TOOLBAR_ADD_ITEM)
        cnt = toolbar_proc(h_bar, TOOLBAR_GET_COUNT)
        h_btn = toolbar_proc(h_bar, TOOLBAR_GET_BUTTON_HANDLE, index=cnt-1)
        if hint=='-':
            button_proc(h_btn, BTN_SET_KIND, BTNKIND_SEP_HORZ)
        else:
            button_proc(h_btn, BTN_SET_KIND, BTNKIND_ICON_ONLY)
            button_proc(h_btn, BTN_SET_HINT, hint)
            button_proc(h_btn, BTN_SET_IMAGEINDEX, icon)
            button_proc(h_btn, BTN_SET_DATA1, command)

    def action_collect_hotspots(self, info=None):
        if not self.h_tree:
            return
        tree_proc(self.h_tree, TREE_ITEM_DELETE)

        bookmarks = [] # list of tuple (file,line,type)

        # 1. collect bookmarks from "history files.json"
        bookmarks_json = None
        try:
            with open(fn_bookmarks) as file:
                bookmarks_json = json.load(file)
        except:
            pass
        if bookmarks_json and 'bookmarks' in bookmarks_json:
            bookmarks_item = None
            for k, v in bookmarks_json['bookmarks'].items():
                fpath = k.replace("|", os.path.sep)
                fpath_expanded = os.path.expanduser(fpath) # expand "~" for linux
                line_numbers = v.split(' ')
                line_numbers.reverse()
                for number in line_numbers:
                    m = re.match(r'^\d+', number)
                    line = int(m.group()) if m else None
                    if line and os.path.isfile(fpath_expanded):
                        bookmarks.append((fpath_expanded, line, 1))

        # 2. collect bookmarks of opened tabs
        for h in ed_handles():
            e = Editor(h)
            bookmarks_tab = e.bookmark(BOOKMARK_GET_ALL, 0)
            bookmarks_tab.reverse()
            for b in bookmarks_tab:
                fpath = e.get_filename("*")
                type = 1 # file
                if not fpath:
                    fpath = e.get_prop(PROP_TAB_TITLE) + chr(3) + str(h)
                    type = 2 # unsaved tab
                bookmarks.append((fpath, b['line'], type))

        # bookmarks collected: add them to the tree
        bookmarks = list(dict.fromkeys(bookmarks)) # deduplicate
        for b in bookmarks:
            fpath, line, type = b
            if not bookmarks_item:
                bookmarks_item = tree_proc(
                    self.h_tree,
                    TREE_ITEM_ADD,
                    text="bookmarks",
                    data='bm'
                )
            text = ''
            data = ''
            if type == 1: # file
                text = os.path.basename(fpath) + ", "+str(line+1) + " (" + os.path.dirname(fpath) + ")"
                data=str(type)+"|"+fpath+"|"+str(line)
            elif type == 2: # unsaved tab
                fpath, handle = fpath.split(chr(3))
                text=fpath + ", "+str(line+1)
                data=str(type)+"|"+handle+"|"+str(line) # TODO: editor handle?
            tree_proc(self.h_tree, TREE_ITEM_ADD, id_item=bookmarks_item, text=text, data=data)
        tree_proc(self.h_tree, TREE_ITEM_UNFOLD_DEEP)

        # 3. collect modified git repo files
        fpath = ed.get_filename("*")
        if not os.path.isfile(fpath):
            return

        code, output = _git_toplevel(fpath)
        if code != 0:
            return
        top_level = os.path.normpath(output.decode().strip())

        code, output = _git_status(fpath)
        output = [line.decode() for line in output.split(b'\n')]
        if code != 0:
            return
        git = None
        for line in output:
            if line.strip() == "":
                continue
            code_dict = {
                "??": "--- ",
                " M": "mod: ",
                "MM": "[*mod]: ",
                "M ": "[mod]: ",
                " D": "del: ",
                "D ": "[del]: ",
                "A ": "[new]: ",
                "AM": "[*new]: ",
                "R ": "[ren]: ",
            }
            status = line[:2]
            if status == "??" and not GIT_SHOW_UNTRACKED_FILES:
                continue
            icon = code_dict.get(status)
            if not icon:
                icon = status+": "
            if status == "##":
                git = tree_proc(
                    self.h_tree,
                    TREE_ITEM_ADD,
                    text="git (" + line[3:] + ")",
                    data='git'
                )
            else:
                fpathpart = os.path.normpath(line[3:].strip('"'))
                tree_proc(
                    self.h_tree,
                    TREE_ITEM_ADD,
                    id_item=git,
                    index=-1,
                    text=icon+fpathpart,
                    data=top_level + "|" + fpathpart + "|" + status
                )

        tree_proc(self.h_tree, TREE_ITEM_UNFOLD_DEEP)

    def action_save_project_as(self, info=None):
        msg_box('Save Project As action', MB_OK)

    def context_menu(self, id_dlg, id_ctl, data='', info=''):
        selected = tree_proc(self.h_tree, TREE_ITEM_GET_SELECTED)
        props = tree_proc(self.h_tree, TREE_ITEM_GET_PROPS, selected)
        h_parent = props['parent']
        selected_data = props['data']
        if h_parent:
            parent_data = tree_proc(self.h_tree, TREE_ITEM_GET_PROPS, h_parent)['data']
            if parent_data == 'git':
                top_level, fpathpart, status = selected_data.split('|')
                if " -> " in fpathpart:
                    fpathpart = fpathpart.split(" -> ")[0]
                fpath = os.path.join(top_level, fpathpart)
                if not self.h_menu:
                    self.h_menu = menu_proc(0, MENU_CREATE)
                menu_proc(self.h_menu, MENU_CLEAR)
                if status in ("??", " M", " D"):
                    menu_proc(self.h_menu, MENU_ADD,
                              lambda *args, **kwargs: self.git_add(fpath, top_level),
                              "Add")
                else:
                    menu_proc(self.h_menu, MENU_ADD,
                              lambda *args, **kwargs: self.git_unstage(fpath, top_level),
                              "Unstage")
                if status not in ("??"):
                    menu_proc(self.h_menu, MENU_ADD,
                              lambda *args, **kwargs: self.git_restore_ask(fpath, top_level),
                              "Restore...")
                if status in (" M", "M ", "MM"):
                    menu_proc(self.h_menu, MENU_ADD, caption="-")
                    menu_proc(self.h_menu, MENU_ADD,
                              lambda *args, **kwargs: self.git_diff(fpath, top_level),
                              "Diff head")
                menu_proc(self.h_menu, MENU_SHOW)

    @collect_hotspots
    def git_add(self, filepath, cwd):
        _git_add(filepath, cwd)

    @collect_hotspots
    def git_unstage(self, filepath, cwd):
        _git_unstage(filepath, cwd)

    @collect_hotspots
    def git_restore_ask(self, filepath, cwd):
        ok = msg_box("REALLY restore?", MB_OKCANCEL+MB_ICONWARNING)
        if ok == ID_OK:
            _git_restore(filepath, cwd)

    def git_diff(self, filepath, cwd):
        code, output = _git_diff(filepath, cwd)
        if code == 0 and output:
            ed.cmd(cmds.cmd_FileNew)
            ed.set_prop(PROP_TAB_TITLE, 'Diff: ' + filepath)
            ed.set_prop(PROP_LEXER_FILE, 'Diff')
            ed.set_text_all(output.decode())
            ed.set_prop(PROP_MODIFIED, False)
