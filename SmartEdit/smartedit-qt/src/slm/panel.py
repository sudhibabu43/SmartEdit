"""
@file
@brief Integrated SLM Assistant Dock Panel for SmartEdit Video Editing.
@author SmartEdit Team
"""

import json
from datetime import datetime
from typing import Optional, Dict, Any
from qt_api import (
    Qt, QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QPlainTextEdit, QFrame, QScrollArea,
    QProgressBar, QThread, pyqtSignal, pyqtSlot, QSizePolicy, QEvent,
    QTimer
)

from slm.prompt_parser import PromptParser
from slm.editing_controller import EditingController, AIPlan
from slm.command_schema import SLMCommand
from classes.logger import log
from slm.history_store import PromptHistoryStore
from slm.chat_controller import ChatController


class SLMAnalysisWorker(QThread):
    """Background worker to analyze media and generate AI plan without UI freezing."""
    statusSignal = pyqtSignal(str)
    responseReadySignal = pyqtSignal(object)
    failedSignal = pyqtSignal(str)

    def __init__(self, chat_controller: ChatController, prompt: str):
        super().__init__()
        self.chat_controller = chat_controller
        self.prompt = prompt

    def run(self):
        try:
            self.statusSignal.emit("Interpreting instruction and analyzing media...")
            response = self.chat_controller.process_message(self.prompt)
            self.responseReadySignal.emit(response)
        except Exception as ex:
            log.error(f"SLM analysis failed: {ex}", exc_info=1)
            self.failedSignal.emit(str(ex))


class PromptInputTextEdit(QPlainTextEdit):
    """Specialized text editor ensuring keyboard focus and Enter-to-run behavior."""
    returnPressed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)
        if self.viewport():
            self.viewport().setFocusPolicy(Qt.StrongFocus)
            self.viewport().setCursor(Qt.IBeamCursor)
        self.setTextInteractionFlags(Qt.TextEditorInteraction)
        self.setTabChangesFocus(True)

    def mousePressEvent(self, event):
        self.setFocus(Qt.MouseFocusReason)
        super().mousePressEvent(event)
        event.accept()

    def mouseReleaseEvent(self, event):
        self.setFocus(Qt.MouseFocusReason)
        super().mouseReleaseEvent(event)

    def viewportEvent(self, event):
        if event.type() in (QEvent.MouseButtonPress, QEvent.MouseButtonRelease):
            self.setFocus(Qt.MouseFocusReason)
        return super().viewportEvent(event)

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not (event.modifiers() & Qt.ShiftModifier):
            self.returnPressed.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class ChatBubble(QWidget):
    """A single chat message bubble."""
    applyClicked = pyqtSignal(object)
    rejectClicked = pyqtSignal()
    
    def __init__(self, role: str, text: str, plan: Optional[AIPlan] = None, parent=None):
        super().__init__(parent)
        self.role = role
        self.plan = plan
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        bubble_frame = QFrame()
        bubble_layout = QVBoxLayout(bubble_frame)
        bubble_layout.setContentsMargins(12, 12, 12, 12)
        bubble_layout.setSpacing(8)
        
        text_label = QLabel(text)
        text_label.setWordWrap(True)
        text_label.setTextFormat(Qt.RichText)
        text_label.setStyleSheet("font-size: 12px;")
        
        if role == "user":
            bubble_frame.setStyleSheet("""
                QFrame {
                    background-color: #0078d7;
                    color: #ffffff;
                    border-radius: 12px;
                }
            """)
            bubble_layout.addWidget(text_label)
            
            container_layout = QHBoxLayout()
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.addStretch()
            container_layout.addWidget(bubble_frame)
            layout.addLayout(container_layout)
        else:
            bubble_frame.setStyleSheet("""
                QFrame {
                    background-color: #2b303b;
                    color: #e0e0e0;
                    border-radius: 12px;
                }
            """)
            
            header = QLabel("🤖 AI Assistant")
            header.setStyleSheet("font-size: 10px; font-weight: bold; color: #7f8c8d; margin-bottom: 4px;")
            bubble_layout.addWidget(header)
            bubble_layout.addWidget(text_label)
            
            if plan and not plan.is_empty:
                btn_layout = QHBoxLayout()
                btn_layout.setSpacing(8)
                
                self.btn_apply = QPushButton("✓ Apply")
                self.btn_apply.setFixedHeight(28)
                self.btn_apply.setStyleSheet("""
                    QPushButton { background-color: #1a8745; color: white; border-radius: 4px; padding: 0 10px; }
                    QPushButton:hover { background-color: #1f9c50; }
                """)
                self.btn_apply.clicked.connect(self.on_apply)
                
                self.btn_reject = QPushButton("✕ Cancel")
                self.btn_reject.setFixedHeight(28)
                self.btn_reject.setStyleSheet("""
                    QPushButton { background-color: #c0392b; color: white; border-radius: 4px; padding: 0 10px; }
                    QPushButton:hover { background-color: #e74c3c; }
                """)
                self.btn_reject.clicked.connect(self.on_reject)
                
                btn_layout.addWidget(self.btn_apply)
                btn_layout.addWidget(self.btn_reject)
                btn_layout.addStretch()
                bubble_layout.addLayout(btn_layout)
            
            container_layout = QHBoxLayout()
            container_layout.setContentsMargins(0, 0, 0, 0)
            container_layout.addWidget(bubble_frame)
            container_layout.addStretch()
            layout.addLayout(container_layout)
            
    def on_apply(self):
        self.applyClicked.emit(self.plan)
        
    def on_reject(self):
        self.rejectClicked.emit()
        

class SLMAssistantPanel(QDockWidget):
    """
    Chat-based AI Assistant Dock Panel.
    """

    def __init__(self, parent=None):
        super().__init__("AI Editing Assistant", parent)
        self.setObjectName("dockSlmAssistant")
        self.setAllowedAreas(Qt.AllDockWidgetAreas)

        self.parser = PromptParser()
        self.controller = EditingController()
        self.chat_controller = ChatController(self.parser, self.controller)
        
        self.history_store = PromptHistoryStore()
        self.worker: Optional[SLMAnalysisWorker] = None

        self._setup_ui()
        self._add_ai_bubble("Hello! I can help you create and modify your video rough cut. Tell me what you'd like to do.")

    def _setup_ui(self):
        main_container = QWidget()
        main_container.setStyleSheet("background-color: #1a1e24;")
        self.setWidget(main_container)

        root_layout = QVBoxLayout(main_container)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # -----------------------------------------------------
        # Chat History Scroll Area
        # -----------------------------------------------------
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setWidgetResizable(True)
        self.chat_scroll.setFrameShape(QFrame.NoFrame)
        self.chat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.chat_scroll.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")

        self.chat_container = QWidget()
        self.chat_container.setStyleSheet("background-color: transparent;")
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setContentsMargins(14, 14, 14, 14)
        self.chat_layout.setSpacing(12)
        self.chat_layout.addStretch(1)

        self.chat_scroll.setWidget(self.chat_container)
        root_layout.addWidget(self.chat_scroll, 1)

        # -----------------------------------------------------
        # Status Bar
        # -----------------------------------------------------
        self.status_bar_frame = QFrame()
        self.status_bar_frame.setStyleSheet("background-color: #121519; border-top: 1px solid #2a303c;")
        status_layout = QHBoxLayout(self.status_bar_frame)
        status_layout.setContentsMargins(10, 4, 10, 4)
        
        self.status_label = QLabel("Ready")
        self.status_label.setStyleSheet("color: #8b99a6; font-size: 10px;")
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setFixedWidth(100)
        self.progress_bar.setStyleSheet("""
            QProgressBar { background-color: #0d131a; border: none; border-radius: 3px; }
            QProgressBar::chunk { background-color: #0084ff; border-radius: 3px; }
        """)
        self.progress_bar.hide()
        
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        status_layout.addWidget(self.progress_bar)
        
        root_layout.addWidget(self.status_bar_frame)

        # -----------------------------------------------------
        # Input Area
        # -----------------------------------------------------
        input_frame = QFrame()
        input_frame.setStyleSheet("background-color: #121519;")
        input_layout = QVBoxLayout(input_frame)
        input_layout.setContentsMargins(14, 8, 14, 14)
        input_layout.setSpacing(8)

        self.prompt_input = PromptInputTextEdit()
        self.prompt_input.setPlaceholderText("Type an editing instruction...")
        self.prompt_input.setFixedHeight(50)
        self.prompt_input.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1a1e24;
                color: #ffffff;
                border: 1px solid #2a303c;
                border-radius: 6px;
                padding: 8px;
                font-size: 12px;
            }
            QPlainTextEdit:focus {
                border: 1px solid #0084ff;
            }
        """)
        self.prompt_input.returnPressed.connect(self.on_send)
        input_layout.addWidget(self.prompt_input)

        root_layout.addWidget(input_frame)

    def _scroll_to_bottom(self):
        QTimer.singleShot(10, self._do_scroll)
        
    def _do_scroll(self):
        scrollbar = self.chat_scroll.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _add_user_bubble(self, text: str):
        self._insert_bubble(ChatBubble("user", text))

    def _add_ai_bubble(self, text: str, plan: Optional[AIPlan] = None):
        bubble = ChatBubble("ai", text, plan)
        bubble.applyClicked.connect(self.on_apply_plan)
        bubble.rejectClicked.connect(self.on_reject_plan)
        self._insert_bubble(bubble)

    def _insert_bubble(self, bubble: QWidget):
        count = self.chat_layout.count()
        if count > 0:
            self.chat_layout.insertWidget(count - 1, bubble)
        else:
            self.chat_layout.addWidget(bubble)
        self._scroll_to_bottom()

    def on_send(self):
        prompt = self.prompt_input.toPlainText().strip()
        if not prompt:
            return

        self.prompt_input.clear()
        self.prompt_input.setEnabled(False)
        self._add_user_bubble(prompt)
        
        self.history_store.add_prompt(prompt)

        self.status_label.setText("Thinking...")
        self.progress_bar.show()

        try:
            self.worker = SLMAnalysisWorker(self.chat_controller, prompt)
            self.worker.statusSignal.connect(lambda s: self.status_label.setText(s))
            self.worker.responseReadySignal.connect(self._on_response_ready)
            self.worker.failedSignal.connect(self._on_analysis_failed)
            self.worker.start()
        except Exception as ex:
            log.error(f"Failed to start SLM AnalysisWorker: {ex}", exc_info=1)
            self.prompt_input.setEnabled(True)
            self.prompt_input.setFocus()
            self.progress_bar.hide()
            self.status_label.setText("Error")

    @pyqtSlot(object)
    def _on_response_ready(self, response: Dict[str, Any]):
        self.prompt_input.setEnabled(True)
        self.prompt_input.setFocus()
        self.progress_bar.hide()
        self.status_label.setText("Ready")

        text = response.get("text", "")
        plan = response.get("plan")
        self._add_ai_bubble(text, plan)

    @pyqtSlot(str)
    def _on_analysis_failed(self, error_msg: str):
        self.prompt_input.setEnabled(True)
        self.prompt_input.setFocus()
        self.progress_bar.hide()
        self.status_label.setText("Error")
        self._add_ai_bubble(f"An error occurred: {error_msg}")

    def on_apply_plan(self, plan: AIPlan):
        if not plan:
            return
            
        self.status_label.setText("Applying changes...")
        self.progress_bar.show()
        
        self._add_user_bubble("Apply changes.")
        
        try:
            self.worker = SLMAnalysisWorker(self.chat_controller, "yes")
            self.worker.statusSignal.connect(lambda s: self.status_label.setText(s))
            self.worker.responseReadySignal.connect(self._on_response_ready)
            self.worker.failedSignal.connect(self._on_analysis_failed)
            self.worker.start()
        except Exception as ex:
            log.error(f"Failed to apply: {ex}", exc_info=1)
            self.progress_bar.hide()
            self.status_label.setText("Error")

    def on_reject_plan(self):
        self._add_user_bubble("Cancel changes.")
        
        try:
            self.worker = SLMAnalysisWorker(self.chat_controller, "no")
            self.worker.statusSignal.connect(lambda s: self.status_label.setText(s))
            self.worker.responseReadySignal.connect(self._on_response_ready)
            self.worker.failedSignal.connect(self._on_analysis_failed)
            self.worker.start()
        except Exception as ex:
            log.error(f"Failed to cancel: {ex}", exc_info=1)
