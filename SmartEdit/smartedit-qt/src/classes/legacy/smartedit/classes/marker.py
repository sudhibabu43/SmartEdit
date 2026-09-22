class marker:
    """This class represents a marker (i.e. a reference point) on the timeline."""

    
    def __init__(self, marker_name, position, parent):
        """Constructor"""
        self.name = marker_name
        self.position_on_track = float(position)
        self.parent = parent
