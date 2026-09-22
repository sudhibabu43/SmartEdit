def is_image(file_object):
    """Check a File object if the file extension is a known image format"""
    path = file_object["path"].lower()
    img_file_extensions = (
        ".bmp",
        ".dpx",
        ".exr",
        ".jpg",
        ".jpeg",
        ".pam",
        ".pbm",
        ".pcx",
        ".pgm",
        ".png",
        ".pnm",
        ".ppm",
        ".psd",
        ".sgi",
        ".svg",
        ".tga",
        ".thm",
        ".tif",
        ".tiff",
        ".webp",
        ".xbm",
        ".xpm",
        ".xwd",
    )
    return path.endswith(img_file_extensions)

def get_media_type(file_object):
    """Check a File object and determine the media type (video, image, audio)"""
    if file_object["has_video"] and not is_image(file_object):
        return "video"
    elif file_object["has_video"] and is_image(file_object):
        return "image"
    elif file_object["has_audio"] and not file_object["has_video"]:
        return "audio"
    else:
        
        return "video"
