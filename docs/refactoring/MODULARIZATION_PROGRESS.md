# ROM Librarian Modularization Progress

## Current Status

**File Size Reduction:** rom_manager.py reduced from **5,803 lines to 5,248 lines** (555 lines removed, 9.6% reduction)

**Status:** ✅ Phase 1 Complete - Foundation modularization successful and tested

---

## What Has Been Completed

### 1. Core Modules ✅
Located in `core/` directory:

- **`core/logging_setup.py`** - Centralized logging with rotating file handler
  - `setup_logging()` - Creates logger with file and console handlers
  - `logger` - Pre-configured logger instance

- **`core/config.py`** - Configuration and cache management
  - `load_config()` - Load app configuration from JSON
  - `save_config()` - Save app configuration to JSON
  - `load_hash_cache()` - Load file hash cache
  - `save_hash_cache()` - Save file hash cache

- **`core/constants.py`** - Application-wide constants
  - VERSION, file paths (CONFIG_FILE, HASH_CACHE_FILE, LOG_FILE, ICON_PATH)
  - ROM_EXTENSIONS_WHITELIST, EXCLUDED_FOLDER_NAMES
  - ES_CONTINUOUS, ES_SYSTEM_REQUIRED

### 2. Parser Modules ✅
Located in `parsers/` directory:

- **`parsers/dat_parser.py`** - DAT file parsing
  - `parse_dat_file(dat_path)` - Parse No-Intro and MAME DAT files
  - Returns: `{hash: game_name}` dictionary
  - Supports both `<game>` and `<machine>` tags

### 3. Operations Modules ✅
Located in `operations/` directory:

- **`operations/file_ops.py`** - File hashing operations
  - `calculate_file_hashes(file_path)` - Calculate CRC32, MD5, SHA1 hashes
  - Handles regular files and ZIP archives containing ROMs
  - Returns: `(crc32_hex, md5_hex, sha1_hex)`

- **`operations/gamelist.py`** - EmulationStation gamelist.xml management
  - `update_gamelist_xml(folder_path, rename_map)` - Update ROM paths in gamelist
  - Creates automatic backups
  - Preserves all metadata (images, descriptions, etc.)

### 4. UI Helper Modules ✅
Located in `ui/` directory:

- **`ui/helpers.py`** - Dialog and UI helper classes
  - `set_window_icon(window)` - Set application icon on windows
  - `CenteredDialog` - Base class for centered modal dialogs
  - `ProgressDialog` - Progress tracking for long operations
  - `ToolTip` - Delayed tooltip widget
  - `show_info()`, `show_error()`, `show_warning()`, `ask_yesno()` - Dialog helpers

### 5. Module Initialization Files ✅
All modules have proper `__init__.py` files for clean imports:
- `core/__init__.py` - Exports all core functionality
- `parsers/__init__.py` - Exports DAT parser
- `operations/__init__.py` - Exports file operations
- `ui/__init__.py` - Exports UI helpers

---

## Module Structure

```
ROM Librarian/
├── rom_manager.py (5,248 lines - main application)
├── rom_manager.py.backup (5,803 lines - backup before modularization)
├── core/
│   ├── __init__.py
│   ├── logging_setup.py (59 lines)
│   ├── config.py (95 lines)
│   └── constants.py (34 lines)
├── parsers/
│   ├── __init__.py
│   └── dat_parser.py (68 lines)
├── operations/
│   ├── __init__.py
│   ├── file_ops.py (90 lines)
│   └── gamelist.py (77 lines)
└── ui/
    ├── __init__.py
    ├── helpers.py (273 lines)
    └── tabs/
        └── base_tab.py (48 lines - foundation for future tab extraction)
```

---

## How to Continue Modularization

### Goal
Reduce rom_manager.py to **under 1,000 lines** by extracting the ROMManager class methods into separate modules.

### Recommended Approach: Tab Extraction

The ROMManager class contains **7 major tabs**, each with 200-500 lines of code. Extract them one at a time into `ui/tabs/` using the BaseTab pattern.

---

## Step-by-Step Tab Extraction Guide

### Pattern for Each Tab

Each tab should follow this structure:

```python
# ui/tabs/example_tab.py
"""
Example Tab for ROM Librarian
Description of what this tab does
"""

import os
import tkinter as tk
from tkinter import ttk
import threading
from ui import show_info, show_error, ask_yesno, ProgressDialog, ToolTip
from ui.tabs.base_tab import BaseTab
from core import logger

class ExampleTab(BaseTab):
    """Tab for doing X functionality"""

    def __init__(self, parent_notebook, root, manager):
        super().__init__(parent_notebook, root, manager)
        self.setup()
        self.add_to_notebook("Tab Title")

    def setup(self):
        """Setup the tab UI"""
        # Create widgets using self.tab as parent
        # Example:
        # label = ttk.Label(self.tab, text="Example")
        # label.pack()
        pass

    def example_action(self):
        """Action triggered by button"""
        # Access shared state:
        # current_folder = self.get_current_folder()
        # files = self.get_files_data()
        pass

    def _example_worker(self):
        """Background worker thread"""
        # Do work...
        # Update UI in main thread:
        # self.root.after(0, lambda: self._update_ui(result))
        pass
```

### Tabs to Extract (in recommended order)

#### 1. M3U Tab (Easiest - ~450 lines)
**File:** `ui/tabs/m3u_tab.py`
**Current location:** rom_manager.py lines 1094-1547
**Methods to extract:**
- `setup_m3u_tab()` → `M3UTab.setup()`
- `_on_m3u_tree_click()` → `M3UTab._on_tree_click()`
- `_update_m3u_create_button()` → `M3UTab._update_create_button()`
- `m3u_select_all()` → `M3UTab.select_all()`
- `m3u_deselect_all()` → `M3UTab.deselect_all()`
- `scan_for_multi_disc()` → `M3UTab.scan()`
- `_scan_multi_disc_worker()` → `M3UTab._scan_worker()`
- `_display_multi_disc_results()` → `M3UTab._display_results()`
- `create_m3u_files()` → `M3UTab.create_files()`
- `_mark_m3u_done()` → `M3UTab._mark_done()`
- `_mark_m3u_error()` → `M3UTab._mark_error()`

**Dependencies:**
- `self.manager.current_folder`
- `self.manager.m3u_scan_mode`, `self.manager.m3u_tree`, etc. → Move to tab class
- Uses: `ToolTip`, `show_info`, `show_error`, `show_warning`, `ask_yesno`, `ProgressDialog`
- Uses: `self.create_scrolled_treeview()` → Need to extract this utility first

#### 2. Compression Tab (~400 lines)
**File:** `ui/tabs/compression_tab.py`
**Current location:** rom_manager.py lines 978-1093
**Methods to extract:**
- `setup_compression_tab()` → `CompressionTab.setup()`
- Compression operation methods

#### 3. Rename Tab (~550 lines)
**File:** `ui/tabs/rename_tab.py`
**Current location:** rom_manager.py lines 695-836
**Methods to extract:**
- `setup_rename_tab()` → `RenameTab.setup()`
- Rename operation methods

#### 4. DAT Rename Tab (~600 lines)
**File:** `ui/tabs/dat_rename_tab.py`
**Current location:** rom_manager.py lines 837-977
**Methods to extract:**
- `setup_dat_rename_tab()` → `DATRenameTab.setup()`
- DAT matching and rename methods

#### 5. Duplicates Tab (~750 lines)
**File:** `ui/tabs/duplicates_tab.py`
**Current location:** rom_manager.py lines 1548-1775
**Methods to extract:**
- `setup_duplicates_tab()` → `DuplicatesTab.setup()`
- `start_duplicate_scan()` → `DuplicatesTab.start_scan()`
- `_scan_files_worker()` → `DuplicatesTab._scan_worker()`
- Duplicate detection and management methods

#### 6. Compare Tab (~800 lines)
**File:** `ui/tabs/compare_tab.py`
**Current location:** rom_manager.py lines 1776-2016
**Methods to extract:**
- `setup_compare_tab()` → `CompareTab.setup()`
- `start_compare()` → `CompareTab.start_compare()`
- `_quick_compare_worker()` → `CompareTab._quick_worker()`
- `_deep_compare_worker()` → `CompareTab._deep_worker()`
- Collection comparison methods

---

## Utility Functions to Extract First

Before extracting tabs, extract these shared utility methods used by multiple tabs:

### Create `ui/tree_utils.py`

```python
"""TreeView utility functions"""

def create_scrolled_treeview(parent, columns, show="headings", selectmode="extended"):
    """Create a treeview with scrollbar"""
    # Extract from rom_manager.py line 2189
    pass

def sort_treeview(tree, col, reverse):
    """Sort treeview by column"""
    # Extract from rom_manager.py line 2280
    pass
```

### Create `ui/formatters.py`

```python
"""Data formatting utilities"""

def format_size(size_bytes):
    """Format file size in human-readable format"""
    # Extract from rom_manager.py line 2165
    pass

def parse_size(size_str):
    """Parse human-readable size to bytes"""
    # Extract from rom_manager.py line 2173
    pass
```

---

## How to Update rom_manager.py After Extraction

After extracting a tab, update rom_manager.py:

### 1. Add import at top
```python
from ui.tabs import M3UTab  # Add this
```

### 2. Update `setup_ui()` method
Replace:
```python
self.setup_m3u_tab()
```

With:
```python
self.m3u_tab = M3UTab(self.notebook, self.root, self)
```

### 3. Remove the old methods
Delete all the methods that were moved to the tab class:
- `setup_m3u_tab()`
- `_on_m3u_tree_click()`
- etc.

### 4. Update any references
If other code references `self.m3u_tree`, update to `self.m3u_tab.tree`

---

## Testing After Each Extraction

After extracting each tab:

1. **Import Test**: Verify Python can import the module
   ```bash
   python -c "from ui.tabs import M3UTab; print('OK')"
   ```

2. **Launch Test**: Start the application and verify it launches without errors
   ```bash
   python rom_manager.py
   ```

3. **Functional Test**: Click on the tab and verify:
   - UI displays correctly
   - All buttons work
   - Operations complete successfully
   - Progress dialogs work
   - Error handling works

4. **Integration Test**: Verify interactions with other tabs still work

---

## Expected Final Structure

After all tabs are extracted:

```
ROM Librarian/
├── rom_manager.py (~800 lines)
│   ├── Imports
│   ├── ROMManager class
│   │   ├── __init__() - initialization
│   │   ├── setup_ui() - create main layout
│   │   ├── setup_menubar() - menu bar
│   │   ├── browse_folder() - folder selection
│   │   ├── Theme management methods
│   │   └── Update checking methods
│   └── main() - Entry point
│
├── ui/
│   ├── helpers.py (dialogs, tooltips)
│   ├── tree_utils.py (treeview utilities)
│   ├── formatters.py (data formatting)
│   └── tabs/
│       ├── base_tab.py (base class)
│       ├── m3u_tab.py (~450 lines)
│       ├── compression_tab.py (~400 lines)
│       ├── rename_tab.py (~550 lines)
│       ├── dat_rename_tab.py (~600 lines)
│       ├── duplicates_tab.py (~750 lines)
│       └── compare_tab.py (~800 lines)
│
├── operations/
│   ├── file_ops.py
│   ├── gamelist.py
│   ├── rename_ops.py (future)
│   ├── compression_ops.py (future)
│   └── duplicate_ops.py (future)
│
├── core/
│   ├── logging_setup.py
│   ├── config.py
│   └── constants.py
│
└── parsers/
    └── dat_parser.py
```

**Projected Final Size:** rom_manager.py at ~800-1,000 lines (85% reduction from original 5,803)

---

## Benefits of Continued Modularization

### Maintainability
- Each tab is self-contained and understandable
- Changes to one tab don't affect others
- Clear separation of concerns

### Testability
- Tabs can be tested in isolation
- Mock the manager for unit tests
- Operations tested independently from UI

### Extensibility
- New tabs added without modifying rom_manager.py
- New operations added to operations/ modules
- Plugin architecture becomes possible

### Code Quality
- Smaller files are easier to review
- Less cognitive load
- Easier onboarding for new contributors

---

## Common Patterns and Tips

### Accessing Shared State
```python
# In tab methods, access manager state through helper methods:
current_folder = self.get_current_folder()
files = self.get_files_data()
config = self.get_config()

# Set status bar message:
self.set_status("Processing...")
```

### Threading Pattern
```python
def action_button_clicked(self):
    """User clicked action button"""
    # Validate
    if not self.get_current_folder():
        show_warning(self.root, "No Folder", "Please select a folder first")
        return

    # Create progress dialog
    progress = ProgressDialog(self.root, "Processing", total_items)

    # Start worker thread
    thread = threading.Thread(target=self._worker, args=(progress,), daemon=True)
    thread.start()

def _worker(self, progress):
    """Background worker"""
    try:
        # Do work...
        for i, item in enumerate(items):
            progress.update(i+1, item_name)
            # Process item...

        progress.close()

        # Update UI in main thread
        self.root.after(0, lambda: show_info(self.root, "Done", "Processing complete"))
    except Exception as e:
        progress.close()
        self.root.after(0, lambda: show_error(self.root, "Error", str(e)))
```

### Widget References
```python
# Store widget references in self.widgets dict:
self.widgets['tree'] = ttk.Treeview(...)
self.widgets['button'] = ttk.Button(...)

# Later access:
self.widgets['tree'].insert(...)
```

---

## Troubleshooting

### Import Errors
- Verify `__init__.py` exists in each directory
- Check import paths are correct
- Ensure all dependencies are imported

### Missing Attributes
- Tab tries to access `self.something` that doesn't exist
- Move the attribute to the tab class `__init__()`
- Or access through `self.manager.something`

### Circular Imports
- Never import rom_manager in tab modules
- Tabs receive manager reference in `__init__()`
- Operations modules should never import UI code

---

## Version Control Recommendations

After each successful tab extraction:

```bash
git add .
git commit -m "Extract M3U tab to ui/tabs/m3u_tab.py"
git tag modularization-m3u-tab
```

This allows easy rollback if needed.

---

## Next Steps

1. Extract `create_scrolled_treeview()` and `sort_treeview()` to `ui/tree_utils.py`
2. Extract `format_size()` and `parse_size()` to `ui/formatters.py`
3. Start with M3U tab (simplest)
4. Test thoroughly
5. Move to next tab
6. Repeat until all tabs extracted

---

## Summary

**Current Progress:**
- ✅ Foundation modules created and tested (core, parsers, operations, ui/helpers)
- ✅ 555 lines removed from rom_manager.py (9.6% reduction)
- ✅ Application tested and working
- ✅ Modular architecture proven successful

**Remaining Work:**
- Extract 7 tabs (~3,500 lines)
- Extract utility functions (~200 lines)
- Final cleanup (~200 lines)

**Estimated Final Reduction:** 3,900+ lines removed (67% reduction)
**Estimated Final Size:** ~800-1,000 lines (from original 5,803 lines)

The foundation is solid. Continue with the tab extraction pattern documented above to complete the modularization.
