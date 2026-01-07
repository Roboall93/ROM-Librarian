@echo off
REM ROM Librarian Build Script
REM Builds a distributable Windows release

echo ========================================
echo ROM Librarian - Release Build Script
echo ========================================
echo.

REM Set version (update this for each release)
set VERSION=1.0.1

echo Building ROM Librarian v%VERSION%
echo.

REM Clean previous builds
echo Cleaning previous builds...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "ROM-Librarian-v%VERSION%-Windows.zip" del "ROM-Librarian-v%VERSION%-Windows.zip"

REM Build with PyInstaller
echo.
echo Building executable...
python -m PyInstaller rom_librarian.spec --clean --noconfirm

if errorlevel 1 (
    echo.
    echo ERROR: Build failed!
    pause
    exit /b 1
)

REM Create release package
echo.
echo Creating release package...

REM Create a temporary release folder
mkdir "release_temp\ROM Librarian v%VERSION%"

REM Copy the executable and dependencies
xcopy /E /I /Y "dist\ROM Librarian\*" "release_temp\ROM Librarian v%VERSION%\"

REM Copy documentation files
copy README.md "release_temp\ROM Librarian v%VERSION%\README.txt"
copy LICENSE "release_temp\ROM Librarian v%VERSION%\LICENSE.txt"

REM Create ZIP file (requires PowerShell)
echo Creating ZIP archive...
powershell -Command "Compress-Archive -Path 'release_temp\ROM Librarian v%VERSION%' -DestinationPath 'ROM-Librarian-v%VERSION%-Windows.zip' -Force"

REM Clean up temp folder
rmdir /s /q release_temp

echo.
echo ========================================
echo Build Complete!
echo ========================================
echo.
echo Release package: ROM-Librarian-v%VERSION%-Windows.zip
echo.
echo The ZIP file is ready for distribution.
echo Users can extract it and run "ROM Librarian.exe"
echo.
pause
