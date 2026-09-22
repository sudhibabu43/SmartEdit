from enum import Enum, auto


class MenuFade(Enum):
    NONE = 0
    IN_FAST = auto()
    IN_SLOW = auto()
    OUT_FAST = auto()
    OUT_SLOW = auto()
    IN_OUT_FAST = auto()
    IN_OUT_SLOW = auto()


class MenuRotate(Enum):
    NONE = 0
    RIGHT_90 = auto()
    LEFT_90 = auto()
    FLIP_180 = auto()


class MenuLayout(Enum):
    NONE = 0
    CENTER = auto()
    TOP_LEFT = auto()
    TOP_RIGHT = auto()
    BOTTOM_LEFT = auto()
    BOTTOM_RIGHT = auto()
    ALL_WITH_ASPECT = auto()
    ALL_WITHOUT_ASPECT = auto()


class MenuAlign(Enum):
    LEFT = 0
    RIGHT = auto()


class MenuAnimate(Enum):
    NONE = 0
    
    SLIDE_IN_LEFT = auto()
    SLIDE_IN_RIGHT = auto()
    SLIDE_IN_TOP = auto()
    SLIDE_IN_BOTTOM = auto()
    BLUR_IN = auto()
    WIPE_IN_CIRCLE_EXPAND = auto()
    WIPE_IN_CIRCLE_SHRINK = auto()
    WIPE_IN_FADE = auto()
    WIPE_IN_LEFT = auto()
    WIPE_IN_RIGHT = auto()
    WIPE_IN_TOP = auto()
    WIPE_IN_BOTTOM = auto()
    FOCUS_WIPE_IN_CIRCLE_EXPAND = auto()
    FOCUS_WIPE_IN_CIRCLE_SHRINK = auto()
    FOCUS_WIPE_IN_LEFT = auto()
    FOCUS_WIPE_IN_RIGHT = auto()
    FOCUS_WIPE_IN_TOP = auto()
    FOCUS_WIPE_IN_BOTTOM = auto()
    POP_IN = auto()
    SPIRAL_IN = auto()
    BACK_IN_DOWN = auto()
    BACK_IN_LEFT = auto()
    BACK_IN_RIGHT = auto()
    BACK_IN_UP = auto()
    BOUNCE_IN = auto()
    BOUNCE_IN_DOWN = auto()
    BOUNCE_IN_LEFT = auto()
    BOUNCE_IN_RIGHT = auto()
    BOUNCE_IN_UP = auto()
    
    SLIDE_OUT_LEFT = auto()
    SLIDE_OUT_RIGHT = auto()
    SLIDE_OUT_TOP = auto()
    SLIDE_OUT_BOTTOM = auto()
    BLUR_OUT = auto()
    WIPE_OUT_CIRCLE_EXPAND = auto()
    WIPE_OUT_CIRCLE_SHRINK = auto()
    WIPE_OUT_FADE = auto()
    WIPE_OUT_LEFT = auto()
    WIPE_OUT_RIGHT = auto()
    WIPE_OUT_TOP = auto()
    WIPE_OUT_BOTTOM = auto()
    FOCUS_WIPE_OUT_CIRCLE_EXPAND = auto()
    FOCUS_WIPE_OUT_CIRCLE_SHRINK = auto()
    FOCUS_WIPE_OUT_LEFT = auto()
    FOCUS_WIPE_OUT_RIGHT = auto()
    FOCUS_WIPE_OUT_TOP = auto()
    FOCUS_WIPE_OUT_BOTTOM = auto()
    POP_OUT = auto()
    SPIRAL_OUT = auto()
    BACK_OUT_DOWN = auto()
    BACK_OUT_LEFT = auto()
    BACK_OUT_RIGHT = auto()
    BACK_OUT_UP = auto()
    BOUNCE_OUT = auto()
    BOUNCE_OUT_DOWN = auto()
    BOUNCE_OUT_LEFT = auto()
    BOUNCE_OUT_RIGHT = auto()
    BOUNCE_OUT_UP = auto()
    
    BOUNCE = auto()
    FLASH = auto()
    PULSE = auto()
    RUBBER_BAND = auto()
    SHAKE_X = auto()
    SHAKE_Y = auto()
    SWING = auto()
    TADA = auto()
    WOBBLE = auto()
    JELLO = auto()
    HEART_BEAT = auto()
    
    CAM_PUSH_IN = auto()
    CAM_PULL_OUT = auto()
    CAM_PAN_AUTO = auto()
    CAM_PAN_LEFT = auto()
    CAM_PAN_RIGHT = auto()
    CAM_PAN_UP = auto()
    CAM_PAN_DOWN = auto()
    KEN_BURNS_IN = auto()
    KEN_BURNS_OUT = auto()
    KEN_BURNS_IN_LEFT_TO_RIGHT = auto()
    KEN_BURNS_IN_RIGHT_TO_LEFT = auto()
    KEN_BURNS_IN_TOP_TO_BOTTOM = auto()
    KEN_BURNS_IN_BOTTOM_TO_TOP = auto()
    KEN_BURNS_OUT_LEFT_TO_RIGHT = auto()
    KEN_BURNS_OUT_RIGHT_TO_LEFT = auto()
    KEN_BURNS_OUT_TOP_TO_BOTTOM = auto()
    KEN_BURNS_OUT_BOTTOM_TO_TOP = auto()
    
    CREDITS_UP = auto()
    CREDITS_DOWN = auto()


class MenuVolume(Enum):
    NONE = 1
    FADE_IN_FAST = auto()
    FADE_IN_SLOW = auto()
    FADE_OUT_FAST = auto()
    FADE_OUT_SLOW = auto()
    FADE_IN_OUT_FAST = auto()
    FADE_IN_OUT_SLOW = auto()
    LEVEL = auto()


class MenuTime(Enum):
    NONE = 0
    FORWARD = auto()
    BACKWARD = auto()
    REVERSE = auto()
    FREEZE = auto()
    FREEZE_ZOOM = auto()


class MenuCopy(Enum):
    ALL = -1
    CLIP = 0
    KEYFRAMES_ALL = auto()
    KEYFRAMES_ALPHA = auto()
    KEYFRAMES_SCALE = auto()
    KEYFRAMES_SHEAR = auto()
    KEYFRAMES_ROTATE = auto()
    KEYFRAMES_LOCATION = auto()
    KEYFRAMES_TIME = auto()
    KEYFRAMES_VOLUME = auto()
    EFFECT = auto()
    ALL_EFFECTS = auto()
    PASTE = auto()
    TRANSITION = auto()
    KEYFRAMES_BRIGHTNESS = auto()
    KEYFRAMES_CONTRAST = auto()


class MenuSlice(Enum):
    KEEP_BOTH = 0
    KEEP_LEFT = auto()
    KEEP_RIGHT = auto()


class MenuSplitAudio(Enum):
    SINGLE = 0
    MULTIPLE = auto()
