####################### CMakeLists.txt (libsmartedit) #########################
# @brief CMake build file for libsmartedit (used to generate Ruby SWIG bindings)
# @author Jonathan Thomas <jonathan@smartedit.org>
#
# @section LICENSE
#
# Copyright (c) 2008-2019 SmartEdit Studios, LLC
#
# SPDX-License-Identifier: LGPL-3.0-or-later

############### RUBY BINDINGS ################
find_package(SWIG 3.0 REQUIRED)
include(${SWIG_USE_FILE})

### Use modern SWIG target behavior when available
if (POLICY CMP0078)
	cmake_policy(SET CMP0078 NEW)
endif()
if (POLICY CMP0086)
	cmake_policy(SET CMP0086 NEW)
endif()

find_package(Ruby)
if (NOT RUBY_FOUND)
  return()
endif()

### Ruby 2.7.0 made API changes that are incompatible with versions of
### SWIG prior to 4.0.3
option(SILENCE_RUBY_VERSION_WARNING
  "Don't warn about possible SWIG incompatibilities with Ruby 2.7.0+" OFF)

if (${RUBY_VERSION} VERSION_GREATER 2.6.9 AND ${SWIG_VERSION} VERSION_LESS 4.0.2)
  if (NOT ${SILENCE_RUBY_VERSION_WARNING})
    message(WARNING "\
Ruby 2.7.0+ detected, building the libsmartedit Ruby API bindings \
requires either SWIG 4.0.2+ or an older version patched with this commit: \
https://github.com/swig/swig/commit/5542cc228ad10bdc5c91107afb77c808c43bf2a4 \
(Recent Fedora and Ubuntu distro packages of SWIG 4.0.1 have already been \
patched.)")
    message(STATUS "To disable the previous warning, add \
-DSILENCE_RUBY_VERSION_WARNING:BOOL=1 to the cmake command line, \
or enable the option in the CMake GUI.")
  endif()
endif()

### Include the Ruby header files
include_directories(${RUBY_INCLUDE_DIRS})

if (CMAKE_VERSION VERSION_LESS 3.12)
  ### Include project headers
  include_directories(
    "${PROJECT_SOURCE_DIR}/src"
    "${PROJECT_BINARY_DIR}/src")
endif()

### Enable C++ in SWIG
set_property(SOURCE smartedit.i PROPERTY CPLUSPLUS ON)
set_property(SOURCE smartedit.i PROPERTY SWIG_MODULE_NAME smartedit)

# Set the SWIG_FLAGS from the library target, IFF its
# COMPILE_DEFINITIONS property is set (in practice, always true)
if(CMAKE_VERSION VERSION_GREATER 3.15)
  set(_defs
    $<REMOVE_DUPLICATES:$<TARGET_PROPERTY:smartedit,COMPILE_DEFINITIONS>>)
elseif(CMAKE_VERSION VERSION_GREATER 3.12)
  set(_defs $<TARGET_PROPERTY:smartedit,COMPILE_DEFINITIONS>)
endif()
if(DEFINED _defs)
  set_property(SOURCE smartedit.i PROPERTY
    COMPILE_DEFINITIONS ${_defs})
else()
  get_property(_defs TARGET smartedit PROPERTY COMPILE_DEFINITIONS)
  foreach(_d ${_defs})
    list(APPEND _flags -D${_d})
  endforeach()
  set_property(SOURCE smartedit.i PROPERTY
    SWIG_FLAGS ${_flags})
endif()

### Suppress a ton of warnings in the generated SWIG C++ code
set(SWIG_CXX_FLAGS "-Wno-unused-variable -Wno-unused-function \
  -Wno-deprecated-copy -Wno-class-memaccess -Wno-cast-function-type \
  -Wno-unused-parameter -Wno-catch-value -Wno-sign-compare -Wno-ignored-qualifiers")
separate_arguments(sw_flags UNIX_COMMAND ${SWIG_CXX_FLAGS})
set_property(SOURCE smartedit.i PROPERTY GENERATED_COMPILE_OPTIONS ${sw_flags})

### Take include dirs from target
if(CMAKE_VERSION VERSION_GREATER 3.15)
  set(_inc $<REMOVE_DUPLICATES:$<TARGET_PROPERTY:smartedit,INCLUDE_DIRECTORIES>>)
elseif(CMAKE_VERSION VERSION_GREATER 3.12)
  set(_inc $<TARGET_PROPERTY:smartedit,INCLUDE_DIRECTORIES>)
endif()
if (DEFINED _inc)
  set_property(SOURCE smartedit.i PROPERTY INCLUDE_DIRECTORIES ${_inc})
endif()

### (FINALLY!)
### Properly manage dependencies (regenerate bindings after changes)
if (CMAKE_VERSION VERSION_GREATER 3.20)
  set_property(SOURCE smartedit.i PROPERTY USE_SWIG_DEPENDENCIES TRUE)
endif()

### Add the SWIG interface file (which defines all the SWIG methods)
swig_add_library(rbsmartedit LANGUAGE ruby SOURCES smartedit.i)

if (POLICY CMP0078)
  set(_rbsmartedit_target rbsmartedit)
else()
  set(_rbsmartedit_target ${SWIG_MODULE_rbsmartedit_REAL_NAME})
endif()

### Set name of target (with no prefix, since Ruby does not like that)
# XXX: If this is not done exactly this way, the module builds as
#      e.g. rbsmartedit.so, but its initializer method will be named
#      'Init_smartedit()' (via the module name set in the SWIG .i file).
#      Which leads to Ruby barfing when it attempts to load the module.
set_target_properties(${_rbsmartedit_target} PROPERTIES
  PREFIX "" OUTPUT_NAME "smartedit")

### Link the new Ruby wrapper library with libsmartedit
target_link_libraries(${_rbsmartedit_target} PUBLIC
    ${RUBY_LIBRARY} smartedit)

######### INSTALL PATH ########
if (NOT DEFINED RUBY_MODULE_PATH AND DEFINED $ENV{RUBY_MODULE_PATH})
  set(RUBY_MODULE_PATH $ENV{RUBY_MODULE_PATH})
endif()

if (NOT DEFINED RUBY_MODULE_PATH)
  if (WIN32 OR APPLE)
    set (RUBY_MODULE_PATH "ruby")
  endif()

  if (UNIX AND NOT APPLE)
    ### FIND THE RUBY INTERPRETER (AND THE LOAD_PATH FOLDER)
    execute_process(COMMAND ${RUBY_EXECUTABLE} -r rbconfig
      -e "dir = RbConfig::CONFIG['vendorarchdir']"
      -e "dir.start_with?(RbConfig::CONFIG['prefix']) && dir.sub!(RbConfig::CONFIG['prefix']+'/', '')"
      -e "p dir"
      OUTPUT_VARIABLE RUBY_MODULE_PATH
      OUTPUT_STRIP_TRAILING_WHITESPACE )
    # Ruby quotes its output strings
    string(REPLACE "\"" "" RUBY_MODULE_PATH "${RUBY_MODULE_PATH}")
  endif()
endif()

message(STATUS "RUBY_MODULE_PATH: ${CMAKE_INSTALL_PREFIX}/${RUBY_MODULE_PATH}")

############### INSTALL HEADERS & LIBRARY ################
# Install Ruby bindings
install(TARGETS ${_rbsmartedit_target}
  DESTINATION ${RUBY_MODULE_PATH} )
