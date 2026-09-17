"""
 @file
 @brief Utility functions for manipulating SVG style attributes
 @author FeRD (Frank Dana) <ferdnyc@gmail.com>

 @section 

 Copyright (c) 2008-2020 SmartEdit Studios, LLC
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

from classes.logger import log


def style_to_dict(style: str) -> dict:
    """Explode an SVG node style= attribute string into a dict representation"""
    styledict = {}
    try:
        
        styledict.update(
            
            (a.split(':', 1))
            
            for a in style.split(';')
            
            if a
            )
        return styledict
    except ValueError as ex:
        log.error(
            "style_to_dict failed to convert to dict: %s\n%s",
            ex, style)


def dict_to_style(styledict: dict) -> str:
    """Turn an exploded style dictionary back into a string"""
    
    try:
        style = ";".join([
            
            ":".join([k, v])
            
            for k, v in styledict.items()
            ])
        
        return style + ';'
    except ValueError as ex:
        import json
        log.error(
            "style_to_dict failed to generate string: %s\n%s",
            ex, json.dumps(styledict))


def set_if_existing(d: dict, existing_key, new_value):
    if existing_key in d:
        d.update({existing_key: new_value})
