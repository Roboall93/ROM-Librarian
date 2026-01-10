# ROM Librarian

A desktop application for managing, organizing, and maintaining retro gaming ROM collections.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## Features

### Rename Collections
- **Regex-based batch renaming** with live preview
- **Preset patterns** for common cleanup tasks:
  - Remove region tags (USA, Europe, Japan)
  - Clean translation tags
  - Remove GoodTools dump tags
  - Convert underscores to spaces
- **Collision detection** with multiple handling strategies
- **Select All/Deselect All** buttons for batch operations
- **Auto-update gamelist.xml** - Automatically updates EmulationStation/RetroPie metadata when renaming files
- **Undo support** for the last rename operation (includes gamelist.xml restoration)

### DAT Renaming
- **No-Intro DAT file support** for accurate ROM naming
- **Multi-hash matching** - Uses CRC32, MD5, and SHA1 for precise identification
- **ZIP file support** - Hashes ROM files inside zip archives for matching
- **Live preview** - See matched files before renaming
- **Smart filtering** - Skip files already correctly named
- **Sortable columns** - Click column headers to sort results
- **Selection tools** - Select All/Deselect All with click-and-drag support
- **Unmatched file tracking** - Shows files that couldn't be matched (for manual review)
- **Export functionality** - Export list of unmatched files
- **Auto-update gamelist.xml** - Maintains EmulationStation/RetroPie metadata
- **Refresh button** - Rescan after operations in other tabs
- **Full undo support** with tree updates and gamelist.xml restoration

### Bulk Compression
- **Dual-pane interface** showing uncompressed ROMs and ZIP archives
- **Batch compress** ROMs to ZIP format
- **Batch extract** ZIP archives
- **Auto-detection** of ROM file types in folder
- **Safe cleanup** - delete only files that have been archived

### Automatic M3U Creation
- **Multi-disc game detection** (Disc 1, Disc 2, CD1, etc.)
- **Automatic M3U playlist generation** for emulators
- **Organized storage** - moves disc files to `.hidden` folder
- Keeps your game list clean with one entry per multi-disc game

### Duplicates Detection
- **Content-based duplicate detection** using SHA1/MD5 hashing
- **Persistent hash caching** - re-scans are lightning fast when files haven't changed
- **Multiple scan modes**: single folder, with subfolders, or entire ROM library
- **Smart auto-selection** strategies:
  - Keep by region preference (USA > Europe > Japan)
  - Keep largest/smallest file
  - Keep oldest/newest file
- **Export duplicate reports** to text file

### Compare Collections
- **Compare two ROM collections** to find differences
- **Quick compare** (by filename) or **Deep compare** (by content hash)
- **Integrity verification** for matching files
- **Copy missing files** between collections
- **Export missing file lists**

### Updates Menu
- **Auto-updater** - Automatically check for new releases from GitHub
- **Check on Startup** toggle (enabled by default)
- 
## Installation

### For End Users (Recommended)

1. **Download** the latest release from the [Releases](https://github.com/YOUR_USERNAME/rom-librarian/releases) page
2. **Extract** the ZIP file to any location on your computer
3. **Run** `ROM Librarian.exe` from the extracted folder

No Python installation required! The application is fully portable.

### For Developers

#### Prerequisites
- Python 3.8 or higher
- Windows (uses Windows-specific APIs for sleep prevention)

#### Install Dependencies

```bash
pip install ttkbootstrap
```

> **Note:** ttkbootstrap is optional but recommended for theme support (light/dark mode).

#### Run from Source

```bash
python rom_manager.py
```

#### Building Releases

To create a distributable package:

```bash
build_release.bat
```

This will create a ZIP file in the project directory ready for distribution.

## Usage

1. **Select a ROM folder** using the Browse button at the top
2. **Navigate between tabs** to access different features
3. **Preview changes** before applying (rename operations show previews)
4. **Use tooltips** - hover over buttons for 1-2 seconds to see descriptions

## Screenshots

*Coming soon*

## Supported ROM Formats

### Cartridge-based Systems
`.nds`, `.gba`, `.gbc`, `.gb`, `.sfc`, `.smc`, `.nes`, `.n64`, `.z64`, `.v64`, `.md`, `.smd`, `.gen`, `.gg`, `.sms`, `.pce`, `.ngp`, `.ngc`, `.ws`, `.wsc`

### Disc-based Systems
`.bin`, `.iso`, `.cue`, `.chd`, `.cso`, `.gcm`, `.rvz`, `.wbfs`, `.wad`

### Modern Systems
`.dol`, `.elf`, `.nsp`, `.xci`, `.nca`

### Archives
`.zip`, `.7z`, `.rar`, `.gz`

## Credits

- **Developed by:** RobotWizard
- **Built with:** [Claude Code](https://claude.ai/claude-code) by Anthropic
- **App Icon:** [Game cartridge icons by Creatype - Flaticon](https://www.flaticon.com/free-icons/game-cartridge)

## License

MIT License - See [LICENSE](LICENSE) file for details.
