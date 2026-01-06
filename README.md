# ROM Librarian

A desktop application for managing, organizing, and maintaining retro gaming ROM collections.

![Python](https://img.shields.io/badge/python-3.8+-blue.svg)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey.svg)
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
- **Undo support** for the last rename operation

### Compression Tab
- **Dual-pane interface** showing uncompressed ROMs and ZIP archives
- **Batch compress** ROMs to ZIP format
- **Batch extract** ZIP archives
- **Auto-detection** of ROM file types in folder
- **Safe cleanup** - delete only files that have been archived

### M3U Creation Tab
- **Multi-disc game detection** (Disc 1, Disc 2, CD1, etc.)
- **Automatic M3U playlist generation** for emulators
- **Organized storage** - moves disc files to `.hidden` folder
- Keeps your game list clean with one entry per multi-disc game

### Duplicates Tab
- **Content-based duplicate detection** using SHA1/MD5 hashing
- **Multiple scan modes**: single folder, with subfolders, or entire ROM library
- **Smart auto-selection** strategies:
  - Keep by region preference (USA > Europe > Japan)
  - Keep largest/smallest file
  - Keep oldest/newest file
- **Export duplicate reports** to text file

### Compare Collections Tab
- **Compare two ROM collections** to find differences
- **Quick compare** (by filename) or **Deep compare** (by content hash)
- **Integrity verification** for matching files
- **Copy missing files** between collections
- **Export missing file lists**

## Installation

### Prerequisites
- Python 3.8 or higher
- Windows (uses Windows-specific APIs for sleep prevention)

### Install Dependencies

```bash
pip install ttkbootstrap
```

> **Note:** ttkbootstrap is optional but recommended for theme support (light/dark mode).

### Run the Application

```bash
python rom_manager.py
```

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
