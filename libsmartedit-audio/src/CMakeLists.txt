#################### CMakeLists.txt (libsmartedit-audio) ######################
# @brief CMake build file for libsmartedit-audio (used to generate makefiles)
# @author Jonathan Thomas <jonathan@smartedit.org>
#
# @section LICENSE
#
# Copyright (c) 2008-2016 SmartEdit Studios, LLC
# <http://www.smarteditstudios.com/>. This file is part of
# SmartEdit Audio Library (libsmartedit-audio), an open-source project dedicated
# to delivering high quality audio editing and playback solutions to the
# world. For more information visit <http://www.smartedit.org/>.
#
# SmartEdit Audio Library (libsmartedit-audio) is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# SmartEdit Audio Library (libsmartedit-audio) is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with SmartEdit Audio Library. If not, see <http://www.gnu.org/licenses/>.
################################################################################

add_executable(smartedit-audio-demo Main.cpp)
target_link_libraries(smartedit-audio-demo SmartEdit::Audio)

# Set compile features in ancient CMake (newer releases would
# make them transitive from the library)
if(CMAKE_VERSION VERSION_LESS 3.8)
  set_target_properties(smartedit-audio-demo PROPERTIES
    CXX_STANDARD 11
    CXX_STANDARD_REQUIRED YES
    CXX_EXTENSIONS NO
  )
endif()

install(TARGETS smartedit-audio-demo
  RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR}
)

