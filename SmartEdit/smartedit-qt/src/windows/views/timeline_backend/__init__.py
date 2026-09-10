"""
Timeline backend package helpers.

Ensures legacy ``classes`` imports work when SmartEdit is installed under
the ``smartedit_qt`` package.
"""

import os
import sys

try:
    import classes  
except ImportError:
    
    
    
    checkout_src = os.path.abspath(
        os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir)
    )
    if (
        os.path.isdir(os.path.join(checkout_src, "classes"))
        and checkout_src not in sys.path
    ):
        sys.path.insert(0, checkout_src)

    try:
        import classes  
    except ImportError:
        try:
            import smartedit_qt

            
            pkg_dir = getattr(smartedit_qt, "SMARTEDIT_PATH", None) or os.path.dirname(
                smartedit_qt.__file__
            )
            if pkg_dir and pkg_dir not in sys.path:
                sys.path.insert(0, pkg_dir)

            import classes  
        except Exception:
            
            pass
