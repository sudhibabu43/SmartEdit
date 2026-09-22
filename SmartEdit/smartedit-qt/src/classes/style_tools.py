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
