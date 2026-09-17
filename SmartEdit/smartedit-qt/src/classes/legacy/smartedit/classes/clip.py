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
from classes.legacy.smartedit.classes import keyframe


class clip:
    """This class represents a media clip on the timeline."""

    
    def __init__(self, clip_name, color, position_on_track, start_time, end_time, parent_track, file_object):
        """Constructor"""

        
        self.name = clip_name  
        self.color = color  
        self.start_time = start_time  
        self.end_time = end_time  
        self.speed = 1.0  
        self.max_length = 0.0  
        self.position_on_track = float(
            position_on_track)  
        self.play_video = True
        self.play_audio = True
        self.fill = True
        self.distort = False
        self.composite = True
        self.halign = "centre"
        self.valign = "centre"
        self.reversed = False
        self.volume = 100.0
        self.audio_fade_in = False
        self.audio_fade_out = False
        self.audio_fade_in_amount = 2.0
        self.audio_fade_out_amount = 2.0
        self.video_fade_in = False
        self.video_fade_out = False
        self.video_fade_in_amount = 2.0
        self.video_fade_out_amount = 2.0
        self.parent = parent_track  
        self.file_object = file_object  
        self.unique_id = str(uuid.uuid1())
        self.rotation = 0.0
        self.thumb_location = ""

        
        self.keyframes = {"start": keyframe(0, 100.0, 100.0, 0.0, 0.0, 1.0),
                          "end": keyframe(-1, 100.0, 100.0, 0.0, 0.0, 1.0)}

        
        self.effects = []

        
        self.drag_x = 0.0
        self.drag_y = 0.0
        self.moved = False
        self.is_timeline_scrolling = False
