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
