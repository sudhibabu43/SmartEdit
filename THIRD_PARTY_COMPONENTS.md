# SmartEdit Third-Party Components & Provenance

This document outlines the source provenance and integration strategy for the foundational libraries that power the SmartEdit video editing engine. 

SmartEdit is constructed as a modern UI application that relies on an integrated, highly-modified core multimedia engine. To comply with open-source licenses and clearly demarcate intellectual property boundaries, all components are classified below.

## 1. SmartEdit Original Code

The following components are **100% original code** written specifically for the SmartEdit project:
- **SmartEdit UI**: The entire PyQt5 frontend application located in `SmartEdit/`.
- **SmartEdit AI Integration**: The advanced AI components, including Shaky Footage Detection, Blur Detection, AI Action Cards, SLM integration, and Silence/Pan-shot detection located within the Python layers.
- **SmartEdit Build Pipeline**: Custom deployment scripts like `run_smartedit.bat`.

## 2. Modified Third-Party Core Frameworks

The core media-processing engine (which handles decoding, encoding, timeline playback, and memory caching) was forked and heavily adapted from the upstream **libsmartedit** repository.

### libsmartedit (Core Video Engine)
- **Original Project**: [smartedit Video Editor (libsmartedit)](https://github.com/smartedit/libsmartedit)
- **License**: LGPL 3.0 (or later)
- **Purpose**: Powers the C++ timeline processing, video decoding (via FFmpeg), video encoding, and image manipulation (via Qt).
- **Modifications Made**: 
  - Integrated into the SmartEdit architecture.
  - Python bindings adapted via SWIG to output a `smartedit` module module instead of `smartedit`.
  - Upstream demonstration and UI-specific configuration logic disabled.
  - Build targets renamed to `libsmartedit.dll`.
- **Where it is used**: Automatically loaded by the SmartEdit Python UI via `_smartedit.pyd`.

### libsmartedit-audio (Audio Engine)
- **Original Project**: [smartedit Audio Library (libsmartedit-audio)](https://github.com/smartedit/libsmartedit-audio)
- **License**: GPL 3.0 / LGPL
- **Purpose**: Audio resampling, buffering, and device output.
- **Modifications Made**:
  - Heavily stripped of upstream demo implementations.
  - ASIO compilation hard-disabled for MSYS2 Windows builds.
  - Exported as `libsmartedit-audio.dll`.
- **Where it is used**: Dynamically linked and consumed by the `libsmartedit` engine.

## 3. Unmodified Upstream Dependencies

The following external dependencies are utilized verbatim during compilation or runtime via the MSYS2 MinGW toolchain:

- **FFmpeg (avcodec, avformat, etc)**: Core video stream demuxing and decoding.
- **Qt5/Qt6**: UI bindings and SVG rendering support.
- **ZeroMQ (cppzmq)**: Used internally by the C++ engine for high-performance multiprocessing.
- **JUCE Framework**: The underlying audio framework powering `libsmartedit-audio`. (Required LGPL/GPL disclosures are preserved in the C++ headers).
- **SWIG**: Simplified Wrapper and Interface Generator used to bind the C++ engine to Python.

## 4. Architectural Separation

To respect upstream design patterns while embedding them smoothly into SmartEdit:
1. **Namespaces**: The `smartedit::` C++ namespace has been rigorously preserved throughout the core engine to prevent ABI breakage and maintain compatibility with upstream updates.
2. **Python Mapping**: The SmartEdit Python layer abstracts this dependency by mapping the upstream API safely behind `import smartedit`, ensuring that the top-level Python developer experience remains exclusively SmartEdit-branded.
