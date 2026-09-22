import threading
from enum import Enum


class ThemeName(Enum):
    """Friendly UI theme names used in settings"""
    COSMIC = "Cosmic Dusk"

    @staticmethod
    def get_sorted_theme_names():
        """Return a sorted list of theme names"""
        return sorted([theme.value for theme in ThemeName])

    @staticmethod
    def find_by_name(name):
        """Return a theme ENUM which matches a name"""
        for theme in ThemeName:
            if theme.value == name:
                return theme
        return ThemeName.COSMIC


class ThemeManager:
    """Singleton Theme Manager class, used to easily switch between UI themes"""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, app=None):
        """Override new method, so the same instance is always returned (i.e. singleton)"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ThemeManager, cls).__new__(cls)
                    cls._instance.app = app
                    cls._instance.original_style = app.style().objectName() if app else None
                    cls._instance.original_palette = app.palette() if app else None
                    cls._instance.current_theme = None
        return cls._instance

    def apply_theme(self, name):
        """Apply a new UI theme. Expects a ThemeName ENUM as the arg."""
        theme_enum = ThemeName.find_by_name(name)

        if theme_enum == ThemeName.COSMIC:
            from themes.cosmic.theme import CosmicTheme
            self.current_theme = CosmicTheme(self.app)

        
        self.current_theme.name = theme_enum.value

        
        self.current_theme.apply_theme()
        return self.current_theme

    def get_current_theme(self):
        """Return the current theme instance, or None if no theme is applied."""
        return self.current_theme
