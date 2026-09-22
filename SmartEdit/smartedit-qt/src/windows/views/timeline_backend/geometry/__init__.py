from .base import GeometryBase
from .clip import ClipGeometryMixin
from .marker import MarkerGeometryMixin
from .track import TrackGeometryMixin
from .transition import TransitionGeometryMixin


class Geometry(
    MarkerGeometryMixin,
    TransitionGeometryMixin,
    ClipGeometryMixin,
    TrackGeometryMixin,
    GeometryBase,
):
    """Concrete geometry helper combining all mixins."""


__all__ = ["Geometry"]
