from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QFrame
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPixmap, QPainter, QWheelEvent

class ZoomablePreview(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        
        # 1. ALINHAMENTO E VISUAL
        self.setAlignment(Qt.AlignCenter) # Garante centro quando a imagem é menor que a tela
        self.setFrameShape(QFrame.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setStyleSheet("background: transparent;")
        
        # 2. CONFIGURAÇÃO DE ZOOM
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setDragMode(QGraphicsView.NoDrag)
        self.setRenderHint(QPainter.Antialiasing, False)
        self.setRenderHint(QPainter.SmoothPixmapTransform, True)
        
        # Estado
        self.pixmap_item = QGraphicsPixmapItem()
        self.scene.addItem(self.pixmap_item)
        self.current_pixmap = None # Guarda a versão leve (720px)
        self._is_zoomed = False

    def setPixmap(self, pixmap):
        """Modo 'Fit': Chamado ao trocar de foto ou carregar preview."""
        self.current_pixmap = pixmap
        self._is_zoomed = False
        
        # --- O SEGREDO DO RESET ---
        self.resetTransform() # 1. Remove qualquer zoom anterior
        self.pixmap_item.setPixmap(pixmap)
        
        # 2. Redefine o tamanho do palco para o tamanho exato da imagem nova
        rect = QRectF(pixmap.rect())
        self.scene.setSceneRect(rect)
        
        # 3. Trava o movimento e ajusta
        self.setDragMode(QGraphicsView.NoDrag)
        self.fitInView(self.pixmap_item, Qt.KeepAspectRatio)

    def clear(self):
        self.pixmap_item.setPixmap(QPixmap())
        self.current_pixmap = None

    def setText(self, text):
        if text: self.clear()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # Se redimensionar a janela e NÃO estiver em zoom, reajusta o Fit
        if not self._is_zoomed and self.current_pixmap:
            self.fitInView(self.pixmap_item, Qt.KeepAspectRatio)

    def start_zoom_mode(self, full_res_pixmap):
        """Entra no modo de Zoom com a imagem HD."""
        self._is_zoomed = True
        
        # 1. Limpa transformações anteriores
        self.resetTransform()
        
        # 2. Coloca a imagem HD
        if full_res_pixmap:
            self.pixmap_item.setPixmap(full_res_pixmap)
            # Atualiza o tamanho do palco para o tamanho da imagem HD
            self.scene.setSceneRect(QRectF(full_res_pixmap.rect()))
        
        # 3. Habilita a 'mãozinha'
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        
        # 4. O AJUSTE DE OURO: Centraliza a câmera na imagem
        self.centerOn(self.pixmap_item)

    def stop_zoom_mode(self):
        """Sai do modo zoom e volta para a thumb leve."""
        # Se já estiver fora do zoom, ignora para não piscar
        if not self._is_zoomed: 
            return

        self._is_zoomed = False
        self.resetTransform() # ZERA O ZOOM
        
        # Restaura a imagem leve
        if self.current_pixmap:
            self.pixmap_item.setPixmap(self.current_pixmap)
            self.scene.setSceneRect(QRectF(self.current_pixmap.rect()))
            self.fitInView(self.pixmap_item, Qt.KeepAspectRatio)
        
        self.setDragMode(QGraphicsView.NoDrag)

    def zoom_in(self):
        if self._is_zoomed:
            self.scale(1.2, 1.2)

    def zoom_out(self):
        if self._is_zoomed:
            self.scale(0.8, 0.8)

    def wheelEvent(self, event: QWheelEvent):
        if self._is_zoomed:
            factor = 1.1 if event.angleDelta().y() > 0 else 0.9
            self.scale(factor, factor)
            event.accept()
        else:
            # Ignora scroll se não estiver em zoom
            event.ignore()

    def manual_scroll(self, key):
        """Move a visão manualmente usando as setas."""
        if not self._is_zoomed: return
        
        step = 50 # Quantidade de pixels para mover
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