import uuid


class SmartEditFile:
    """The generic file object for SmartEdit"""

    
    def __init__(self, project=None):
        """Constructor"""
        self.project = project

        
        self.name = ""  
        self.length = 0.0  
        self.videorate = (30, 0)  
        self.file_type = ""  
        self.max_frames = 0.0
        self.fps = 0.0
        self.height = 0
        self.width = 0
        self.label = ""  
        self.thumb_location = ""  
        self.ttl = 1  

        self.unique_id = str(uuid.uuid1())
        self.parent = None
        self.project = project  

        self.video_codec = ""
        self.audio_codec = ""
        self.audio_frequency = ""
        self.audio_channels = ""


class SmartEditFolder:
    """The generic folder object for SmartEdit"""

    
    def __init__(self, project=None):
        """Constructor"""

        
        self.name = ""  
        self.location = ""  
        self.parent = None
        self.project = project

        self.label = ""  
        self.unique_id = str(uuid.uuid1())

        
        
        
        self.items = []

        
        
        self.queue = []
