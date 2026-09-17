###
# @file
# @brief CMake EXPORTED configuration for SmartEditAudio
# @author FeRD (Frank Dana) <ferdnyc@gmail.com>
#
# Copyright (c) 2008-2020 SmartEdit Studios, LLC
# <http://www.smarteditstudios.com/>. This file is part of
# SmartEdit Audio Library (libsmartedit-audio), an open-source project dedicated
# to delivering high quality audio editing and playback solutions to the
# world. For more information visit <http://www.smartedit.org/>.
#
# SmartEdit Audio Library (libsmartedit-audio) is free software: you can
# redistribute it and/or modify it under the terms of the GNU General Public
#  as published by the Free Software Foundation, either version 3 of the
# , or (at your option) any later version.
#
# SmartEdit Audio Library (libsmartedit-audio) is distributed in the hope that it
# will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty
# of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
# Public  for more details.
#
# You should have received a copy of the GNU General Public 
# along with SmartEdit Audio Library. If not, see <http://www.gnu.org/s/>.
################################################################################


####### Expanded from @PACKAGE_INIT@ by configure_package_config_file() #######
####### Any changes to this file will be overwritten by the next CMake run ####
####### The input file was Config.cmake.in                            ########

get_filename_component(PACKAGE_PREFIX_DIR "${CMAKE_CURRENT_LIST_DIR}/../../../" ABSOLUTE)

macro(set_and_check _var _file)
  set(${_var} "${_file}")
  if(NOT EXISTS "${_file}")
    message(FATAL_ERROR "File or directory ${_file} referenced by variable ${_var} does not exist !")
  endif()
endmacro()

macro(check_required_components _NAME)
  foreach(comp ${${_NAME}_FIND_COMPONENTS})
    if(NOT ${_NAME}_${comp}_FOUND)
      if(${_NAME}_FIND_REQUIRED_${comp})
        set(${_NAME}_FOUND FALSE)
      endif()
    endif()
  endforeach()
endmacro()

####################################################################################

include(CMakeFindDependencyMacro)

if(FALSE)
  list(APPEND CMAKE_MODULE_PATH ${CMAKE_CURRENT_LIST_DIR})
  find_dependency(ASIO)
endif()

if(FALSE)
  find_dependency(ALSA)
  if (ALSA_FOUND AND NOT TARGET ALSA::ALSA)  # CMake < 3.12
    add_library(ALSA::ALSA INTERFACE IMPORTED)
    set_target_properties(ALSA::ALSA PROPERTIES
      INTERFACE_INCLUDE_DIRECTORIES ${ALSA_INCLUDE_DIR}
      INTERFACE_LINK_LIBRARIES ${ALSA_LIBRARIES}
    )
  endif()
endif()

find_dependency(ZLIB)

include("${CMAKE_CURRENT_LIST_DIR}/SmartEditAudioTargets.cmake")

check_required_components(SmartEditAudio)
