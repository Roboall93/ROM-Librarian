# ROM Librarian

A cross-platform desktop application for managing, organizing, and maintaining retro gaming ROM collections.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-lightgrey.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

## Features

### Rename Tab
- **Regex-based batch renaming** with live preview
- **Preset patterns** for common cleanup tasks:
  - Remove region tags (USA, Europe, Japan)
  - Clean translation tags
  - Remove GoodTools dump tags
  - Convert underscores to spaces
- **Collision detection** with multiple handling strategies
- **Select All/Deselect All** buttons for batch operations
- **Auto-update gamelist.xml** - Automatically updates EmulationStation/RetroPie metadata when renaming files
- **CUE file awareness** - Automatically updates CUE file contents when renaming BIN files (keeps disc images intact)
- **Undo support** for the last rename operation (includes gamelist.xml restoration)

### DAT Rename Tab
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
- **CUE file awareness** - Automatically updates CUE file contents when renaming BIN files
- **Refresh button** - Rescan after operations in other tabs
- **Full undo support** with tree updates and gamelist.xml restoration

### Compression Tab
- **Dual-pane interface** showing uncompressed ROMs and compressed archives
- **ZIP and 7z compression** - choose your archive format via radio buttons
- **Batch compress** ROMs to ZIP or 7z format (no external tools required)
- **Batch extract** ZIP and 7z archives
- **Auto-detection** of ROM file types in folder
- **Status tracking** - archives marked "Extracted" when their ROM counterpart exists
- **Safe cleanup** - "Delete Archived Only" and "Delete Extracted Only" buttons for safe one-click cleanup after operations

### Conversion Tab
- **CHD format conversion** for disc images used with MAME/RetroArch
- **CUE/BIN → CHD** - Convert PlayStation and other disc images to compressed CHD format
- **ISO → CHD** - Convert ISO disc images to CHD format
- **Smart validation** - Automatically validates BIN file references in CUE files
- **Bulk conversion** - Convert selected files or all files at once
- **Source cleanup** - Optional deletion of source files after successful conversion
- **Progress tracking** - Real-time progress with detailed error reporting
- **Bundled chdman** - No separate installation required (Windows; Linux users need chdman in PATH)

### M3U Creation Tab
- **Multi-disc game detection** (Disc 1, Disc 2, CD1, etc.)
- **Automatic M3U playlist generation** for emulators
- **Organized storage** - Moves disc files to `.hidden` folder
- Keeps your game list clean with one entry per multi-disc game

### Duplicates Tab
- **Content-based duplicate detection** using SHA1/MD5 hashing
- **Persistent hash caching** - Re-scans are lightning fast when files haven't changed
- **Multiple scan modes**: single folder, with subfolders, or entire ROM library
- **Smart auto-selection** strategies:
  - Keep by region preference (USA > Europe > Japan)
  - Keep largest/smallest file
  - Keep oldest/newest file
- **Export duplicate reports** to text file
- **Archive awareness** - Note: Archives are compared as files, not by ROM content inside (extract first for accurate detection)

### Compare Collections Tab
- **Compare two ROM collections** to find differences
- **Quick compare** (by filename) or **Deep compare** (by content hash)
- **Integrity verification** for matching files
- **Copy missing files** between collections
- **Export missing file lists**

### Updates Menu
- **Auto-updater** - Automatically check for new releases from GitHub
- **Check on Startup** toggle (enabled by default)
- **Manual update check** - "Check for Updates" option
- **Release notes preview** - See what's new before updating

## Installation

### Windows

#### For End Users (Recommended)

1. **Download** the latest `ROM-Librarian-vX.X.X-Windows.zip` from the [Releases](https://github.com/Roboall93/ROM-Librarian/releases) page
2. **Extract** the ZIP file to any location on your computer
3. **Run** `ROM Librarian.exe` from the extracted folder

No Python installation required! The application is fully portable.

### Linux

#### For End Users (Recommended)

1. **Download** the latest `ROM-Librarian-vX.X.X-Linux.tar.gz` from the [Releases](https://github.com/Roboall93/ROM-Librarian/releases) page
2. **Extract** the archive:
   ```bash
   tar -xzf ROM-Librarian-vX.X.X-Linux.tar.gz
   ```
3. **Make executable** (if needed):
   ```bash
   chmod +x ROM-Librarian
   ```
4. **Run** the application:
   ```bash
   ./ROM-Librarian
   ```

**Note:** The Linux version runs without themes for maximum compatibility across distributions.

### For Developers

#### Prerequisites
- Python 3.8 or higher
- tkinter (usually included with Python)

#### Install Dependencies

**Windows:**
```bash
pip install -r requirements.txt
```

**Linux:**
```bash
pip install py7zr
pip install ttkbootstrap  # Optional - not recommended on Linux
```

> **Note:** On Linux, the app works best without ttkbootstrap due to compatibility issues with some distributions.

#### Run from Source

```bash
python rom_manager.py
```

#### Building Releases

**Windows:**
```bash
build_release.bat
```

**Linux:**
```bash
pyinstaller rom_manager.py --onefile --noconsole --name "ROM-Librarian" \
  --hidden-import=PIL --hidden-import=PIL._tkinter_finder \
  --hidden-import=PIL.Image --hidden-import=PIL.ImageTk \
  --clean --noconfirm
```

## Usage

1. **Select a ROM folder** using the Browse button at the top
2. **Navigate between tabs** to access different features
3. **Preview changes** before applying (rename operations show previews)
4. **Use tooltips** - Hover over buttons for 1-2 seconds to see descriptions

## Supported ROM Formats

### Cartridge-based Systems
`.nds`, `.gba`, `.gbc`, `.gb`, `.sfc`, `.smc`, `.nes`, `.n64`, `.z64`, `.v64`, `.md`, `.smd`, `.gen`, `.gg`, `.sms`, `.pce`, `.ngp`, `.ngc`, `.ws`, `.wsc`

### Disc-based Systems
`.bin`, `.iso`, `.cue`, `.chd`, `.cso`, `.gcm`, `.rvz`, `.wbfs`, `.wad`

### Modern Systems
`.dol`, `.elf`, `.nsp`, `.xci`, `.nca`

### Archives
`.zip`, `.7z`, `.rar`, `.gz`

## Platform Notes

### Windows
- Full theme support (light/dark modes)
- All features fully functional
- Sleep prevention during long operations

### Linux
- Runs on most distributions including Steam Deck
- No theme support (plain Tk interface)
- Some features may have limited functionality on certain distributions
- Tested on Ubuntu, Arch Linux, and SteamOS

## Credits

- **Developed by:** RobotWizard
- **Built with:** [Claude Code](https://claude.ai/claude-code) by Anthropic
- **App Icon:** [Game cartridge icons by Creatype - Flaticon](https://www.flaticon.com/free-icons/game-cartridge)

## License

MIT License - See [LICENSE](LICENSE) file for details.
