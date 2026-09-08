"""
 @file
 @brief This file loads the Animation dialog (i.e about Smartedit Project)
 @author Jonathan Thomas <jonathan@smartedit.org>
 @author Olivier Girard <olivier@smartedit.org>

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

from qt_api import QDialog

from classes import info, ui_util
from classes.app import get_app
from classes.metrics import track_metric_screen


class Animation(QDialog):
    """ Animation Dialog """

    ui_path = os.path.join(info.PATH, 'windows', 'ui', 'animation.ui')

    def __init__(self):
        # Create dialog class
        super().__init__()

        # Load UI from designer
        ui_util.load_ui(self, self.ui_path)

        # Init Ui
        ui_util.init_ui(self)

        # get translations
        self.app = get_app()
        _ = self.app._tr

        # Track metrics
        track_metric_screen("animation-screen")
