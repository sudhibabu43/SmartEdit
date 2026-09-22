from qt_api import QRectF
from qt_api import QColor, QPainter, QPainterPath, QPen, Qt

from .base import BasePainter


class KeyframePainter(BasePainter):
    def update_theme(self):
        fill = self.w.theme.keyframe_fill
        border = self.w.theme.keyframe_border
        base_color = QColor("#4d7bff")
        if fill.isValid():
            base_color = QColor(fill)
        self.fill = base_color
        border_color = QColor("#ffffff")
        if border.isValid():
            border_color = QColor(border)
        self.border = border_color
        self.pen = QPen(self.border, 1.2)
        self.pen.setCosmetic(True)
        self.inactive_opacity = getattr(self.w.theme, "keyframe_inactive_opacity", 0.5)
        self.size = max(1, int(getattr(self.w.theme, "keyframe_size", 10) or 10))

    def paint(self, painter: QPainter):
        markers = getattr(self.w, "_keyframe_markers", [])
        if not markers:
            return

        content_area = QRectF(
            self.w.track_name_width,
            self.w.ruler_height,
            self.w.width() - self.w.track_name_width - self.w.scroll_bar_thickness,
            self.w.height() - self.w.ruler_height - self.w.scroll_bar_thickness,
        )

        painter.save()
        painter.setClipRect(content_area, Qt.IntersectClip)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setPen(self.pen)
        for marker in markers:
            rect = marker.get("rect")
            if not isinstance(rect, QRectF) or rect.isNull():
                continue
            opacity = 1.0 if marker.get("selected") else self.inactive_opacity
            if marker.get("dimmed"):
                opacity *= 0.5
            painter.setOpacity(opacity)
            color = marker.get("color")
            if not isinstance(color, QColor) or not color.isValid():
                color = self.fill
            painter.setBrush(color)
            interpolation = marker.get("interpolation", "bezier")
            if interpolation == "linear":
                painter.drawRect(rect)
            elif interpolation == "constant":
                path = QPainterPath()
                center = rect.center()
                path.moveTo(center.x(), rect.top())
                path.lineTo(rect.right(), center.y())
                path.lineTo(center.x(), rect.bottom())
                path.lineTo(rect.left(), center.y())
                path.closeSubpath()
                painter.drawPath(path)
            else:
                painter.drawEllipse(rect)
        painter.restore()
