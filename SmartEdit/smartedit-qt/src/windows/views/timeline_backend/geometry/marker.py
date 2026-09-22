from qt_api import QRectF

from classes.query import Marker


class MarkerGeometryMixin:
    """Populate cached marker rectangles."""

    def _populate_marker_rects(self, ctx):
        w = self.widget
        top_margin = ctx.get("top_margin", 0.0)
        height = max(0.0, ctx["content_h"] - top_margin)
        theme = getattr(w, "theme", None)
        pix = getattr(theme, "marker_icon", None) if theme else None
        icon_w = float(getattr(theme, "marker_icon_width", 0) or 0)
        icon_h = float(getattr(theme, "marker_icon_height", 0) or 0)
        if icon_w <= 0.0 and pix:
            icon_w = float(pix.width())
        if icon_h <= 0.0 and pix:
            icon_h = float(pix.height())
        if icon_w <= 0.0:
            icon_w = 8.0
        if icon_h <= 0.0:
            icon_h = 10.0
        offset_x = getattr(theme, "marker_icon_offset_x", None) if theme else None
        if offset_x is None:
            offset_x = -icon_w / 2.0
        offset_y = getattr(theme, "marker_icon_offset_y", None) if theme else None
        if offset_y is None:
            offset_y = -6.0
        hit_pad = getattr(theme, "marker_hit_padding", 0.0) if theme else 0.0
        try:
            hit_pad = float(hit_pad)
        except (TypeError, ValueError):
            hit_pad = 0.0
        hit_pad = max(0.0, hit_pad)
        for marker in Marker.filter():
            mx = (
                w.track_name_width
                + marker.data.get("position", 0.0) * w.pixels_per_second
            )
            line_rect = QRectF(
                mx,
                w.ruler_height + top_margin,
                0.5,
                height,
            )
            icon_rect = None
            if icon_w > 0.0 and icon_h > 0.0:
                icon_rect = QRectF(
                    mx + offset_x,
                    max(0.0, w.ruler_height - icon_h - offset_y),
                    icon_w,
                    icon_h,
                )
            hit_rect = None
            if icon_rect and not icon_rect.isNull() and hit_pad > 0.0:
                hit_rect = QRectF(icon_rect)
                hit_rect.adjust(-hit_pad, -hit_pad, hit_pad, hit_pad)
            seconds = marker.data.get("position", 0.0)
            try:
                seconds = float(seconds)
            except (TypeError, ValueError):
                seconds = 0.0
            entry = {
                "marker": marker,
                "id": str(getattr(marker, "id", "")),
                "seconds": seconds,
                "line_rect": line_rect,
            }
            if icon_rect:
                entry["icon_rect"] = icon_rect
            if hit_rect:
                entry["hit_rect"] = hit_rect
            self.marker_rects.append(entry)
