from qt_api import QRectF
from qt_api import QPainter

from .base import BasePainter


class MarkerPainter(BasePainter):
    def update_theme(self):
        pix = getattr(self.w.theme, "marker_icon", None)
        width = getattr(self.w.theme, "marker_icon_width", 0) or 0
        height = getattr(self.w.theme, "marker_icon_height", 0) or 0
        self.icon_pix = None
        if pix and not pix.isNull():
            self.icon_pix = self.scaled_pixmap(pix, width, height)
        self.icon_width, self.icon_height = self.logical_size(self.icon_pix)

    def paint(self, painter: QPainter):
        self.w.geometry.ensure()
        ruler_area = QRectF(
            self.w.track_name_width,
            0.0,
            self.w.width() - self.w.track_name_width - self.w.scroll_bar_thickness,
            self.w.ruler_height,
        )
        if not self.icon_pix or self.icon_pix.isNull():
            return

        markers = list(self.w.geometry.iter_markers())
        if not markers:
            return

        painter.save()
        painter.setClipRect(ruler_area)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        for mr in markers:
            if not isinstance(mr, dict):
                continue
            icon_rect = mr.get("icon_rect")
            if not icon_rect or icon_rect.isNull():
                continue
            painter.drawPixmap(icon_rect.topLeft(), self.icon_pix)
        painter.restore()
