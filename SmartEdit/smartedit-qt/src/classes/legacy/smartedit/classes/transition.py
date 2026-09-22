import uuid


class transition:
    """This class represents a media clip on the timeline."""

    
    def __init__(self, name, position_on_track, length, resource, parent, type="transition", mask_value=50.0):
        """Constructor"""

        
        self.name = name
        self.position_on_track = float(position_on_track)  
        self.length = float(length)  
        self.resource = resource  
        self.softness = 0.3  
        self.reverse = False
        self.unique_id = str(uuid.uuid1())
        self.parent = parent  

        
        self.type = type  
        self.mask_value = mask_value  

        
        self.drag_x = 0.0
        self.drag_y = 0.0
