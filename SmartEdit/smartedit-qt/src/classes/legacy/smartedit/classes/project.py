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

import os
from classes.legacy.smartedit.classes import files


class project():
    """This is the main project class that contains all
    the details of a project, such as name, folder, timeline
    information, sequences, media files, etc..."""

    
    def __init__(self, init_threads=True):
        """Constructor"""

        
        self.DEBUG = True

        
        
        
        
        self.BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.UI_DIR = os.path.join(self.BASE_DIR, "smartedit", "windows", "ui")
        self.IMAGE_DIR = os.path.join(self.BASE_DIR, "smartedit", "images")
        self.LOCALE_DIR = os.path.join(self.BASE_DIR, "smartedit", "locale")
        self.PROFILES_DIR = os.path.join(self.BASE_DIR, "smartedit", "profiles")
        self.TRANSITIONS_DIR = os.path.join(self.BASE_DIR, "smartedit", "transitions")
        self.BLENDER_DIR = os.path.join(self.BASE_DIR, "smartedit", "blender")
        self.EXPORT_PRESETS_DIR = os.path.join(self.BASE_DIR, "smartedit", "export_presets")
        self.EFFECTS_DIR = os.path.join(self.BASE_DIR, "smartedit", "effects")
        
        self.DESKTOP = os.path.join(os.path.expanduser("~"), "Desktop")
        self.USER_DIR = os.path.join(os.path.expanduser("~"), ".smartedit")
        self.THEMES_DIR = os.path.join(self.BASE_DIR, "smartedit", "themes")
        self.USER_PROFILES_DIR = os.path.join(self.USER_DIR, "user_profiles")
        self.USER_TRANSITIONS_DIR = os.path.join(self.USER_DIR, "user_transitions")

        
        self.name = "Default Project"
        self.folder = self.USER_DIR
        self.project_type = None
        self.canvas = None
        self.is_modified = False
        self.refresh_xml = True
        self.mlt_profile = None

        
        self.form = None

        
        self.project_folder = files.SmartEditFolder(self)

        
        self.sequences = []

        
        self.tabs = []
