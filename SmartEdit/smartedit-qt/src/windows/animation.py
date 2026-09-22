import os

from qt_api import QDialog

from classes import info, ui_util
from classes.app import get_app
from classes.metrics import track_metric_screen


class Animation(QDialog):
    """ Animation Dialog """

    ui_path = os.path.join(info.PATH, 'windows', 'ui', 'animation.ui')

    def __init__(self):
        
        super().__init__()

        
        ui_util.load_ui(self, self.ui_path)

        
        ui_util.init_ui(self)

        
        self.app = get_app()
        _ = self.app._tr

        
        track_metric_screen("animation-screen")
