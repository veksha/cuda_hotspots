Plugin for CudaText.
Gives panel (in CudaText side-panel) to show all existing bookmarks to jump to;
also shows Git modified/untracked files.

Panel can be shown by:
- click on plugin's sidebar icon
- menu item "Plugins / Hotspots / Open side panel"

Bookmarks list shows 2 lists, combined/deduplicated:
- bookmarks from all opened UI-tabs
- bookmarks saved to CudaText file 'settings/history files.json'

Note: You must click "Collect hotspots" to refresh the list, also it is refreshed on save file action.

For filenames in the 'Git' panel item, plugin supports context menu with items:
- Add
- Unstage
- Restore...
- Diff head

Author: Yuriy Balyuk, https://github.com/veksha
License: MIT
Icons: from Lazarus IDE project, free license.