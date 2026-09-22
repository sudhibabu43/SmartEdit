import uuid


class effect:
    """This class represents a media clip on the timeline."""

    
    def __init__(self, service, paramaters=[]):
        """Constructor"""

        
        self.service = service  
        self.paramaters = paramaters  
        self.audio_effect = ""
        self.unique_id = str(uuid.uuid1())
