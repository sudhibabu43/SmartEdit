<!--
© SmartEdit Studios, LLC

SPDX-License-Identifier: LGPL-3.0-or-later
-->

SmartEdit Video Library (libsmartedit) is a free, open-source C++ library
dedicated to delivering high quality video editing, animation, and playback
solutions to the world.

## Build Status

[![libsmartedit CI Build](https://github.com/SmartEdit/libsmartedit/actions/workflows/ci.yml/badge.svg)](https://github.com/SmartEdit/libsmartedit/actions/workflows/ci.yml) [![libsmartedit-audio CI Build](https://github.com/SmartEdit/libsmartedit-audio/actions/workflows/ci.yml/badge.svg)](https://github.com/SmartEdit/libsmartedit-audio/actions/workflows/ci.yml)

## Features

* Cross-Platform (Linux, Mac, and Windows)
* Multi-Layer Compositing
* Video and Audio Effects (Chroma Key, Color Adjustment, Grayscale, etc…)
* Animation Curves (Bézier, Linear, Constant)
* Time Mapping (Curve-based Slow Down, Speed Up, Reverse)
* Audio Mixing & Resampling (Curve-based)
* Audio Plug-ins (VST & AU)
* Audio Drivers (ASIO, WASAPI, DirectSound, CoreAudio, iPhone Audio,
  ALSA, JACK, and Android)
* Telecine and Inverse Telecine (Film to TV, TV to Film)
* Frame Rate Conversions
* Multi-Processor Support (Performance)
* Python and Ruby Bindings (All Features Supported)
* Qt Video Player Included (Ability to display video on any QWidget)
* Unit Tests (Stability)
* All FFmpeg Formats and Codecs Supported (Images, Videos, and Audio files)
* Full Documentation with Examples (Doxygen Generated)

## Install

Detailed instructions for building libsmartedit and libsmartedit-audio for
each OS. These instructions are also available in the `/docs/` source folder.

   * [Linux](https://github.com/SmartEdit/libsmartedit/wiki/Linux-Build-Instructions)
   * [Mac](https://github.com/SmartEdit/libsmartedit/wiki/Mac-Build-Instructions)
   * [Windows](https://github.com/SmartEdit/libsmartedit/wiki/Windows-Build-Instructions)

## Hardware Acceleration

SmartEdit now supports experimental hardware acceleration, both for encoding
and decoding videos. When enabled, this can either speed up those operations
or slow them down, depending on the power and features supported by your
graphics card.

Please see [`doc/HW-ACCEL.md`](doc/HW-ACCEL.md) for more information.

## Documentation

Beautiful HTML documentation can be generated using Doxygen.
```
make doc
```
(Also available online: http://smartedit.org/files/libsmartedit/)

## Developers

Are you interested in becoming more involved in the development of SmartEdit?
Build exciting new features, fix bugs, make friends, and become a hero!
Please read the [step-by-step](https://github.com/SmartEdit/smartedit-qt/wiki/Become-a-Developer)
instructions for getting source code, configuring dependencies, and building
SmartEdit.

## Report a bug

You can report a new libsmartedit issue directly on GitHub:

https://github.com/SmartEdit/libsmartedit/issues

## Websites

- https://www.smartedit.org/  (Official website and blog)
- https://github.com/SmartEdit/libsmartedit/ (source code and issue tracker)
- https://github.com/SmartEdit/libsmartedit-audio/ (source code for audio library)
- https://github.com/SmartEdit/smartedit-qt/ (source code for Qt client)
- https://launchpad.net/smartedit/

### Copyright & License

Copyright (c) 2008-2022 SmartEdit Studios, LLC. This file is part of
SmartEdit Video Editor (https://www.smartedit.org), an open-source project
dedicated to delivering high quality video editing and animation solutions
to the world.

SmartEdit Library (libsmartedit) is free software: you can redistribute it
and/or modify it under the terms of the GNU Lesser General Public License
as published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

SmartEdit Library (libsmartedit) is distributed in the hope that it will be
useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with SmartEdit Library. If not, see http://www.gnu.org/licenses/.

To release a commercial product which uses libsmartedit (i.e. video
editing and playback), commercial licenses are also available: contact
sales@smartedit.org for more information.
