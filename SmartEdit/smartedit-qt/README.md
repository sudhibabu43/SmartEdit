# SmartEdit Video Editor

SmartEdit Video Editor is an award-winning free and open-source video editor 
for Linux, Mac, and Windows, and is dedicated to delivering high quality 
video editing and animation solutions to the world.

## Build Status

[![smartedit-qt CI Build](https://github.com/SmartEdit/smartedit-qt/actions/workflows/ci.yml/badge.svg)](https://github.com/SmartEdit/smartedit-qt/actions/workflows/ci.yml) 
[![libsmartedit CI Build](https://github.com/SmartEdit/libsmartedit/actions/workflows/ci.yml/badge.svg)](https://github.com/SmartEdit/libsmartedit/actions/workflows/ci.yml) 
[![libsmartedit-audio CI Build](https://github.com/SmartEdit/libsmartedit-audio/actions/workflows/ci.yml/badge.svg)](https://github.com/SmartEdit/libsmartedit-audio/actions/workflows/ci.yml)
![Discord](https://img.shields.io/discord/1143390791507644496?style=flat)

## Features

* Cross-platform (Linux, Mac, and Windows)
* Support for many video, audio, and image formats (based on FFmpeg)
* Powerful curve-based Key frame animations
* Desktop integration (drag and drop support)
* Unlimited tracks / layers
* Clip resizing, scaling, trimming, snapping, rotation, and cutting
* Video transitions with real-time previews
* Compositing, image overlays, watermarks
* Title templates, title creation, sub-titles
* 2D animation support (image sequences)
* 3D animated titles (and effects)
* SVG friendly, to create and include vector titles and credits
* Scrolling motion picture credits
* Advanced Timeline (including Drag & drop, scrolling, panning, zooming, and snapping)
* Frame accuracy (step through each frame of video)
* Time-mapping and speed changes on clips (slow/fast, forward/backward, etc...)
* Audio mixing and editing
* Digital video effects, including brightness, gamma, hue, greyscale, chroma key, and many more!
* Experimental hardware encoding and decoding (VA-API, NVDEC, D3D9, D3D11, VTB)
* Import & Export widely supported formats (EDL, XML)
* Render videos in many codecs and formats (based on FFmpeg)

## Getting Started

The quickest way to get started using SmartEdit is to download one of 
our pre-built installers. On our download page, click the **Daily Builds** 
button to view the latest, experimental builds, which are created for each 
new commit to this repo.

https://www.smartedit.org/download/

## Tutorial

Watch the official [step-by-step video tutorial](https://www.youtube.com/watch?list=PLymupH2aoNQNezYzv2lhSwvoyZgLp1Q0T&v=1k-ISfd-YBE), or read the official [user-guide](https://www.smartedit.org/user-guide/):

## Developers

Are you interested in becoming more involved in the development of 
SmartEdit? Build exciting new features, fix bugs, make friends, and become a hero! 
Please read the [step-by-step](https://github.com/SmartEdit/smartedit-qt/wiki/Become-a-Developer) 
instructions for getting source code, configuring dependencies, and building SmartEdit.

## Documentation

Beautiful HTML documentation can be generated using Sphinx.

```sh
cd doc
make html
```

The documentation for the most recent release can be viewed online at [smartedit.org/user-guide](https://www.smartedit.org/user-guide/).

## Report a bug

Please report bugs using the official [Report a Bug](https://www.smartedit.org/issues/new/) 
feature on our website. This walks you through the bug reporting process, and helps 
to create a high-quality bug report for the SmartEdit community.

Or you can report a new issue directly on GitHub:

https://github.com/SmartEdit/smartedit-qt/issues

## Translations

Translating SmartEdit into other languages is very easy! Please read the [step-by-step](https://github.com/SmartEdit/smartedit-qt/wiki/Become-a-Translator) instructions or login to LaunchPad and get started.
All you need is a web browser.

* Application Translations: https://translations.launchpad.net/smartedit/2.0/+translations
* Website Translations: https://translations.launchpad.net/smartedit/website/+pots/django

## Dependencies

Although installers are much easier to use, if you must build from 
source, here are some tips: 

SmartEdit is programmed in Python (version 3+), and thus does not need
to be compiled to run. However, be sure you have the following 
dependencies in order to run SmartEdit successfully: 

*  Python 3.0+ (http://www.python.org)
*  PyQt / PySide binding for Qt5 or Qt6 (https://www.riverbankcomputing.com/software/pyqt/ and https://pyside.org/)
*  libsmartedit: SmartEdit Library (https://github.com/SmartEdit/libsmartedit)
*  libsmartedit-audio: SmartEdit Audio Library (https://github.com/SmartEdit/libsmartedit-audio)
*  FFmpeg or Libav (http://www.ffmpeg.org/ or http://libav.org/)
*  GCC build tools (or MinGW on Windows)

For packagers and developers: use `SMARTEDIT_QT_API=auto|pyqt6|pyside6|pyqt5`
to select the Python Qt binding. If building `libsmartedit`, its Qt major
version is selected separately with `-DUSE_QT6=AUTO|ON|OFF`.

## Launch

To run SmartEdit from the command line with an installed `libsmartedit`,
use the following syntax:
(be sure the change the path to match the install or repo location 
of smartedit-qt)

```sh
cd [smartedit-qt folder]
python3 src/launch.py
```
    
To run with a version of `libsmartedit` built from source but not installed,
set `PYTHONPATH` to the location of the compiled Python bindings. e.g.:

```sh
cd [libsmartedit folder]
cmake -B build -S . [options]
cmake --build build
    
cd [smartedit-qt folder]
PYTHONPATH=[libsmartedit folder]/build/bindings/python \
python3 src/launch.py
```

## Websites

- https://www.smartedit.org/  (Official website and blog)
- https://github.com/SmartEdit/smartedit-qt (source code and issue tracker)
- https://github.com/SmartEdit/libsmartedit-audio (source code for audio library)
- https://github.com/SmartEdit/libsmartedit (source code for video library)
- https://launchpad.net/smartedit/

### Copyright & License

Copyright (c) 2008-2022 SmartEdit Studios, LLC. This file is part of
SmartEdit Video Editor (https://www.smartedit.org), an open-source project
dedicated to delivering high quality video editing and animation solutions
to the world.

SmartEdit Video Editor is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

SmartEdit Video Editor is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with SmartEdit Library.  If not, see <http://www.gnu.org/licenses/>.
