from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QFrame, QPushButton
from PySide6.QtCore import Qt, QRectF, Signal, QObject
from PySide6.QtGui import QPixmap, QPainter, QWheelEvent, QCursor

class ZoomablePreviewSignals(QObject):
    """Sinais para comunicar as mudanças de tamanho do viewport."""
    max_size_changed = Signal(QRectF) # Usaremos QRectF inicialmente, mas ajustaremos no CullingApp.

class ZoomablePreview(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.signals = ZoomablePreviewSignals()
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        
        # 1. SETUP BÁSICO
        self.setAlignment(Qt.AlignCenter)
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setStyleSheet("background: transparent;")
        
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setRenderHint(QPainter.Antialiasing, False)
        self.setRenderHint(QPainter.SmoothPixmapTransform, True)
        
        self.pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(self.pixmap_item)
        self.current_pixmap = None
        self._is_zoomed = False

        # --- 2. BOTÕES DE OVERLAY (A novidade) ---
        # Criamos botões filhos de 'self' para flutuarem por cima
        self.btn_plus = QPushButton("+", self)
        self.btn_minus = QPushButton("-", self)

        # Impede que os botões roubem o foco do teclado ao serem clicados
        self.btn_plus.setFocusPolicy(Qt.NoFocus)
        self.btn_minus.setFocusPolicy(Qt.NoFocus)
        # -------------------------
        
        # Estilo "Glass" (Semi-transparente e moderno)
        style = """
            QPushButton {
                background-color: rgba(0, 0, 0, 150);
                color: white;
                border-radius: 15px;
                font-weight: bold;
                font-size: 16px;
                border: 1px solid #555;
            }
            QPushButton:hover { background-color: rgba(41, 128, 185, 200); }
            QPushButton:pressed { background-color: white; color: black; }
        """
        self.btn_plus.setStyleSheet(style)
        self.btn_minus.setStyleSheet(style)
        
        # Tamanho fixo
        self.btn_plus.setFixedSize(30, 30)
        self.btn_minus.setFixedSize(30, 30)
        
        # Cursor de mão para indicar que é clicável
        self.btn_plus.setCursor(QCursor(Qt.ArrowCursor))
        self.btn_minus.setCursor(QCursor(Qt.ArrowCursor))

        # Conexões internas
        self.btn_plus.clicked.connect(self.zoom_in)
        self.btn_minus.clicked.connect(self.zoom_out)

        # Começam invisíveis
        self.btn_plus.hide()
        self.btn_minus.hide()

    def setPixmap(self, pixmap):
        self.current_pixmap = pixmap
        self._is_zoomed = False
        self.resetTransform()
        self.pixmap_item.setPixmap(pixmap)
        rect = QRectF(pixmap.rect())
        self.scene.setSceneRect(rect)
        self.setDragMode(QGraphicsView.NoDrag)
        self.fitInView(self.pixmap_item, Qt.KeepAspectRatio)
        
        # Garante que botões sumam ao trocar de foto
        self.btn_plus.hide()
        self.btn_minus.hide()

    def clear(self):
        self.pixmap_item.setPixmap(QPixmap())
        self.current_pixmap = None
        self.btn_plus.hide()
        self.btn_minus.hide()

    def setText(self, text):
        if text: self.clear()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        
        # 1. Manter o ajuste de visualização (se não estiver em zoom)
        if not self._is_zoomed and self.current_pixmap:
            self.fitInView(self.pixmap_item, Qt.KeepAspectRatio)
            
        # 2. Notificar a nova área disponível para o CullingApp
        viewport_rect = self.viewport().rect()
        self.signals.max_size_changed.emit(QRectF(viewport_rect))
            
        # 3. POSICIONAMENTO DINÂMICO dos botões de zoom (mantido)
        margin = 10
        btn_w = 30
        
        x_pos = self.width() - btn_w - margin
        y_pos_plus = self.height() - btn_w - margin - 40 
        y_pos_minus = self.height() - btn_w - margin     
        
        self.btn_plus.move(x_pos, y_pos_plus)
        self.btn_minus.move(x_pos, y_pos_minus)

    def start_zoom_mode(self, full_res_pixmap):
        self._is_zoomed = True
        self.resetTransform()
        if full_res_pixmap:
            self.pixmap_item.setPixmap(full_res_pixmap)
            self.scene.setSceneRect(QRectF(full_res_pixmap.rect()))
        
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.centerOn(self.pixmap_item)
        
        # MOSTRAR OS BOTÕES
        self.btn_plus.show()
        self.btn_minus.show()

    def stop_zoom_mode(self):
        if not self._is_zoomed: return
        self._is_zoomed = False
        self.resetTransform()
        if self.current_pixmap:
            self.pixmap_item.setPixmap(self.current_pixmap)
            self.scene.setSceneRect(QRectF(self.current_pixmap.rect()))
            self.fitInView(self.pixmap_item, Qt.KeepAspectRatio)
        self.setDragMode(QGraphicsView.NoDrag)
        
        # ESCONDER OS BOTÕES
        self.btn_plus.hide()
        self.btn_minus.hide()

    def zoom_in(self):
        if self._is_zoomed: self.scale(1.2, 1.2)

    def zoom_out(self):
        if self._is_zoomed: self.scale(0.8, 0.8)

    def wheelEvent(self, event: QWheelEvent):
        if self._is_zoomed:
            factor = 1.1 if event.angleDelta().y() > 0 else 0.9
            self.scale(factor, factor)
            event.accept()
        else:
            event.ignore()

    def manual_scroll(self, key):
        """Move a visão manualmente usando as setas."""
        if not self._is_zoomed: return
        
        step = 50 # Velocidade do scroll
        h_bar = self.horizontalScrollBar()
        v_bar = self.verticalScrollBar()

        if key == Qt.Key_Left:
            h_bar.setValue(h_bar.value() - step)
        elif key == Qt.Key_Right:
            h_bar.setValue(h_bar.value() + step)
        elif key == Qt.Key_Up:
            v_bar.setValue(v_bar.value() - step)
        elif key == Qt.Key_Down:
            v_bar.setValue(v_bar.value() + step)