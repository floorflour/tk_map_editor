from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QTextBrowser
#
# ------------------------------------------------------------------
#  可点击地图浏览器：带锚点检测的只读文本区域
# ------------------------------------------------------------------
#

class ClickableMapBrowser(QTextBrowser):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        # 禁止外部链接打开（内部我们处理锚点点击）
        self.setOpenExternalLinks(False)
        # 连接 anchorClicked 信号，不做默认处理
        self.anchorClicked.connect(lambda url: None)

    def mouseDoubleClickEvent(self, ev):
        ev.accept()

    def mouseReleaseEvent(self, ev):
        ev.accept()

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.RightButton:
            parent_window = self.parent()
            while parent_window and not hasattr(parent_window, 'on_right_click'):
                parent_window = parent_window.parent()
            if parent_window:
                parent_window.on_right_click()
            event.accept()
            return

        pos = event.position().toPoint()
        cursor = self.cursorForPosition(pos)
        char_format = cursor.charFormat()
        href = char_format.anchorHref()
        if href and href.startswith("node_"):
            try:
                node_id = int(href.split("_")[1])
            except Exception:
                node_id = None

            parent_window = self.parent()
            while parent_window and not hasattr(parent_window, 'on_map_anchor_clicked'):
                parent_window = parent_window.parent()

            if parent_window and node_id is not None:
                clicked_node = next((n for n in parent_window.all_nodes if n.node_id == node_id), None)
                if clicked_node:
                    parent_window.on_map_anchor_clicked(clicked_node)
            event.accept()
        else:
            super().mousePressEvent(event)

    def scrollToAnchor(self, anchor: str):
        pass

    def setSource(self, url: QUrl):
        pass

    def contextMenuEvent(self, event):
        event.ignore()