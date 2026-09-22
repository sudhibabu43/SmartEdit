from qt_api import QSize
from qt_api import QTreeView, QAbstractItemView

from classes import info
from classes.app import get_app
from windows.models.add_to_timeline_model import TimelineModel


class TimelineTreeView(QTreeView):
    """ A TreeView QWidget used on the add to timeline window """

    def currentChanged(self, selected, deselected):
        
        self.selected = selected
        self.deselected = deselected

        
        _ = self.app._tr

    def contextMenuEvent(self, event):
        
        event.ignore()

    def mousePressEvent(self, event):

        
        event.ignore()
        super().mousePressEvent(event)

    def refresh_view(self):
        self.timeline_model.update_model()
        self.hideColumn(2)

    def __init__(self, *args):
        
        QTreeView.__init__(self, *args)

        
        self.app = get_app()
        self.win = args[0]

        
        self.timeline_model = TimelineModel()

        
        self.selected = None
        self.deselected = None

        
        self.setModel(self.timeline_model.model)
        self.setIconSize(info.TREE_ICON_SIZE)
        self.setIndentation(0)
        self.setSelectionBehavior(QTreeView.SelectRows)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setWordWrap(True)

        
        self.refresh_view()
