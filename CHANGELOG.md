# Changelog

All notable changes to ROM Librarian will be documented in this file.

## [1.0.1] - 2025-01-07

### Fixed
- **Window Size**: Increased default window size (1200x900) to properly show status bar and all duplicate controls
- **Rename Preview**: Added auto-update of preview when selecting regex presets
- **Rename Dialog**: Fixed rename complete dialog to properly display long messages with scrollable text
- **Hash Caching**: Implemented persistent hash caching for duplicate scans - re-scans are now much faster when files haven't changed
- **Export Dialog**: Fixed duplicate list export dialog showing correct file path instead of last scanned file
- **Export Format**: Fixed duplicates.txt export to properly show Keep/Delete status for each file

### Added
- Cache hit statistics displayed in duplicate scan summary
- Scrollable text widget for long dialog messages

## [1.0.0] - 2025-01-06

### Initial Release

#### Features

##### Rename Tab
- Regex-based batch renaming with live preview
- Preset patterns for common cleanup tasks
- Collision detection with multiple handling strategies
- Undo support for the last rename operation

##### Compression Tab
- Dual-pane interface showing uncompressed ROMs and ZIP archives
- Batch compress ROMs to ZIP format
- Batch extract ZIP archives
- Auto-detection of ROM file types
- Safe cleanup - delete only archived files

##### M3U Creation Tab
- Multi-disc game detection
- Automatic M3U playlist generation for emulators
- Organized storage in `.hidden` folders

##### Duplicates Tab
- Content-based duplicate detection using SHA1/MD5 hashing
- Multiple scan modes (folder, with subfolders, entire library)
- Smart auto-selection strategies
- Export duplicate reports to text file
- Persistent hash caching for faster re-scans

##### Compare Collections Tab
- Compare two ROM collections to find differences
- Quick compare (filename) or Deep compare (content hash)
- Integrity verification for matching files
- Copy missing files between collections
- Export missing file lists

#### Supported Platforms
- Windows 10/11

#### Supported ROM Formats
- Cartridge: .nds, .gba, .gbc, .gb, .sfc, .smc, .nes, .n64, .z64, .v64, .md, .smd, .gen, .gg, .sms, .pce, .ngp, .ngc, .ws, .wsc
- Disc: .bin, .iso, .cue, .chd, .cso, .gcm, .rvz, .wbfs, .wad
- Modern: .dol, .elf, .nsp, .xci, .nca
- Archives: .zip, .7z, .rar, .gz
