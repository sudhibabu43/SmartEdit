"""
 @file
 @brief This file converts project data from one FPS to a new FPS (adjusting precisions, trims, and positions)
 @author Jonathan Thomas <jonathan@smartedit.org>

 @section 

 Copyright (c) 2008-2024 SmartEdit Studios, LLC
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


def remove_gaps(clips, new_profile):
    project_fps_num = new_profile.info.fps.num
    project_fps_den = new_profile.info.fps.den
    FRAME_DURATION = project_fps_den / project_fps_num  

    
    max_gap_tolerance = 3 * FRAME_DURATION
    min_gap_tolerance = 1 / 10000  

    def snap_to_new_fps_grid(time_in_seconds):
        
        return round(time_in_seconds / FRAME_DURATION) * FRAME_DURATION

    
    clips.sort(key=lambda x: x['position'])

    
    for i in range(1, len(clips)):
        current_clip = clips[i]
        previous_clip = clips[i - 1]
        if 'start' not in current_clip or 'start' not in previous_clip:
            continue
        if 'end' not in current_clip or 'end' not in previous_clip:
            continue

        
        previous_clip_right_edge = snap_to_new_fps_grid(previous_clip['position'] + (previous_clip['end'] - previous_clip['start']))

        
        gap = current_clip['position'] - previous_clip_right_edge

        
        if min_gap_tolerance < abs(gap) < max_gap_tolerance:
            
            previous_clip['end'] += gap  

        
        previous_clip['end'] = snap_to_new_fps_grid(previous_clip['end'])

    return clips

def change_profile(clips, new_profile):
    """Adjust all clip-like objects to use project FPS precision, adjusting 'end' trim
    (if needed) to close any tiny (1 to 3 frame) gaps."""
    project_fps_num = new_profile.info.fps.num
    project_fps_den = new_profile.info.fps.den

    def snap_to_new_fps_grid(time_in_seconds):
        frame_time = project_fps_den / project_fps_num
        return round(time_in_seconds / frame_time) * frame_time

    for clip in clips:
        
        clip['position'] = snap_to_new_fps_grid(clip['position'])
        if 'start' in clip:
            clip['start'] = snap_to_new_fps_grid(clip['start'])
        if 'end' in clip:
            clip['end'] = snap_to_new_fps_grid(clip['end'])

    
    return remove_gaps(clips, new_profile)
