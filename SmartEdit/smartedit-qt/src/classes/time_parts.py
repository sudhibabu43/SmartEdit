import math


def padNumber(value, pad_length):
    """Pad number a specific # of characters"""
    format_mask = '%%0%sd' % pad_length
    return format_mask % value


def secondsToTime(secs, fps_num=30, fps_den=1):
    """Convert # of seconds (float) to parts of time (dict)"""
    milliseconds = secs * 1000
    sec = math.floor(milliseconds / 1000)
    milli = milliseconds % 1000
    minute = math.floor(sec / 60)
    sec = sec % 60
    hour = math.floor(minute / 60)
    minute = minute % 60
    day = math.floor(hour / 24)
    hour = hour % 24
    week = math.floor(day / 7)
    day = day % 7

    fps_float = (float(fps_num) / float(fps_den)) if fps_den else 0.0
    frame = int(round((milli / 1000.0) * fps_float))
    if fps_float > 0:
        frame = max(0, min(frame, int(fps_float) - 1))
    return {"week": padNumber(week, 2), "day": padNumber(day, 2), "hour": padNumber(hour, 2),
            "min": padNumber(minute, 2), "sec": padNumber(sec, 2), "milli": padNumber(milli, 3),
            "frame": padNumber(frame, 2)}

def timecodeToSeconds(time_code="00:00:00:00", fps_num=30, fps_den=1):
    """Convert time code to seconds (float)"""
    fps_float = float(fps_num / fps_den)

    seconds = 0.0
    time_parts = time_code.split(":")
    if len(time_parts) == 4:
        hours = float(time_parts[0])
        mins = float(time_parts[1])
        secs = float(time_parts[2])
        frames = float(time_parts[3])
        seconds = (hours * 60 * 60) + (mins * 60) + secs + (frames / fps_float)
    return seconds

def secondsToTimecode(time_in_seconds=0.0, fps_num=30, fps_den=1, use_milliseconds=False):
    """Return a formatted time code HH:MM:SS:FRAME"""
    if use_milliseconds:
        return "%(hour)s:%(min)s:%(sec)s:%(milli)s" % secondsToTime(time_in_seconds, fps_num, fps_den)
    return "%(hour)s:%(min)s:%(sec)s:%(frame)s" % secondsToTime(time_in_seconds, fps_num, fps_den)
