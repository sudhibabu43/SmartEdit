"""
 @file
 @brief Geometry helpers split into focused mixins.
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
