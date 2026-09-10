"""
 @file
 @brief This file contains the add to timeline model
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

from qt_api import Qt
from qt_api import QStandardItem, QStandardItemModel, QIcon

from classes import info
from classes.logger import log
from classes.app import get_app
from classes.thumbnail import GetThumbPath


class TimelineModel():
    def update_model(self, files=[], clear=True):
        log.info("updating timeline model.")
        app = get_app()

        
        _ = app._tr

        
        if files:
            log.info('set files to %s' % files)
            self.files = files

        
        if clear:
            self.model.clear()

        
        self.model.setHorizontalHeaderLabels([_("Thumb"), _("Name")])

        log.info(self.files)

        for file in self.files:
            
            path, filename = os.path.split(file.data["path"])
            media_type = file.data.get("media_type")

            
            if media_type in ["video", "image"]:
                
                thumbnail_frame = 1
                if 'start' in file.data:
                    fps = file.data["fps"]
                    fps_float = float(fps["num"]) / float(fps["den"])
                    thumbnail_frame = round(float(file.data['start']) * fps_float) + 1

                
                thumb_icon = QIcon(GetThumbPath(file.id, thumbnail_frame))
            else:
                
                thumb_icon = QIcon(os.path.join(info.PATH, "images", "AudioThumbnail.svg"))

            row = []

            
            name = file.data.get("name", filename)

            
            col = QStandardItem()
            col.setIcon(thumb_icon)
            col.setToolTip(filename)
            col.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            row.append(col)

            
            col = QStandardItem("Name")
            col.setData(filename, Qt.DisplayRole)
            col.setText((name[:20] + '...') if len(name) > 15 else name)
            col.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            row.append(col)

            
            self.model.appendRow(row)

            
            app.processEvents()

    def __init__(self, *args):

        
        self.app = get_app()
        self.model = QStandardItemModel()
        self.model.setColumnCount(2)
        self.model_paths = {}
        self.files = []
