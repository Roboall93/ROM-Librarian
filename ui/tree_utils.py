"""
TreeView utility functions for ROM Librarian
Provides treeview creation and sorting functionality
"""

import os
import tkinter as tk
from tkinter import ttk


def create_scrolled_treeview(parent, columns, show="headings", selectmode="extended"):
    """
    Create a treeview with scrollbars and grid configuration.

    Args:
        parent: Parent widget
        columns: Tuple of column identifiers
        show: What to show ("headings", "tree", or "tree headings")
        selectmode: Selection mode ("extended", "browse", "none")

    Returns:
        ttk.Treeview widget with scrollbars attached
    """
    vsb = ttk.Scrollbar(parent, orient="vertical")
    hsb = ttk.Scrollbar(parent, orient="horizontal")
    tree = ttk.Treeview(parent, columns=columns, show=show, selectmode=selectmode,
                       yscrollcommand=vsb.set, xscrollcommand=hsb.set)
    vsb.config(command=tree.yview)
    hsb.config(command=tree.xview)
    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")
    hsb.grid(row=1, column=0, sticky="ew")
    parent.grid_rowconfigure(0, weight=1)
    parent.grid_columnconfigure(0, weight=1)
    return tree


def sort_treeview(tree, col, reverse, parse_size_func=None):
    """
    Sort treeview contents by column.

    Args:
        tree: ttk.Treeview widget to sort
        col: Column identifier to sort by
        reverse: Sort in reverse order
        parse_size_func: Optional function to parse size strings (e.g., "5.2 MB" -> bytes)
    """
    # Get all items
    items = [(tree.set(item, col), item) for item in tree.get_children('')]

    # Determine sort key based on column
    if col == "size" and parse_size_func:
        # Sort by actual file size (parse formatted size back to bytes)
        items.sort(key=lambda x: parse_size_func(x[0]), reverse=reverse)
    elif col == "date":
        # Sort by date (chronologically)
        items.sort(key=lambda x: x[0], reverse=reverse)
    else:
        # Sort alphabetically for text columns (filename, select checkbox, etc.)
        items.sort(key=lambda x: x[0].lower() if x[0] else "", reverse=reverse)

    # Rearrange items in sorted order
    for index, (val, item) in enumerate(items):
        tree.move(item, '', index)


def get_files_from_tree(tree, folder, selected_only=True, filename_col=0):
    """
    Extract file paths from treeview items.

    Args:
        tree: ttk.Treeview widget
        folder: Folder path where files are located
        selected_only: Only get selected items (default True)
        filename_col: Column index containing filename (default 0)

    Returns:
        List of (full_path, item_id) tuples for existing files
    """
    items = tree.selection() if selected_only else tree.get_children()
    files = []
    for item in items:
        values = tree.item(item, "values")
        filename = values[filename_col]
        full_path = os.path.join(folder, filename)
        if os.path.exists(full_path):
            files.append((full_path, item))
    return files
