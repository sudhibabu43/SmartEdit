











import os as _os
import sys as _sys

_PKG_DIR = _os.path.dirname(_os.path.abspath(__file__))
_SRC_DIR = _os.path.dirname(_PKG_DIR)


if _SRC_DIR not in _sys.path:
    _sys.path.insert(0, _SRC_DIR)

if _os.name == "nt":
    for _src_name, _dst_name in [
        ("libsmartedit.dll", "libsmartedit.dll"),
        ("libsmartedit-audio.dll", "libsmartedit-audio.dll"),
        ("_smartedit.pyd", "_openshot.pyd"),
    ]:
        _s = _os.path.join(_SRC_DIR, _src_name)
        _d = _os.path.join(_SRC_DIR, _dst_name)
        if _os.path.exists(_s) and not _os.path.exists(_d):
            try:
                import shutil
                shutil.copyfile(_s, _d)
            except Exception:
                pass

if _os.name == "nt" and hasattr(_os, "add_dll_directory"):
    for _dll_dir in (_SRC_DIR, r"C:\msys64\ucrt64\bin"):
        if _os.path.isdir(_dll_dir):
            try:
                _os.add_dll_directory(_dll_dir)
            except Exception:
                pass
    if r"C:\msys64\ucrt64\bin" not in _os.environ.get("PATH", ""):
        _os.environ["PATH"] = r"C:\msys64\ucrt64\bin;" + _os.environ.get("PATH", "")


import _libsmartedit as _swig_mod


_THIS = _sys.modules[__name__]
for _name in dir(_swig_mod):
    if _name.startswith("__") and _name.endswith("__"):
        if _name in ("__file__", "__loader__", "__name__", "__package__",
                     "__spec__", "__path__", "__cached__", "__builtins__"):
            continue
    if hasattr(_THIS, _name):
        continue
    try:
        setattr(_THIS, _name, getattr(_swig_mod, _name))
    except Exception:
        pass


if not hasattr(_THIS, "_smartedit"):
    _ext = getattr(_swig_mod, "_smartedit", None)
    if _ext is not None:
        _THIS._smartedit = _ext
        if "_smartedit" not in _sys.modules:
            _sys.modules["_smartedit"] = _ext


_sys.modules.setdefault("smartedit_swig", _swig_mod)


from .video_analysis import VideoAnalyzer
from .audio_analysis import AudioAnalyzer
from .prompt_interpreter import PromptInterpreter
from .rough_cut_generator import RoughCutGenerator
