from qt_api import QRectF


class TransitionInteractionMixin:
    def _transition_menu_rect(self, rect, tran=None):
        for entry in reversed(getattr(self, "_transition_text_rects", [])):
            entry_tran = entry.get("transition") if isinstance(entry, dict) else None
            entry_rect = entry.get("rect") if isinstance(entry, dict) else None
            if tran is not None and entry_tran is not tran:
                continue
            if isinstance(entry_rect, QRectF):
                return QRectF(entry_rect)
        if not self.transition_painter:
            return QRectF()
        _container_rect, hit_rect, _scaled_arrow, _arrow_rect, _title = self.transition_painter.transition_menu_geometry(rect, tran)
        return hit_rect

    def _trigger_transition_menu_icon(self, pos):
        for rect, tran, _selected in self.geometry.iter_transitions(reverse=True):
            if self._transition_menu_rect(rect, tran).contains(pos) and hasattr(self.win, "timeline"):
                self._select_timeline_item(tran.id, "transition", True)
                self.win.timeline.ShowTransitionMenu(tran.id)
                return True
        return False
