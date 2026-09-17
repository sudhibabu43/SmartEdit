"""
 @file
 @brief This file deals with value conversions
 @author Jonathan Thomas <jonathan@smartedit.org>
 @author Frank Dana <ferdnyc AT gmail com>

 @section 

 Copyright (c) 2008-2018 SmartEdit Studios, LLC
 (http://www.smarteditstudios.com). This file is part of
 SmartEdit Video Editor (http://www.smartedit.org), an open-source project
 dedicated to delivering high quality video editing and animation solutions
 to the world.

 SmartEdit Video Editor is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public  as published by
 the Free Software Foundation, either version 3 of the , or
 (at your option) any later version.

 SmartEdit Video Editor is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public  for more details.

 You should have received a copy of the GNU General Public 
 along with SmartEdit Library.  If not, see <http://www.gnu.org/s/>.
 """

zoomSeconds = [1, 3, 5, 10, 15, 20, 30, 45, 60, 75,
               90, 120, 150, 180, 240, 300, 360, 480, 600, 720,
               900, 1200, 1500, 1800, 2400, 2700, 3600, 4800, 6000, 7200]

def zoomToSeconds(zoomValue):
    """ Convert zoom factor (slider position) into scale-seconds """
    if zoomValue < len(zoomSeconds):
        return zoomSeconds[zoomValue]
    else:
        return zoomSeconds[-1]

def secondsToZoom(scaleValue):
    """ Convert a number of seconds to a timeline zoom factor """
    if scaleValue in zoomSeconds:
        return zoomSeconds.index(scaleValue)
    else:
        
        closestValue = zoomSeconds[0]
        for zoomValue in zoomSeconds:
            if zoomValue < scaleValue:
                closestValue = zoomValue
        return zoomSeconds.index(closestValue)
