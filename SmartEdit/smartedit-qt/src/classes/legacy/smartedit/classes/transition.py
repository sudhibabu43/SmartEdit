"""
 @file
 @brief This file is for legacy support of SmartEdit 1.x project files
 @author Jonathan Thomas <jonathan@smartedit.org>

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

import uuid


class transition:
    """This class represents a media clip on the timeline."""

    
    def __init__(self, name, position_on_track, length, resource, parent, type="transition", mask_value=50.0):
        """Constructor"""

        
        self.name = name
        self.position_on_track = float(position_on_track)  
        self.length = float(length)  
        self.resource = resource  
        self.softness = 0.3  
        self.reverse = False
        self.unique_id = str(uuid.uuid1())
        self.parent = parent  

        
        self.type = type  
        self.mask_value = mask_value  

        
        self.drag_x = 0.0
        self.drag_y = 0.0
