import sys
import json
import os
from PyQt6.QtCore import Qt, QUrl, QTimer, QSize, QPoint, QRect, QEvent, QSettings
from PyQt6.QtGui import QPainter, QPen, QColor, QMouseEvent, QAction, QIcon
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, 
                            QWidget, QSizeGrip, QHBoxLayout, QPushButton,
                            QSystemTrayIcon, QMenu, QSpinBox, QDialog,
                            QLabel, QVBoxLayout, QCheckBox)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings

if sys.platform == 'win32':
    import ctypes
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

class DragHandle(QWidget):
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(20) 
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.dragging = False
        self.start_pos = None
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        font = painter.font()
        font.setFamily("Courier New")
        font.setPointSize(10)
        painter.setFont(font)
        
        painter.setPen(QColor(255, 255, 255))
        
        rect = self.rect()
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, "stalcraft.widgets")
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.start_pos = event.globalPosition().toPoint()
            self.window_start_pos = self.window().pos()
    
    def mouseMoveEvent(self, event):
        if self.dragging:
            delta = event.globalPosition().toPoint() - self.start_pos
            self.window().move(self.window_start_pos + delta)
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False

class SettingsDialog(QDialog):
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Настройки sc.widgets")
        self.setFixedSize(300, 200)
        
        layout = QVBoxLayout(self)
        
        zoom_layout = QHBoxLayout()
        self.zoom_spin = QSpinBox()
        self.zoom_spin.setRange(25, 200)
        self.zoom_spin.setSuffix("%")
        self.zoom_spin.setSingleStep(25)
        zoom_layout.addWidget(QLabel("Масштаб:"))
        zoom_layout.addWidget(self.zoom_spin)
        layout.addLayout(zoom_layout)
        
        self.always_on_top = QCheckBox("Поверх других окон")
        layout.addWidget(self.always_on_top)
        
        layout.addStretch()
        self.apply_button = QPushButton("Применить")
        self.apply_button.clicked.connect(self.accept)
        layout.addWidget(self.apply_button)

class ResizableFramelessWidget(QWidget):
    
    BORDER_WIDTH = 8
    MIN_SIZE = QSize(300, 200)
    MAX_SIZE = QSize(1920, 1080)
    
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.setWindowIcon(QIcon("icons/tray.png"))
        
        self.settings = QSettings("stalcraft.widgets", "widget")

        self.resizing = False
        self.resize_edge = None
        self.start_pos = None
        self.start_geometry = None
        self.aspect_ratio = 16/9
        self.maintain_aspect_ratio = False
        
        self.resize(1024, 576)

        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(self.BORDER_WIDTH, self.BORDER_WIDTH, 
                                     self.BORDER_WIDTH, self.BORDER_WIDTH)
        self.layout.setSpacing(0)
        
        self.content = QWidget()
        self.content.setObjectName("content")
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        
        self.web_view = QWebEngineView()
        self.web_view.load(QUrl("https://stalcraft.wiki/maps"))
        self.content_layout.addWidget(self.web_view)
        
        self.layout.addWidget(self.content)
        self.drag_handle = DragHandle(self)
        
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon("icons/tray.png"))
        
        tray_menu = QMenu()
        settings_action = QAction("Настройки", self)
        settings_action.triggered.connect(self.showSettings)
        quit_action = QAction("Закрыть", self)
        quit_action.triggered.connect(self.close)
        
        tray_menu.addAction(settings_action)
        tray_menu.addSeparator()
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        
        self.setStyleSheet("""
            #content {
                background-color: white;
                border-radius: 10px;
                border: 1px solid white;
            }
        """)
        
        self.loadSettings()
    
    def showSettings(self):
        dialog = SettingsDialog(self)
        
        dialog.zoom_spin.setValue(int(self.web_view.zoomFactor() * 100))
        dialog.always_on_top.setChecked(bool(self.windowFlags() & Qt.WindowType.WindowStaysOnTopHint))
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.web_view.setZoomFactor(dialog.zoom_spin.value() / 100)
            
            flags = self.windowFlags()
            if dialog.always_on_top.isChecked():
                flags |= Qt.WindowType.WindowStaysOnTopHint
            else:
                flags &= ~Qt.WindowType.WindowStaysOnTopHint
            self.setWindowFlags(flags)
            self.show()
            
            self.saveSettings()
    
    def saveSettings(self):
        self.settings.setValue("zoom_factor", self.web_view.zoomFactor())
        self.settings.setValue("always_on_top", bool(self.windowFlags() & Qt.WindowType.WindowStaysOnTopHint))
        self.settings.setValue("geometry", self.geometry())
    
    def loadSettings(self):
        zoom_factor = self.settings.value("zoom_factor", 1.0, type=float)
        self.web_view.setZoomFactor(zoom_factor)
        
        always_on_top = self.settings.value("always_on_top", False, type=bool)
        if always_on_top:
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        
        geometry = self.settings.value("geometry")
        if geometry:
            self.setGeometry(geometry)
    
    def closeEvent(self, event):
        self.saveSettings()
        event.accept()
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.updateDragHandle()
    
    def showEvent(self, event):
        super().showEvent(event)
        self.updateDragHandle()
    
    def updateDragHandle(self):
        if hasattr(self, 'web_view') and hasattr(self, 'drag_handle'):
            self.drag_handle.setGeometry(
                self.BORDER_WIDTH,
                self.BORDER_WIDTH,
                self.width() - 2 * self.BORDER_WIDTH,
                self.drag_handle.height()
            )
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(255, 255, 255))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawRoundedRect(
            self.BORDER_WIDTH // 2,
            self.BORDER_WIDTH // 2,
            self.width() - self.BORDER_WIDTH,
            self.height() - self.BORDER_WIDTH,
            10, 10
        )
    
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            edge = self.getResizeEdge(event.position().toPoint())
            if edge:
                self.resizing = True
                self.resize_edge = edge
                self.start_pos = event.globalPosition().toPoint()
                self.start_geometry = QRect(self.pos(), self.size())
    
    def mouseMoveEvent(self, event):
        if not self.resizing:
            edge = self.getResizeEdge(event.position().toPoint())
            cursor = self.getCursorForEdge(edge)
            self.setCursor(cursor)
            return
        

        current_pos = event.globalPosition().toPoint()
        delta = current_pos - self.start_pos
        
        new_geometry = self.calculateNewGeometry(delta)
        
        if self.isValidGeometry(new_geometry):
            self.setGeometry(new_geometry)
            self.updateDragHandle()
    
    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.resizing = False
            self.resize_edge = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Shift:
            self.maintain_aspect_ratio = True
    
    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key.Key_Shift:
            self.maintain_aspect_ratio = False
    
    def getResizeEdge(self, pos):
        x, y = pos.x(), pos.y()
        w, h = self.width(), self.height()
        b = self.BORDER_WIDTH
        
        left = x < b
        right = x > w - b
        top = y < b
        bottom = y > h - b
        
        if left and top: return 'top-left'
        if right and top: return 'top-right'
        if left and bottom: return 'bottom-left'
        if right and bottom: return 'bottom-right'
        if left: return 'left'
        if right: return 'right'
        if top: return 'top'
        if bottom: return 'bottom'
        return None
    
    def getCursorForEdge(self, edge):
        cursors = {
            'top-left': Qt.CursorShape.SizeFDiagCursor,
            'top-right': Qt.CursorShape.SizeBDiagCursor,
            'bottom-left': Qt.CursorShape.SizeBDiagCursor,
            'bottom-right': Qt.CursorShape.SizeFDiagCursor,
            'left': Qt.CursorShape.SizeHorCursor,
            'right': Qt.CursorShape.SizeHorCursor,
            'top': Qt.CursorShape.SizeVerCursor,
            'bottom': Qt.CursorShape.SizeVerCursor,
            None: Qt.CursorShape.ArrowCursor
        }
        return cursors.get(edge, Qt.CursorShape.ArrowCursor)
    
    def calculateNewGeometry(self, delta):
        new_geometry = QRect(self.start_geometry)
        dx, dy = delta.x(), delta.y()
        
        if self.resize_edge in ['top-left', 'top-right', 'bottom-left', 'bottom-right']:
            if abs(dx) > abs(dy):
                if self.resize_edge == 'top-left':
                    new_geometry.setLeft(self.start_geometry.left() + dx)
                elif self.resize_edge == 'top-right':
                    new_geometry.setRight(self.start_geometry.right() + dx)
                elif self.resize_edge == 'bottom-left':
                    new_geometry.setLeft(self.start_geometry.left() + dx)
                elif self.resize_edge == 'bottom-right':
                    new_geometry.setRight(self.start_geometry.right() + dx)
            else:
                if self.resize_edge == 'top-left':
                    new_geometry.setTop(self.start_geometry.top() + dy)
                elif self.resize_edge == 'top-right':
                    new_geometry.setTop(self.start_geometry.top() + dy)
                elif self.resize_edge == 'bottom-left':
                    new_geometry.setBottom(self.start_geometry.bottom() + dy)
                elif self.resize_edge == 'bottom-right':
                    new_geometry.setBottom(self.start_geometry.bottom() + dy)
        else:
            if self.resize_edge in ['left', 'top-left', 'bottom-left']:
                new_geometry.setLeft(self.start_geometry.left() + dx)
            if self.resize_edge in ['right', 'top-right', 'bottom-right']:
                new_geometry.setRight(self.start_geometry.right() + dx)
            if self.resize_edge in ['top', 'top-left', 'top-right']:
                new_geometry.setTop(self.start_geometry.top() + dy)
            if self.resize_edge in ['bottom', 'bottom-left', 'bottom-right']:
                new_geometry.setBottom(self.start_geometry.bottom() + dy)
        
        if self.maintain_aspect_ratio:
            new_geometry = self.maintainAspectRatio(new_geometry)
        
        return new_geometry
    
    def maintainAspectRatio(self, geometry):
        new_geometry = QRect(geometry)
        width = new_geometry.width()
        height = new_geometry.height()
        
        if abs(width - self.start_geometry.width()) > abs(height - self.start_geometry.height()):
            target_height = int(width / self.aspect_ratio)
            if self.resize_edge in ['top', 'top-left', 'top-right']:
                new_geometry.setTop(new_geometry.bottom() - target_height)
            else:
                new_geometry.setBottom(new_geometry.top() + target_height)
        else:
            target_width = int(height * self.aspect_ratio)
            if self.resize_edge in ['left', 'top-left', 'bottom-left']:
                new_geometry.setLeft(new_geometry.right() - target_width)
            else:
                new_geometry.setRight(new_geometry.left() + target_width)
        
        return new_geometry
    
    def isValidGeometry(self, geometry):
        if geometry.width() < self.MIN_SIZE.width() or geometry.height() < self.MIN_SIZE.height():
            return False
        
        if geometry.width() > self.MAX_SIZE.width() or geometry.height() > self.MAX_SIZE.height():
            return False
        
        screen = QApplication.primaryScreen().geometry()
        if not screen.contains(geometry):
            return False
        
        return True

def main():
    if hasattr(sys, 'setappname'):
        sys.setappname('scwidget')
    
    app = QApplication(sys.argv)
    app.setApplicationName('scwidget')
    app.setApplicationDisplayName('sc.widgets')
    app.setWindowIcon(QIcon("icons/tray.png"))
    
    window = ResizableFramelessWidget()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main() 
