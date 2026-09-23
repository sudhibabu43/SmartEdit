# SmartEdit Library Migration Guide (libsmartedit)

This document details the transition process and modifications made to the `libsmartedit` component during its integration into the SmartEdit ecosystem. The library is originally based on `libopenshot` and has been adapted to function seamlessly within SmartEdit while preserving original functionality and licenses.

## 1. Overview of Changes

The overarching goal was to shift the namespace, build configurations, and SWIG Python bindings from `OPENSHOT` to `SMARTEDIT`, without affecting the underlying implementations.

### 1.1 Core Modifications
- Replaced `openshot` namespace with `smartedit` in C++ headers and source files where applicable, especially in `smarteditVersion.cpp`.
- Adjusted `#include` paths and namespaces to properly resolve core functionality.
- Fixed C++ integer types in `Exceptions.h` by including `<cstdint>` to resolve missing `int64_t` types under MinGW64 compiler settings.

### 1.2 Build System Updates
- Refactored CMake configurations (`CMakeLists.txt`, `src/CMakeLists.txt`, `bindings/python/CMakeLists.txt`) to build the new library name `libsmartedit` and its SWIG wrappers.
- Corrected the `SmartEditVersion.h.in` CMake template by fixing spacing around variable substitution (e.g., changed `@VARIABLE @` to `@VARIABLE@`).
- Ensured proper generation of `SmartEditVersion.h`.

### 1.3 Python Bindings (SWIG)
- Repaired corrupted `%` directives in `smartedit.i` that caused "Syntax error in input" during SWIG compilation.
- Extracted grouped `%include` macros onto separate lines for correct parsing.
- Restored broken embedded `%pythoncode` block for `Fraction` which was previously mangled by a C++ code formatter.
- Successfully built `_smartedit.pyd` (SWIG C++ extension) and `_libsmartedit.py` (Python shim), eliminating the `AttributeError: module '_smartedit' has no attribute 'Settings_PATH_smartedit_INSTALL_get'` exception at app initialization.

## 2. Important Guidelines Maintained
- **No Destruction**: Original directory structure and non-conflicting components of `libsmartedit` remain intact.
- **Copyright Integrity**: All original third-party copyright, SPDX identifiers, and license notices have been strictly retained to honor the open-source provenance.
- **Functionality Intact**: Code behavior remains fundamentally unchanged to prevent regressions in multimedia playback and editing logic.

## 3. Next Steps for Developers
- Ensure the `build` directory is cleanly generated using MSYS2 MinGW64 with `cmake --build . -j16`.
- Note that Python application dependencies (e.g., `cv2`, `librosa`) must be installed in the MinGW64 Python environment, as `SmartEditApp` heavily relies on these external modules for media analysis.
