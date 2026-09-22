import uuid


class track:
    """The track class contains a simple grouping of clips on the same layer (aka track)."""

    
    def __init__(self, track_name, parent_sequence):
        """Constructor"""

        
        self.name = track_name
        self.x = 10  
        self.y_top = 0  
        self.y_bottom = 0  
        self.parent = parent_sequence  
        self.play_video = True
        self.play_audio = True
        self.unique_id = str(uuid.uuid1())

        
        self.clips = []

        
        self.transitions = []
