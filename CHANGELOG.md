# Changelog

All notable changes to ROM Librarian will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2024-XX-XX

### Added
- **Conversion Tab**: New tab for converting disc images to CHD format
  - CUE/BIN → CHD conversion support
  - ISO → CHD conversion support
  - Smart BIN file validation for CUE files
  - Bulk conversion with progress tracking
  - Optional source file deletion after successful conversion
  - Bundled chdman.exe utility (Windows)
- **CUE File Awareness**: Both Rename and DAT Rename tabs now automatically update CUE file contents when renaming BIN files
  - Prevents broken CUE/BIN pairs after renaming operations
  - Automatic FILE reference updates in CUE files
  - Logging of all CUE file updates

### Fixed
- CUE/BIN pairing issues when BIN filenames don't match CUE references
- Improved BIN file detection by extracting basename from paths in CUE files
- Added debug logging for CUE file parsing issues

### Changed
- Version bumped to 1.2.0 to reflect major feature additions
- Updated documentation with CHD conversion and CUE file awareness features

### Technical
- Added `conversion_tab.py` module with full CHD conversion support
- Integrated `chdman.exe` into build process via PyInstaller spec file
- Enhanced both `rename_tab.py` and `dat_rename_tab.py` with `_update_cue_files()` method
- Uses subprocess for safe external tool execution with timeout handling
- Automatic cleanup of partial CHD files on conversion failure

## [1.1.3] - 2024-XX-XX

### Changed
- **Major Refactoring**: Reduced main file from 5,803 lines to 788 lines (86.4% reduction)
- Extracted 6 tabs into modular components:
  - RenameTab
  - DATRenameTab
  - CompressionTab
  - M3UTab
  - DuplicatesTab
  - CompareTab
- Reorganized project structure with clean separation of concerns:
  - `core/` - Configuration, constants, logging
  - `operations/` - File operations, hash calculations, gamelist updates
  - `parsers/` - DAT file parsing
  - `ui/` - UI components, helpers, formatters, tree utilities
  - `ui/tabs/` - Modular tab controllers

### Technical
- Improved maintainability and code organization
- Better separation of UI and business logic
- Easier to add new features and fix bugs
- Consistent patterns across all tabs

## [1.1.2] - 2024-XX-XX

### Added
- Initial public release
- Rename Tab with regex-based batch renaming
- DAT Rename Tab with No-Intro DAT support
- Compression Tab for ZIP operations
- M3U Creation Tab for multi-disc games
- Duplicates Tab with content-based detection
- Compare Collections Tab
- Auto-updater functionality

[1.2.0]: https://github.com/Roboall93/ROM-Librarian/releases/tag/v1.2.0
[1.1.3]: https://github.com/Roboall93/ROM-Librarian/releases/tag/v1.1.3
[1.1.2]: https://github.com/Roboall93/ROM-Librarian/releases/tag/v1.1.2
