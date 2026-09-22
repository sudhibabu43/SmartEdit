zoomSeconds = [1, 3, 5, 10, 15, 20, 30, 45, 60, 75,
               90, 120, 150, 180, 240, 300, 360, 480, 600, 720,
               900, 1200, 1500, 1800, 2400, 2700, 3600, 4800, 6000, 7200]

def zoomToSeconds(zoomValue):
    """ Convert zoom factor (slider position) into scale-seconds """
    if zoomValue < len(zoomSeconds):
        return zoomSeconds[zoomValue]
    else:
        return zoomSeconds[-1]

def secondsToZoom(scaleValue):
    """ Convert a number of seconds to a timeline zoom factor """
    if scaleValue in zoomSeconds:
        return zoomSeconds.index(scaleValue)
    else:
        
        closestValue = zoomSeconds[0]
        for zoomValue in zoomSeconds:
            if zoomValue < scaleValue:
                closestValue = zoomValue
        return zoomSeconds.index(closestValue)
