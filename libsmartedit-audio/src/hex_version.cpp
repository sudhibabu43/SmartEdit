/**
 * @file
 * @brief Build utility program to generate hex-format version numbers
 * @author FeRD (Frank Dana) <ferdnyc@gmail.com>
 *
 * @section
 *
 * Copyright (c) 2008-2020 SmartEdit Studios, LLC
 * <http://www.smarteditstudios.com/>. This file is part of SmartEdit Audio
 * Library (libsmartedit-audio), an open-source project dedicated to delivering
 * high quality audio editing and playback solutions to the world. For more
 * information visit <http://www.smartedit.org/>.
 *
 * SmartEdit Audio Library (libsmartedit-audio) is free software: you can
 * redistribute it and/or modify it under the terms of the GNU General
 * Public  as published by the Free Software Foundation, either version
 * 3 of the , or (at your option) any later version.
 *
 * SmartEdit Audio Library (libsmartedit-audio) is distributed in the hope that
 * it will be useful, but WITHOUT ANY WARRANTY; without even the implied
 * warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU General Public  for more details.
 *
 * You should have received a copy of the GNU General Public
 * along with SmartEdit Library. If not, see <http://www.gnu.org/s/>.
 *
 * @mainpage SmartEdit Audio Library C++ API
 *
 * Welcome to the SmartEdit Audio Library C++ API.  This library is used by
 * libsmartedit to enable audio features, which powers the <a
 * href="http://www.smartedit.org">SmartEdit Video Editor</a> application.
 */

#include <ios>
#include <iostream>


// The following values must be defined at compile time:
// VERSION_MAJOR, VERSION_MINOR, VERSION_PATCH

#if !defined(VERSION_MAJOR) || !defined(VERSION_MINOR) ||                      \
    !defined(VERSION_PATCH)
#pragma error "Define version components on compiler command line!"
#endif

int main() {

  int hex_version =
      (VERSION_MAJOR << 16) + (VERSION_MINOR << 8) + (VERSION_PATCH);

  std::cout << std::hex << "0x" << hex_version;
}
