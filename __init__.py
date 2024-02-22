import os
import re
import subprocess
import json
from itertools import islice

import cudatext_cmd as cmds
from cudatext import *
from cudatext_keys import *

from cudax_lib import get_translation
_ = get_translation(__file__)  # i18n

fn_icon = os.path.join(os.path.dirname(__file__), 'icon.png')
fn_config = os.path.join(app_path(APP_DIR_SETTINGS), 'cuda_hotspots.ini')
fn_bookmarks = os.path.join(app_path(APP_DIR_SETTINGS), 'history files.json')
IS_WIN = os.name=='nt'
THEME_TOOLBAR_MAIN = 'toolbar_main'
GIT_SHOW_UNTRACKED_FILES = False

git = ['git', '-c', 'core.quotepath=false']

def _git_status(filepath):
    params = git + ['status', "--porcelain", "--branch", "--untracked-files=all"]
    return __git(params, cwd=os.path.dirname(filepath))
def _git_toplevel(filepath):
    params = git + ['rev-parse', "--show-toplevel"]
    return __git(params, cwd=os.path.dirname(filepath))
def _git_add(filepath, cwd):
    params = git + ['add', filepath]
    return __git(params, cwd)
def _git_restore(filepath, cwd):
    params = git + ['restore', '--staged', '--worktree', filepath]
    return __git(params, cwd)
def _git_unstage(filepath, cwd):
    params = git + ['reset', '--mixed', filepath]
    return __git(params, cwd)
def _git_diff(filepath, cwd, head=False):
    params = git + ['diff', 'HEAD', filepath] if head else git + ['diff', filepath]
    return __git(params, cwd)

def __git(params, cwd=None):
    startupinfo = None
    if IS_WIN:
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    
    try:
        result = subprocess.run(params, capture_output=True, startupinfo=startupinfo, cwd=cwd)
    except:
        return 1, None
    
    return result.returncode, result.stdout if result.returncode == 0 else result.stderr

def read_specific_line(fpath, line):
    # TODO: use 'utf-8' for now, but rework to read 'enc' key from "history files.json"?
    with open(fpath, encoding='utf-8', errors='replace') as input_file:
        line = next(islice(input_file, line, line+1), None)
        if line is not None:
            return line[:100].strip()
    return ""

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

    def form_key_down(self, id_dlg, id_ctl, data):
        if id_ctl in [VK_SPACE, VK_ENTER, VK_F4]:
            self.callback_list_dblclick(id_dlg, id_ctl, data)
            return False #block key
    
    def init_side_form(self):
        h=dlg_proc(0, DLG_CREATE)
        
        dlg_proc(h, DLG_PROP_SET, {
            'keypreview': True,
            'on_key_down': self.form_key_down,
            } )

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
        
    def hotspot_open(self, type, data):
        data = data.split(chr(3))
        if type == 'git':
            top_level, fpathpart = data[:2]
            if " -> " in fpathpart:
                fpathpart = fpathpart.split(" -> ")[1]
            fpath = os.path.join(top_level, fpathpart)
            if fpath and os.path.isfile(fpath):
                file_open(fpath) #, options="/preview")
                ed.focus()
        elif type  == 'bm':
            type, fpath, line = data[:3]
            type = int(type)
            if type == 1: # file
                file_open(fpath) #, options="/preview")
                ed.set_caret(0, int(line))
            elif type == 2: # unsaved tab
                handle = int(fpath)
                for h in ed_handles():
                    if handle == h:
                        e = Editor(h)
                        e.focus()
                        e.set_caret(0, int(line))

    def callback_list_dblclick(self, id_dlg, id_ctl, data='', info=''):
        id_item = tree_proc(self.h_tree, TREE_ITEM_GET_SELECTED)
        if id_item is not None:
            props = tree_proc(self.h_tree, TREE_ITEM_GET_PROPS, id_item)
            h_parent = props['parent']
            if h_parent:
                parent_data = tree_proc(self.h_tree, TREE_ITEM_GET_PROPS, h_parent)['data']
                self.hotspot_open(parent_data, props["data"])

    def set_imagelist_size(self, imglist):
        imagelist_proc(imglist, IMAGELIST_SET_SIZE, (24, 24))

    def toolbar_add_btn(self, h_bar, hint, icon=-1, command=''):
        h_btn = toolbar_proc(h_bar, TOOLBAR_ADD_ITEM)
        if hint=='-':
            button_proc(h_btn, BTN_SET_KIND, BTNKIND_SEP_HORZ)
        else:
            button_proc(h_btn, BTN_SET_KIND, BTNKIND_ICON_ONLY)
            button_proc(h_btn, BTN_SET_HINT, hint)
            button_proc(h_btn, BTN_SET_IMAGEINDEX, icon)
            button_proc(h_btn, BTN_SET_DATA1, command)

    def action_collect_hotspots(self, info=None):
        if not self.h_side:
            self.init_forms()
        tree_proc(self.h_tree, TREE_ITEM_DELETE)

        bookmarks = [] # list of tuple (file,line,type)
        
        # create list of opened files, will be used for deduplication.
        opened_files = []
        for h in ed_handles():
            e = Editor(h)
            fpath = e.get_filename("*")
            if os.path.isfile(fpath):
                opened_files.append(fpath)

        # 1. collect bookmarks from "history files.json"
        bookmarks_json = None
        try:
            with open(fn_bookmarks, encoding='utf-8', errors='replace') as file:
                bookmarks_json = json.load(file)
        except:
            pass
        if bookmarks_json and 'bookmarks' in bookmarks_json:
            for k, v in bookmarks_json['bookmarks'].items():
                fpath = k.replace("|", os.path.sep)
                fpath_expanded = os.path.expanduser(fpath) # expand "~" for linux
                if fpath_expanded in opened_files:
                    continue # deduplication: we don't want info from json, if we can get fresh info from opened tab
                line_numbers = v.split(' ')
                line_numbers.reverse()
                for number in line_numbers:
                    m = re.match(r'^\d+', number)
                    line = int(m.group()) if m else None
                    if line is not None and os.path.isfile(fpath_expanded):
                        bookmarks.append((fpath_expanded, line, 1, read_specific_line(fpath_expanded, line)))

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
                line_str = e.get_text_line(b['line'])[:100].strip()
                bookmarks.append((fpath, b['line'], type, line_str))

        # bookmarks collected: add them to the tree
        bookmarks_item = None
        for b in bookmarks:
            fpath, line, type, line_str = b
            if not bookmarks_item:
                bookmarks_item = tree_proc(
                    self.h_tree,
                    TREE_ITEM_ADD,
                    text=_("Bookmarks"),
                    data='bm'
                )
            text = ''
            data = ''
            if type == 1: # file
                # Replace the path before the last folder with "..."
                last_folder = os.path.basename(os.path.dirname(fpath))
                last_folder2 = os.path.basename(os.path.dirname(os.path.dirname(fpath)))
                short_path = fpath
                if last_folder and last_folder2:
                    file_name = os.path.basename(fpath)
                    short_path = os.path.join("...", last_folder, file_name)
                text = f"{line_str} ({short_path}:{str(line+1)})"
                data = str(type) + chr(3) + fpath + chr(3) + str(line) + chr(3) + line_str
            elif type == 2: # unsaved tab
                fpath, handle = fpath.split(chr(3))
                text = f"{line_str} ({fpath}:{str(line+1)})"
                data = str(type) + chr(3) + handle + chr(3) + str(line) + chr(3) + line_str
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
                # Untracked:
                "??": "--- ",
                # Modified, Deleted, New, Renamed:
                " M": "mod: ",
                "MM": "[*mod]: ",
                "M ": "[mod]: ",
                " D": "del: ",
                "D ": "[del]: ",
                "A ": "[new]: ",
                "AM": "[*new]: ",
                "R ": "[ren]: ",
                # Unmerged (conflict):
                "DD": "!del: ",
                "AU": "[!new]: ",
                "UD": "!del: ",
                "UA": "!new: ",
                "DU": "[!del]: ",
                "AA": "!new: ",
                "UU": "!mod: ",
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
                    text="Git (" + line[3:] + ")",
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
                    data=top_level + chr(3) + fpathpart + chr(3) + status
                )

        tree_proc(self.h_tree, TREE_ITEM_UNFOLD_DEEP)

    def context_menu(self, id_dlg, id_ctl, data='', info=''):
        selected = tree_proc(self.h_tree, TREE_ITEM_GET_SELECTED)
        if selected is None:
            return
        props = tree_proc(self.h_tree, TREE_ITEM_GET_PROPS, selected)
        h_parent = props['parent']
        selected_data = props['data']
        if h_parent:
            parent_data = tree_proc(self.h_tree, TREE_ITEM_GET_PROPS, h_parent)['data']
            if parent_data == 'git':
                top_level, fpathpart, status = selected_data.split(chr(3))
                if " -> " in fpathpart:
                    fpathpart = fpathpart.split(" -> ")[0]
                fpath = os.path.join(top_level, fpathpart)
                if not self.h_menu:
                    self.h_menu = menu_proc(0, MENU_CREATE)
                menu_proc(self.h_menu, MENU_CLEAR)
                if status in ("??", " M", " D", "DD", "AU", "UD", "UA", "DU", "AA", "UU"):
                    menu_proc(self.h_menu, MENU_ADD,
                              lambda *args, **kwargs: self.git_add(fpath, top_level),
                              _("Add"))
                else:
                    menu_proc(self.h_menu, MENU_ADD,
                              lambda *args, **kwargs: self.git_unstage(fpath, top_level),
                              _("Unstage"))
                if status not in ("??"):
                    menu_proc(self.h_menu, MENU_ADD,
                              lambda *args, **kwargs: self.git_restore_ask(fpath, top_level),
                              _("Restore..."))
                if status in (" M", "M ", "MM"):
                    menu_proc(self.h_menu, MENU_ADD, caption="-")
                    menu_proc(self.h_menu, MENU_ADD,
                              lambda *args, **kwargs: self.git_diff(fpath, top_level, head=True),
                              _("Diff head"))
                if status in ("DD", "AU", "UD", "UA", "DU", "AA", "UU"):
                    menu_proc(self.h_menu, MENU_ADD, caption="-")
                    menu_proc(self.h_menu, MENU_ADD,
                              lambda *args, **kwargs: self.git_diff(fpath, top_level),
                              _("Diff unmerged"))
                    
                menu_proc(self.h_menu, MENU_SHOW)

    @collect_hotspots
    def git_add(self, filepath, cwd):
        _git_add(filepath, cwd)

    @collect_hotspots
    def git_unstage(self, filepath, cwd):
        _git_unstage(filepath, cwd)

    @collect_hotspots
    def git_restore_ask(self, filepath, cwd):
        ok = msg_box(_("REALLY restore?"), MB_OKCANCEL+MB_ICONWARNING)
        if ok == ID_OK:
            _git_restore(filepath, cwd)

    def git_diff(self, filepath, cwd, head=False):
        code, output = _git_diff(filepath, cwd, head)
        if code == 0 and output:
            file_open('')
            if ed.get_filename('*') == '' and ed.get_text_all() == '': # ensure we are at correct tab
                ed.set_prop(PROP_TAB_TITLE, 'Diff: ' + filepath)
                ed.set_prop(PROP_LEXER_FILE, 'Diff')
                ed.set_text_all(output.decode())
                ed.set_prop(PROP_MODIFIED, False)

    def get_w_h(self):
        w = 600
        h = 600
        r = app_proc(PROC_COORD_MONITOR, 0)
        if r:
            w = (r[2]-r[0]) * 2 // 3
            h = (r[3]-r[1]) // 2
    
        return w, h

    def go_to_hotspot(self):
        hotspots = []
        self.action_collect_hotspots()
        items = tree_proc(self.h_tree, TREE_ITEM_ENUM_EX)
        
        if items is not None:
            for item_parent in items:
                items = tree_proc(self.h_tree, TREE_ITEM_ENUM_EX, item_parent['id'])
                if items is None:
                    continue
                for item in items:
                    hotspots.append({'text': item['text'], 'hotspot_type': item_parent['data'], 'data': item['data']})
            
            items = []
            for i in hotspots:
                if i['hotspot_type'] == 'git':
                    top_level, fpathpart, status = i['data'].split(chr(3))
                    #items.append(f"{status}: {fpathpart}\t{top_level}")
                    items.append(f"{i['text']}\t{top_level}")
                elif i['hotspot_type'] == 'bm':
                    fpath, line, line_str = i['data'].split(chr(3))[1:]
                    items.append(f"{line_str}\t{fpath}:{str(int(line)+1)}")
            
            w, h = self.get_w_h()
            ind = dlg_menu(DMENU_LIST+DMENU_CENTERED, items, caption=_('Hotspots'), w=w, h=h)
            if ind is not None:
                hotspot = hotspots[ind]
                self.hotspot_open(hotspot['hotspot_type'], hotspot["data"])
        else:
            msg_status(_("No hotspots"))
