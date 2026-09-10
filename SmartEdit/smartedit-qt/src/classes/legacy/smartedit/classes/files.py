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

import uuid


class SmartEditFile:
    """The generic file object for SmartEdit"""

    
    def __init__(self, project=None):
        """Constructor"""
        self.project = project

        
        self.name = ""  
        self.length = 0.0  
        self.videorate = (30, 0)  
        self.file_type = ""  
        self.max_frames = 0.0
        self.fps = 0.0
        self.height = 0
        self.width = 0
        self.label = ""  
        self.thumb_location = ""  
        self.ttl = 1  

        self.unique_id = str(uuid.uuid1())
        self.parent = None
        self.project = project  

        self.video_codec = ""
        self.audio_codec = ""
        self.audio_frequency = ""
        self.audio_channels = ""


class SmartEditFolder:
    """The generic folder object for SmartEdit"""

    
    def __init__(self, project=None):
        """Constructor"""

        
        self.name = ""  
        self.location = ""  
        self.parent = None
        self.project = project

        self.label = ""  
        self.unique_id = str(uuid.uuid1())

        
        
        
        self.items = []

        
        
        self.queue = []
