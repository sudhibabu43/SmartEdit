from qt_api import QState, QStateMachine


class DragState(QState):
    def __init__(self, widget):
        super().__init__()
        self.widget = widget

    def onEntry(self, event):
        self.widget._startClipDrag()

    def onExit(self, event):
        self.widget._finishClipDrag()


class ResizeState(QState):
    def __init__(self, widget):
        super().__init__()
        self.widget = widget

    def onEntry(self, event):
        self.widget._startResize()

    def onExit(self, event):
        self.widget._finishResize()


class PlayheadState(QState):
    def __init__(self, widget):
        super().__init__()
        self.widget = widget

    def onEntry(self, event):
        self.widget._startPlayhead()

    def onExit(self, event):
        self.widget._finishPlayhead()


class BoxSelectState(QState):
    def __init__(self, widget):
        super().__init__()
        self.widget = widget

    def onEntry(self, event):
        self.widget._startBoxSelect()

    def onExit(self, event):
        self.widget._finishBoxSelect()


class KeyframeState(QState):
    def __init__(self, widget):
        super().__init__()
        self.widget = widget

    def onEntry(self, event):
        self.widget._startKeyframeDrag()

    def onExit(self, event):
        self.widget._finishKeyframeDrag()


class TimelineStateMachine(QStateMachine):
    def __init__(self, widget):
        super().__init__(widget)
        self.idle = QState()
        self.drag = DragState(widget)
        self.resize = ResizeState(widget)
        self.playhead = PlayheadState(widget)
        self.box = BoxSelectState(widget)
        self.keyframe = KeyframeState(widget)

        
        
        
        
        for state in (self.idle, self.drag, self.resize, self.playhead, self.box, self.keyframe):
            self.addState(state)

        self.setInitialState(self.idle)
        self.start()
