from qt_api import QRectF, Qt
from qt_api import QPainter, QPen

from .base import BasePainter


class SelectionPainter(BasePainter):
    def update_theme(self):
        bw = self.w.theme.selection_border_width
        col = (
            self.w.theme.selection_border
            if self.w.theme.selection_border.isValid()
            else self.w.theme.selection
        )
        self.pen = QPen(col, bw, Qt.SolidLine)
        self.pen.setCosmetic(True)

    def paint(self, painter: QPainter):
        if not self.w.selection_rect.isNull():
            area = QRectF(
                0.0,
                self.w.ruler_height,
                self.w.width() - self.w.scroll_bar_thickness,
                self.w.height() - self.w.ruler_height - self.w.scroll_bar_thickness,
            )
            painter.save()
            vis = self.w.selection_rect.intersected(area)
            if not vis.isNull():
                if self.w.theme.selection.isValid():
                    painter.fillRect(vis, self.w.theme.selection)
                if self.pen.color().isValid() and self.pen.widthF() > 0:
                    painter.setPen(self.pen)
                    painter.drawRect(vis)
            painter.restore()
