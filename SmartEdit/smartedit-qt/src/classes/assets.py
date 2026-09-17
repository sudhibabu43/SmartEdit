"""
 @file
 @brief This file generates the path for a project's assets
 @author Jonathan Thomas <jonathan@smartedit.org>

 @section 

 Copyright (c) 2008-2018 SmartEdit Studios, LLC
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

import os
import shutil
from classes import info
from classes.logger import log


def get_assets_path(file_path=None, create_paths=True):
    """Get and/or create the current assets path. This path is used for thumbnail and blender files,
    and is unique to each project. For example: `Project1.osp` would use `Project1_assets` folder."""
    if not file_path:
        return info.USER_PATH

    
    
    if str(file_path).startswith("content://"):
        return info.USER_PATH

    file_abs = os.path.abspath(str(file_path))
    backup_abs = os.path.abspath(info.BACKUP_FILE)
    recovery_abs = os.path.abspath(info.RECOVERY_PATH) + os.sep
    if file_abs == backup_abs or file_abs.startswith(recovery_abs):
        return info.USER_PATH

    try:
        
        file_path = file_path
        asset_filename = os.path.splitext(os.path.basename(file_path))[0]
        asset_folder_name = asset_filename[:248] + "_assets" 
        asset_path = os.path.join(os.path.dirname(file_path), asset_folder_name)

        
        
        asset_folder_name_30_char = asset_filename[:30] + "_assets"
        asset_path_30_char = os.path.join(os.path.dirname(file_path), asset_folder_name_30_char)

        
        if create_paths:
            if not os.path.exists(asset_path):
                if os.path.exists(asset_path_30_char):
                    
                    
                    try:
                        shutil.copytree(asset_path_30_char, asset_path)
                        log.info("Copying shortened asset folder. {}".format(asset_path))
                    except:
                        log.error("Could not make a copy of assets folder")
                else:
                    os.mkdir(asset_path)
                    log.info("Asset dir created as {}".format(asset_path))
            else:
                log.debug("Using existing asset folder {}".format(asset_path))

            
            asset_thumbnails_folder = os.path.join(asset_path, "thumbnail")
            if not os.path.exists(asset_thumbnails_folder):
                os.mkdir(asset_thumbnails_folder)
                log.info("New thumbnails folder: {}".format(asset_thumbnails_folder))

            
            asset_titles_folder = os.path.join(asset_path, "title")
            if not os.path.exists(asset_titles_folder):
                os.mkdir(asset_titles_folder)
                log.info("New titles folder: {}".format(asset_titles_folder))

            
            asset_blender_folder = os.path.join(asset_path, "blender")
            if not os.path.exists(asset_blender_folder):
                os.mkdir(asset_blender_folder)
                log.info("New blender folder: {}".format(asset_blender_folder))

            
            asset_clipboard_folder = os.path.join(asset_path, "clipboard")
            if not os.path.exists(asset_clipboard_folder):
                os.mkdir(asset_clipboard_folder)
                log.info("New clipboard folder: {}".format(asset_clipboard_folder))

            
            asset_comfy_output_folder = os.path.join(asset_path, "comfyui-output")
            if not os.path.exists(asset_comfy_output_folder):
                os.mkdir(asset_comfy_output_folder)
                log.info("New ComfyUI output folder: {}".format(asset_comfy_output_folder))

            
            asset_protobuf_folder = os.path.join(asset_path, "protobuf_data")
            if not os.path.exists(asset_protobuf_folder):
                os.mkdir(asset_protobuf_folder)
                log.info("New protobuf data folder: {}".format(asset_protobuf_folder))

            
            asset_proxy_folder = os.path.join(asset_path, "optimized")
            if not os.path.exists(asset_proxy_folder):
                os.mkdir(asset_proxy_folder)
                log.info("New optimized folder: {}".format(asset_proxy_folder))

        return asset_path

    except Exception as ex:
        log.error("Error while getting/creating asset folder {}: {}".format(asset_path, ex))
