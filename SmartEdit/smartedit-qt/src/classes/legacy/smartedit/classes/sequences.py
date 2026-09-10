"""
 @file
 @brief This file is for legacy support of SmartEdit 1.x project files
 @author Jonathan Thomas <jonathan@smartedit.org>

 @section LICENSE

 Copyright (c) 2008-2018 SmartEdit Studios, LLC
 (http://www.smarteditstudios.com). This file is part of
 SmartEdit Video Editor (http://www.smartedit.org), an open-source project
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
 """


class sequence:
    """A sequence contains tracks and clips that make up a scene (aka sequence).  Currently, Smartedit
    only contains a single sequence, but soon it will have the ability to create many sequences."""

    
    def __init__(self, seq_name, project):
        """Constructor"""

        
        self.name = seq_name
        self.length = 600.0  
        self.project = project  
        self.scale = 8.0  
        self.tick_pixels = 100  
        self.play_head_position = 0.0  

        
        self.tracks = []

        
        self.markers = []

        
        self.play_head = None
        self.ruler_time = None
        self.play_head_line = None
        self.enable_animated_playhead = True
