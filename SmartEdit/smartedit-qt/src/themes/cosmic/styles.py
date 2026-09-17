"""
Cosmic Dusk timeline theme class for SmartEdit.
"""

from qt_api import QColor
from windows.views.timeline_backend.theme import TimelineTheme, _icon

class CosmicDuskTimelineTheme(TimelineTheme):
    """Cosmic Dusk timeline theme."""

    def __init__(self):
        super().__init__()

        # Cosmic custom settings + Humanity base settings
        self.background             = QColor("#121212")
        self.background2            = QColor()
        self.playhead_color         = QColor("#FABE0A")
        self.playhead_width         = 2.0
        self.clip_selected          = QColor("#FF0000")
        self.selection              = QColor(42, 130, 218, 102)
        self.selection_border       = QColor(42, 130, 218, 102)
        self.selection_border_width = 1.0
        self.playback_cache_color   = QColor("#4B92AD")
        self.playback_cache_height  = 5.0
        self.ruler_name_background  = QColor("#121212")
        self.ruler_name_background2 = QColor()
        self.ruler_time_font_size   = 13
        self.ruler_time_pad_left    = 17
        self.ruler_time_pad_top     = 12
        self.ruler_label_top        = 6
        self.scrollbar_handle       = QColor("#4B92AD")
        self.scrollbar_track        = QColor("#121212")
        self.scrollbar_width        = 8
        self.waveform_color         = QColor("#2A82DA")
        self.waveform_peak_color    = QColor(42, 130, 218, 128)
        self.keyframe_fill          = QColor("#4D7BFF")
        self.keyframe_border        = QColor("#FFFFFF")
        self.keyframe_inactive_opacity       = 0.5
        self.keyframe_size                   = 10
        self.keyframe_panel_property_bg      = QColor()
        self.keyframe_panel_row_border_color = QColor()
        self.keyframe_panel_row_border_width = 0.0
        self.keyframe_panel_curve_color      = QColor()
        self.keyframe_panel_marker_fill      = QColor()
        self.keyframe_panel_marker_border    = QColor()

        # Clip properties
        self.clip.background    = QColor("#1e1e1e")
        self.clip.background2   = QColor()
        self.clip.top_overlay   = QColor(255, 255, 255, 51)
        self.clip.top_overlay2  = QColor(255, 255, 255, 0)
        self.clip.border_color  = QColor("#0078FF")
        self.clip.border_radius = 8
        self.clip.border_width  = 2.0
        self.clip.font_color    = QColor("#FFFFFF")
        self.clip.font_size     = 9
        self.clip.height        = 48
        self.clip.shadow_color  = QColor("#000000")
        self.clip.shadow_blur   = 10

        # Track properties
        self.track.background               = QColor("#252526")
        self.track.background2              = QColor()
        self.track.border_color             = QColor("#252526")
        self.track.border_radius            = 0
        self.track.height                   = 48
        self.track.gap                      = 8
        self.track.margin_top               = -1
        self.track.font_color               = QColor("#FFFFFF")
        self.track.font_size                = 9
        self.track.name_background          = QColor("#1e1e1e")
        self.track.name_width               = 140
        self.track.name_border_color        = QColor("#0078FF")
        self.track.name_border_width        = 4
        self.track.name_border_top_color    = QColor("#1e1e1e")
        self.track.name_border_top_width    = 1
        self.track.name_border_bottom_color = QColor("#1e1e1e")
        self.track.name_border_bottom_width = 1
        self.track.name_radius_tl           = 0
        self.track.name_radius_bl           = 0
        self.track.name_top_overlay         = QColor(255, 255, 255, 51)
        self.track.name_top_overlay2        = QColor(255, 255, 255, 0)

        # Transition properties
        self.transition.background       = QColor("#0192C1")
        self.transition.background2      = QColor("#3FA1BF")
        self.transition.border_color     = QColor("#0192C1")
        self.transition.border_radius    = 8
        self.transition.border_width     = 2.0
        self.transition.font_color       = QColor("#FFFFFF")
        self.transition.font_size        = 9
        self.transition.height           = 48
        self.transition.background_image = _icon("themes/cosmic/images/transition.svg")

        # Ruler properties
        self.ruler.background   = QColor("#121212")
        self.ruler.background2  = QColor()
        self.ruler.border_color = QColor("#ACACAC")
        self.ruler.font_color   = QColor("#999999")
        self.ruler.font_size    = 10
        self.ruler.height       = 39

        # Icons and sizes
        _c = "themes/cosmic/images/"
        self.menu_size               = 12
        self.menu_margin             = 4
        self.playhead_icon           = _icon(_c + "playhead.svg")
        self.playhead_icon_width     = 12
        self.playhead_icon_height    = 188
        self.playhead_icon_offset_x  = -6
        self.playhead_icon_offset_y  = 20
        self.marker_icon             = _icon(_c + "marker.svg")
        self.marker_icon_width       = 8
        self.marker_icon_height      = 10
        self.marker_icon_offset_x    = -4
        self.marker_icon_offset_y    = 0

        self.track_keyframe_panel_disabled_icon = _icon(_c + "track-keyframe-panel-show-disabled.svg")
        self.track_keyframe_panel_enabled_icon  = _icon(_c + "track-keyframe-panel-show-enabled.svg")
        self.keyframe_panel_add_icon            = _icon(_c + "keyframe-panel-add.svg")
        self.track_add_above_disabled_icon      = _icon(_c + "track-add-above-disabled.svg")
        self.track_add_above_enabled_icon       = _icon(_c + "track-add-above-enabled.svg")
        self.track_add_below_disabled_icon      = _icon(_c + "track-add-below-disabled.svg")
        self.track_add_below_enabled_icon       = _icon(_c + "track-add-below-enabled.svg")
        self.track_delete_disabled_icon         = _icon(_c + "track-delete-disabled.svg")
        self.track_delete_enabled_icon          = _icon(_c + "track-delete-enabled.svg")
        self.track_locked_disabled_icon         = _icon(_c + "track-locked-disabled.svg")
        self.track_locked_enabled_icon          = _icon(_c + "track-locked-enabled.svg")
        self.track_unlocked_disabled_icon       = _icon(_c + "track-unlocked-disabled.svg")
        self.track_unlocked_enabled_icon        = _icon(_c + "track-unlocked-enabled.svg")

        self.keyframe_toggle_off_icon = self.track_keyframe_panel_disabled_icon
        self.keyframe_toggle_on_icon  = self.track_keyframe_panel_enabled_icon
