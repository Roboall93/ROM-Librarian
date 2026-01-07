# GitHub Release Guide

This guide will help you publish a new release of ROM Librarian on GitHub.

## Prerequisites

- Your code should be pushed to GitHub
- You should be logged into GitHub
- The build should be tested and working

## Step-by-Step Release Process

### 1. Build the Release Package

Run the build script to create the distributable ZIP file:

```bash
build_release.bat
```

This will create a file named `ROM-Librarian-v1.0.1-Windows.zip` in the project directory.

### 2. Commit and Push Your Changes

```bash
git add .
git commit -m "Release v1.0.1 - Bug fixes and improvements"
git push origin main
```

### 3. Create a GitHub Release

1. Go to your repository on GitHub
2. Click on "Releases" in the right sidebar (or go to `/releases`)
3. Click the "Draft a new release" button
4. Fill in the release information:

   **Tag version:** `v1.0.1`
   - Click "Create new tag: v1.0.1 on publish"

   **Release title:** `ROM Librarian v1.0.1`

   **Description:** Copy the relevant section from CHANGELOG.md, for example:

   ```markdown
   ## What's New in v1.0.1

   ### Fixed
   - Increased default window size to properly show all controls
   - Added auto-update of rename preview when selecting regex presets
   - Fixed rename complete dialog to properly display long messages
   - Implemented persistent hash caching - re-scans are now much faster!
   - Fixed duplicate list export dialog and export format

   ### Added
   - Cache hit statistics in duplicate scan results
   - Scrollable text widget for long dialog messages

   ## Download

   Download the ZIP file below, extract it to any location, and run `ROM Librarian.exe`.
   No installation or Python required!

   ## System Requirements
   - Windows 10 or later
   - Approximately 50MB disk space for the application
   ```

5. **Attach the ZIP file:**
   - Drag and drop `ROM-Librarian-v1.0.1-Windows.zip` into the "Attach binaries" section
   - Or click to browse and select the file

6. **Publish:**
   - If this is a stable release, leave "Set as a pre-release" unchecked
   - If this is the latest version, check "Set as the latest release"
   - Click "Publish release"

### 4. Update README (Optional)

If this is your first release, update the download link in README.md:

Replace `YOUR_USERNAME` with your actual GitHub username in the releases link.

## Release Checklist

Before publishing:

- [ ] All bugs from testing are fixed
- [ ] Version number updated in `rom_manager.py`
- [ ] CHANGELOG.md is updated with changes
- [ ] Build script runs successfully
- [ ] ZIP file created and tested
- [ ] All changes committed and pushed to GitHub
- [ ] Release notes prepared

## Tips

- **Version Numbering:** Follow semantic versioning (MAJOR.MINOR.PATCH)
  - MAJOR: Breaking changes
  - MINOR: New features (backward compatible)
  - PATCH: Bug fixes

- **Pre-releases:** For beta versions, use tags like `v1.1.0-beta.1` and check "pre-release"

- **Release Timing:** Consider releasing on specific days (e.g., Fridays) so users have the weekend to test

## Example Release Schedule

1. **Monday-Thursday:** Development and testing
2. **Friday:** Build release, create GitHub release
3. **Weekend:** Monitor for critical bugs
4. **Monday:** Hot-fix if needed, otherwise start next cycle
