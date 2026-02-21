# ROM Librarian v1.2.1

**Compression Tab improvements, 7z support, and pure Python archive handling.**

---

## What's New

### 7z Compression
The Compression Tab now supports 7z alongside ZIP — just pick your format with the new radio buttons before compressing. No external tools needed; it's all handled natively via Python.

### Compression Tab Parity
The archive side of the Compression Tab now matches the ROM side feature-for-feature:

- Archives show a **"Extracted"** status when their ROM counterpart is already in the folder
- New **"Delete Extracted Only"** button — clean up your archives after extracting, safely
- Mirrors the existing "Delete Archived Only" on the uncompressed side

### Improved Conversion UX
- Large CHD conversions (PS2 ISOs etc.) now show a size estimate and time warning so the app no longer appears frozen
- Informational chdman note is now a calm gray label instead of an orange warning

---

## Installation

**Windows:** Download the ZIP, extract, run `ROM Librarian.exe`
**Linux:** Download the tar.gz, extract, make executable, run

No Python required — fully portable!

---

## Links

- [Download Latest Release](https://github.com/Roboall93/ROM-Librarian/releases/latest)
- [Full Changelog](https://github.com/Roboall93/ROM-Librarian/blob/main/CHANGELOG.md)
- [Documentation](https://github.com/Roboall93/ROM-Librarian/blob/main/README.md)

---

**Built with [Claude Code](https://claude.ai/claude-code) by Anthropic**
