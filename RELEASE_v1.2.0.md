# 🎮 ROM Librarian v1.2.0

**Major release combining complete architecture refactoring with powerful new disc image management features.**

---

## 🆕 What's New

### CHD Conversion Tab
Convert your disc images to the space-saving CHD format used by MAME and RetroArch emulators.

- **CUE/BIN → CHD**: PlayStation and other disc images
- **ISO → CHD**: Standard ISO disc images  
- **Smart validation**: Automatically checks that all BIN files are present
- **Bulk operations**: Convert entire collections at once
- **Progress tracking**: Real-time conversion progress with detailed error reporting
- **chdman included**: No need to download separately (Windows)

### CUE File Awareness
Never break your disc images again when renaming files!

- Both **Rename** and **DAT Rename** tabs now automatically update CUE file contents
- When you rename a BIN file, the CUE file updates its references automatically
- Keeps your disc image pairs intact during bulk operations
- Full logging of all updates for transparency

### Improved Architecture
Behind the scenes, the entire codebase has been refactored for better performance and maintainability.

- **86% smaller** main file (5,803 lines → 788 lines)
- Modular tab system for easier updates
- Cleaner code organization
- Improved stability

---

## 🔧 Improvements

- Better BIN file detection in CUE files
- Enhanced error handling and logging
- Updated documentation with new features
- Optimized file operations

---

## 📥 Installation

**Windows:** Download the ZIP, extract, and run `ROM Librarian.exe`  
**Linux:** Download the tar.gz, extract, make executable, and run

No Python installation required - fully portable!

---

## 🔗 Links

- [Download Latest Release](https://github.com/Roboall93/ROM-Librarian/releases/latest)
- [Full Changelog](https://github.com/Roboall93/ROM-Librarian/blob/main/CHANGELOG.md)
- [Documentation](https://github.com/Roboall93/ROM-Librarian/blob/main/README.md)

---

**Built with [Claude Code](https://claude.ai/claude-code) by Anthropic**
