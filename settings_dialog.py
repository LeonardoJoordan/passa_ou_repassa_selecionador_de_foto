# settings_dialog.py
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPushButton, QWidget
from PySide6.QtCore import Qt

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurações")
        self.resize(400, 300)
        self.setStyleSheet("background-color: #2c3e50; color: #ecf0f1;")
        
        # Layout Principal
        layout = QVBoxLayout(self)
        
        # Placeholder (Conteúdo temporário)
        lbl_info = QLabel("Em breve: Opções de configuração aqui.")
        lbl_info.setAlignment(Qt.AlignCenter)
        lbl_info.setStyleSheet("font-size: 14px; color: #95a5a6;")
        
        # Botão Fechar
        btn_ok = QPushButton("Salvar / Fechar")
        btn_ok.clicked.connect(self.accept)
        btn_ok.setStyleSheet("""
            QPushButton {
                background-color: #27ae60; 
                color: white; 
                padding: 10px; 
                border: none; 
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #2ecc71; }
        """)
        
        layout.addWidget(lbl_info)
        layout.addWidget(btn_ok)