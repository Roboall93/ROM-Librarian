# ROM Librarian v1.2.1 - Free ROM Collection Manager

Small but solid update to my ROM collection manager!

## What's new in v1.2.1:

**7z Compression** - The Compression tab now supports 7z alongside ZIP. Pick your format, compress your ROMs. No 7-Zip installation needed — handled entirely in Python.

**Smarter Compression Tab** - Archives now show "Extracted" status when the ROM file is already present. Plus a new "Delete Extracted Only" button so you can safely clean up your archives after extracting — mirrors the existing "Delete Archived Only" on the other side.

**Better CHD conversion feedback** - Large files (PS2 ISOs etc.) now show a size/time warning so the app doesn't look frozen during long conversions.

## What it does (full feature list):

**CHD Conversion** - Convert disc images (CUE/BIN, ISO) to compressed CHD format. chdman included on Windows.

**Smart Renaming** - Regex-based batch renaming with DAT file support (No-Intro). Automatically updates CUE files when you rename BIN files — no more broken disc images.

**Duplicates Detection** - Content-based duplicate scanning with smart auto-selection (keep by region, size, date, etc.)

**Compression Tools** - Batch compress/extract ROMs to ZIP or 7z to save space

**Multi-disc Support** - Auto-generate M3U playlists for games with multiple discs

**Collection Compare** - Compare two ROM folders to find missing files

## Key Features:
- Works with all major ROM formats (NES, SNES, Genesis, PlayStation, N64, GameCube, etc.)
- EmulationStation/RetroPie gamelist.xml auto-update
- Full undo support
- Persistent hash caching (blazing fast re-scans)
- Auto-updater built-in
- Completely free and open source

Available for Windows and Linux. No Python required — just download and run!

GitHub: https://github.com/Roboall93/ROM-Librarian

Built with Claude Code by Anthropic
