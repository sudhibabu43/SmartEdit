# SmartEdit Project Rename - Product Requirements Document

## Overview
- **Summary**: Rename the entire OpenShot project to SmartEdit, including all project directories, file names, paths, imports, references, build configurations, CMake files, resources, application metadata, UI text, executable names, and DLL/library references.
- **Purpose**: Rebrand the OpenShot video editor application fully to SmartEdit while preserving all existing functionality and editing logic.
- **Target Users**: Developers building and maintaining the SmartEdit video editor, end users of the application.

## Goals
- Rename the top-level `OpenShot/` directory to `SmartEdit/`
- Rename library directories `libopenshot/` to `libsmartedit/` and `libopenshot-audio/` to `libsmartedit-audio/`
- Update all path references in IDE configuration files (.vscode/c_cpp_properties.json)
- Ensure no broken paths or imports are created by the rename
- Verify CMake/build files still work with new paths
- Verify application title and UI branding show SmartEdit consistently
- Ensure internal module/library references are updated consistently
- Preserve all existing functionality; do not modify editing logic
- Perform recursive post-change verification to ensure no OpenShot/openshot references remain (except intentional compatibility shims)

## Non-Goals
- Do not rename third-party dependencies
- Do not modify video editing logic or algorithms
- Do not change any functional behavior of the application
- Do not remove or modify the intentional compatibility shim in `_libsmartedit.py` that creates bidirectional OpenShot/SmartEdit symbol aliases for pre-compiled binary compatibility
- Do not modify pre-compiled binary DLL/PYD files (libsmartedit.dll, _smartedit.pyd)

## Background & Context
- The project is located at `d:\mini project updation\smartEdit1`
- Initial exploration reveals the project is already partially renamed:
  - Most source files, CMake files, and UI text already reference "SmartEdit" or "smartedit"
  - Application metadata in info.py uses "SmartEdit Video Editor" (PRODUCT_NAME)
  - Main window title is "SmartEdit Video Editor"
  - About dialog title is "About SmartEdit"
  - CMakeLists.txt files already use project name "libsmartedit" and "SmartEditAudio"
- Remaining items requiring rename:
  1. Directory: `OpenShot/` → `SmartEdit/`
  2. Directory: `libopenshot/` → `libsmartedit/`
  3. Directory: `libopenshot-audio/` → `libsmartedit-audio/`
  4. File: `.vscode/c_cpp_properties.json` - paths referencing old directory names
- The `_libsmartedit.py` file contains an intentional compatibility shim (lines 26-81) that creates bidirectional aliases between OPENSHOT_* ↔ SMARTEDIT_* and OpenShot* ↔ SmartEdit* symbols. This shim exists because pre-compiled binaries (_smartedit.pyd, libsmartedit.dll) were compiled before the rename and still export original symbols. This shim MUST be preserved.

## Functional Requirements
- **FR-1**: All three top-level directories (OpenShot, libopenshot, libopenshot-audio) must be renamed to their SmartEdit equivalents
- **FR-2**: All file content references to old directory names must be updated to match new names
- **FR-3**: IDE configuration (.vscode/c_cpp_properties.json) must reflect correct include paths and compile_commands.json location
- **FR-4**: All existing imports and module references in source code must resolve correctly after rename
- **FR-5**: Intentional compatibility shim in _libsmartedit.py must remain intact and functional

## Non-Functional Requirements
- **NFR-1**: No broken import paths or file references after the rename
- **NFR-2**: CMake configuration must remain syntactically valid with updated paths
- **NFR-3**: All existing source code must remain parseable and syntactically correct
- **NFR-4**: Post-rename recursive grep for "openshot|OpenShot" must return zero results EXCEPT for the intentional compatibility shim lines in _libsmartedit.py and any references inside pre-compiled binary files (DLL, PYD)

## Constraints
- **Technical**: Pre-compiled binaries (libsmartedit.dll, _smartedit.pyd, etc.) are binary files and cannot be text-searched or modified for internal symbol names. These are excluded from the text rename requirement.
- **Technical**: Build artifact directories (build/, CMakeFiles/, etc.) may be regenerated after the rename; if they contain stale references, these can be cleaned up or accepted as ephemeral.
- **Business**: Compatibility with pre-compiled DLL symbols must be maintained via the existing shim.
- **Dependencies**: No changes to third-party dependencies (Qt, FFmpeg, JUCE, SWIG, etc.)

## Assumptions
- The user has write permissions to rename directories and edit all files in the project
- The compatibility shim in _libsmartedit.py is the ONLY intentional source of "OpenShot" text references and should be preserved exactly as-is
- Build directories may contain auto-generated files with old references; these are acceptable as they will be regenerated on next build

## Acceptance Criteria

### AC-1: Directory rename - OpenShot to SmartEdit
- **Type**: `rule`
- **Given**: Project root directory exists at `d:\mini project updation\smartEdit1`
- **When**: Directory rename operations are completed
- **Then**: `OpenShot/` directory no longer exists and `SmartEdit/` directory exists with identical contents
- **Pass Condition**: `Test-Path "d:\mini project updation\smartEdit1\SmartEdit"` returns True AND `Test-Path "d:\mini project updation\smartEdit1\OpenShot"` returns False
- **Evidence**: File system listing of project root showing SmartEdit directory and no OpenShot directory

### AC-2: Directory rename - libopenshot to libsmartedit
- **Type**: `rule`
- **Given**: Project root directory exists
- **When**: Directory rename operations are completed
- **Then**: `libopenshot/` directory no longer exists and `libsmartedit/` directory exists with identical contents
- **Pass Condition**: `Test-Path "d:\mini project updation\smartEdit1\libsmartedit"` returns True AND `Test-Path "d:\mini project updation\smartEdit1\libopenshot"` returns False
- **Evidence**: File system listing of project root showing libsmartedit directory and no libopenshot directory

### AC-3: Directory rename - libopenshot-audio to libsmartedit-audio
- **Type**: `rule`
- **Given**: Project root directory exists
- **When**: Directory rename operations are completed
- **Then**: `libopenshot-audio/` directory no longer exists and `libsmartedit-audio/` directory exists with identical contents
- **Pass Condition**: `Test-Path "d:\mini project updation\smartEdit1\libsmartedit-audio"` returns True AND `Test-Path "d:\mini project updation\smartEdit1\libopenshot-audio"` returns False
- **Evidence**: File system listing of project root showing libsmartedit-audio directory and no libopenshot-audio directory

### AC-4: IDE configuration paths updated
- **Type**: `rule`
- **Given**: Directory renames are complete
- **When**: Reading `.vscode/c_cpp_properties.json`
- **Then**: All includePath entries and compileCommands path reference `libsmartedit` and `libsmartedit-audio` (not libopenshot or libopenshot-audio)
- **Pass Condition**: Grep for `libopenshot` in c_cpp_properties.json returns 0 matches; grep for `libsmartedit` returns matches for the correct new paths
- **Evidence**: File contents of updated c_cpp_properties.json showing correct new paths

### AC-5: No unintended OpenShot references remain in source text files
- **Type**: `rubric`
- **Dimension**: Completeness of rename across all text-based source, config, and build files
- **Scale**: 1-5
- **Anchors**: 
  - 1 = Multiple source files still reference openshot/OpenShot (10+ occurrences in non-shim, non-binary files)
  - 3 = Minor residual references remain in build artifacts only (2-9 occurrences)
  - 5 = Zero references to openshot/OpenShot in any editable text file EXCEPT the intentional compatibility shim in _libsmartedit.py
- **Pass Threshold**: >= 4
- **Evidence**: Recursive grep output across project for `openshot|OpenShot` pattern, excluding binary file formats (DLL, PYD, PNG, SVG, ICO, etc.) and excluding the known compatibility shim lines

### AC-6: Import and path integrity preserved
- **Type**: `rule`
- **Given**: All rename operations are complete
- **When**: Verifying key source files reference valid existing paths
- **Then**: Python imports like `from classes import info`, `import smartedit`, and `from windows import about` still resolve to correct files under new directory structure; QRC resource paths and UI file paths remain valid
- **Pass Condition**: All referenced include directories from c_cpp_properties.json exist; all Python package __init__.py files exist at expected paths under SmartEdit/smartedit-qt/src/
- **Evidence**: Directory listings confirming SmartEdit/smartedit-qt/src/classes/__init__.py, SmartEdit/smartedit-qt/src/windows/__init__.py exist and key referenced paths are valid

### AC-7: UI branding consistency (SmartEdit name)
- **Type**: `rule`
- **Given**: Directory renames complete
- **When**: Checking key UI metadata files
- **Then**: PRODUCT_NAME in info.py = "SmartEdit Video Editor", main-window.ui windowTitle = "SmartEdit Video Editor", about.ui windowTitle = "About SmartEdit"
- **Pass Condition**: All three values match expected SmartEdit branding (already confirmed via initial scan, verify unchanged post-rename)
- **Evidence**: Grep output for PRODUCT_NAME, windowTitle in the respective files

## Open Questions
- None identified. Initial exploration confirms the scope is well understood.
