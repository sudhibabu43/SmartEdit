class sequence:
    """A sequence contains tracks and clips that make up a scene (aka sequence).  Currently, Smartedit
    only contains a single sequence, but soon it will have the ability to create many sequences."""

    
    def __init__(self, seq_name, project):
        """Constructor"""

        
        self.name = seq_name
        self.length = 600.0  
        self.project = project  
        self.scale = 8.0  
        self.tick_pixels = 100  
        self.play_head_position = 0.0  

        
        self.tracks = []

        
        self.markers = []

        
        self.play_head = None
        self.ruler_time = None
        self.play_head_line = None
        self.enable_animated_playhead = True
