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
