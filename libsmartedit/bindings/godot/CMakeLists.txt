####################### CMakeLists.txt (libsmartedit) #########################
# @brief CMake build file for libsmartedit-godot (used to generate GDExtension)
# @author Jonathan Thomas <jonathan@smartedit.org>
#
# @section LICENSE
#
# Copyright (c) 2008-2025 SmartEdit Studios, LLC
#
# SPDX-License-Identifier: LGPL-3.0-or-later

cmake_minimum_required(VERSION 3.17)

project(libsmartedit_godot)

# Clone and build GoDot CPP
# git submodule add https://github.com/godotengine/godot-cpp.git external/godot-cpp
# git submodule update --init --recursive
# cd external/godot-cpp
# scons -c
# scons platform=linux generate_bindings=yes -j$(nproc)
set(GODOT_CPP_PATH ${CMAKE_SOURCE_DIR}/external/godot-cpp)

include_directories(
        ${GODOT_CPP_PATH}/include
        ${GODOT_CPP_PATH}/gen/include
        ${GODOT_CPP_PATH}/gdextension
        ${CMAKE_SOURCE_DIR}/include
)

link_directories(${GODOT_CPP_PATH}/bin)

add_library(libsmartedit_godot SHARED
        register_types.cpp
        osg_timeline.cpp
)

target_link_libraries(libsmartedit_godot
        ${GODOT_CPP_PATH}/bin/libgodot-cpp.linux.template_debug.x86_64.a
        smartedit
)

set_target_properties(libsmartedit_godot PROPERTIES
        OUTPUT_NAME "libsmartedit_godot"
        PREFIX ""
)
