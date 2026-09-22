from qt_api import QRectF

from classes.query import Track


class TrackGeometryMixin:
    """Populate cached track rectangles and layer lookups."""

    def _build_layer_index(self):
        self.track_list = list(reversed(sorted(Track.filter())))
        layers = {}
        for idx, layer in enumerate(self.track_list):
            layers[layer.data.get("number")] = idx
        return layers

    def _populate_track_rects(self, layers, ctx):
        w = self.widget
        offsets = ctx.get("track_offsets", {})
        heights = ctx.get("track_heights", {})
        self.panel_rects = {}
        track_entries = []
        track_offsets = []
        for track in self.track_list:
            track_num = w.normalize_track_number(track.data.get("number"))
            layer_index = layers.get(track.data.get("number"), 0)
            y = (
                w.ruler_height
                + ctx.get("top_margin", 0.0)
                + offsets.get(track_num, layer_index * ctx["spacing"])
            )
            track_height = heights.get(track_num, w.vertical_factor)
            track_rect = QRectF(
                w.track_name_width,
                y,
                ctx["timeline_w"],
                track_height,
            )
            name_rect = QRectF(0, y, w.track_name_width, track_height)
            track_entries.append((track_rect, track, name_rect))

            panel_height = max(0.0, track_height - w.vertical_factor)
            if panel_height > 0.0:
                panel_rect = QRectF(
                    track_rect.x(),
                    y + w.vertical_factor,
                    track_rect.width(),
                    panel_height,
                )
                self.panel_rects[track_num] = panel_rect
            else:
                self.panel_rects.pop(track_num, None)

            track_offsets.append(y)

        self.track_rects = track_entries
        self._track_offsets = track_offsets

        w.resize_handle_rect = QRectF(
            w.track_name_width - w._resize_handle_width / 2,
            w.ruler_height + ctx.get("top_margin", 0.0),
            w._resize_handle_width,
            max(0.0, ctx["content_h"] - ctx.get("top_margin", 0.0)),
        )
        w.timeline_resize_handle_rect = QRectF()
