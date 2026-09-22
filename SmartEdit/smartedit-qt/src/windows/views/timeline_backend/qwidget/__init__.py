from .base import TimelineWidgetBase, TimelineEvents, _ConditionalTransition
from .clip import ClipInteractionMixin
from .effect import EffectInteractionMixin
from .keyframe import KeyframeMixin
from .keyframe_panel import KeyframePanelMixin
from .playhead import PlayheadMixin
from .track import TrackInteractionMixin
from .transition import TransitionInteractionMixin


class TimelineWidget(
    ClipInteractionMixin,
    TransitionInteractionMixin,
    EffectInteractionMixin,
    TrackInteractionMixin,
    KeyframePanelMixin,
    KeyframeMixin,
    PlayheadMixin,
    TimelineWidgetBase,
):
    """Concrete QWidget timeline implementation."""


__all__ = [
    "TimelineWidget",
    "TimelineWidgetBase",
    "TimelineEvents",
    "_ConditionalTransition",
]
