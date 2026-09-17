"""
 @file
 @brief Painter for the timeline background gradient.
 @author Jonathan Thomas <jonathan@smartedit.org>

 @section 

 Copyright (c) 2008-2025 SmartEdit Studios, LLC
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

from qt_api import QPointF, QRectF
from qt_api import QBrush, QColor, QLinearGradient, QPainter

from .base import BasePainter


class BackgroundPainter(BasePainter):
    def paint(self, painter: QPainter, rect: QRectF):
        bg = self.w.theme.background
        bg2 = getattr(self.w.theme, "background2", QColor())
        if bg2.isValid() and bg2 != bg:
            grad = QLinearGradient(QPointF(rect.topLeft()), QPointF(rect.bottomLeft()))
            grad.setColorAt(0, bg)
            grad.setColorAt(1, bg2)
            painter.fillRect(rect, QBrush(grad))
        else:
            painter.fillRect(rect, bg)
