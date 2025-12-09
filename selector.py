from PySide6.QtGui import QPainter, QBrush, QColor, QFont
from PySide6.QtCore import Qt, QRect

class ImageSelector:
    def __init__(self):
        # Dicionário privado para guardar as notas {caminho: nota}
        self._ratings = {}

    def set_rating(self, path, rating):
        """Define uma nota. Se rating for 0, remove da lista."""
        if rating > 0:
            self._ratings[path] = rating
        else:
            if path in self._ratings:
                del self._ratings[path]

    def get_rating(self, path):
        """Retorna a nota atual de um arquivo (ou 0 se não tiver)."""
        return self._ratings.get(path, 0)

    def get_selected_items(self):
        """Retorna o dicionário completo para exportação."""
        return self._ratings

    def clear(self):
        self._ratings.clear()

    def apply_overlay(self, pixmap, rating):
        """
        Recebe um QPixmap limpo e desenha o selo sobre ele.
        Retorna um NOVO QPixmap modificado.
        """
        if rating == 0:
            return pixmap
        
        resultado = pixmap.copy()
        painter = QPainter(resultado)
        painter.setRenderHint(QPainter.Antialiasing)

        # Configuração do visual do selo
        tamanho_selo = 30
        margem = 5
        x = resultado.width() - tamanho_selo - margem
        y = margem

        # Desenha Círculo Amarelo
        painter.setBrush(QBrush(QColor("#f1c40f")))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(x, y, tamanho_selo, tamanho_selo)

        # Desenha Número
        painter.setPen(QColor("#000000"))
        font = QFont("Arial", 12, QFont.Bold)
        painter.setFont(font)
        painter.drawText(QRect(x, y, tamanho_selo, tamanho_selo), Qt.AlignCenter, str(rating))

        painter.end()
        return resultado