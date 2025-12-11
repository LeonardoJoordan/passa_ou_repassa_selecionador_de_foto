import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QCheckBox, QGroupBox,
    QSpinBox, QSpacerItem, QSizePolicy, QFrame
)
from PySide6.QtCore import Qt, QSettings

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurações")
        self.resize(480, 480)

        # Estilo Dark Mode (mesmas cores, só refinando layout/curvas/tipografia)
        self.setStyleSheet("""
            QDialog {
                background-color: #2c3e50;
                color: #ecf0f1;
                border-radius: 10px;
            }
                           
            /* Torna todos os QLabel comuns transparentes */
            QLabel {
                background-color: transparent;
            }

            QLabel#HeaderTitle {
                font-size: 18px;
                font-weight: 600;
                background-color: transparent;
            }

            QLabel#HeaderSubtitle {
                font-size: 12px;
                color: #bdc3c7;
                background-color: transparent;
            }

            QGroupBox {
                border: 1px solid #5d6d7e;
                margin-top: 18px;
                font-weight: bold;
                color: #ecf0f1;
                border-radius: 6px;
                padding-top: 18px;
                padding-left: 10px;
                padding-right: 10px;
                padding-bottom: 10px;
                background-color: #273646;
            }

            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 8px;
                background-color: transparent;
            }

            QCheckBox {
                spacing: 8px;
                font-size: 13px;
                color: #ecf0f1;
                background-color: transparent;
            }

            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 1px solid #bdc3c7;
                border-radius: 3px;
                background-color: transparent;
            }

            QCheckBox::indicator:checked {
                background-color: #27ae60;
                border-color: #27ae60;
            }

            QCheckBox::indicator:disabled {
                background-color: #7f8c8d;
                border-color: #7f8c8d;
            }

            QSpinBox {
                background-color: #34495e;
                color: white;
                padding: 5px 8px;
                border: 1px solid #5d6d7e;
                border-radius: 4px;
            }

            QSpinBox::up-button, QSpinBox::down-button {
                border: none;
                background-color: #3b5164;
                width: 18px;
            }

            QSpinBox::up-button:hover, QSpinBox::down-button:hover {
                background-color: #466179;
            }

            QComboBox {
                background-color: #34495e;
                color: white;
                padding: 6px 8px;
                border: 1px solid #5d6d7e;
                border-radius: 4px;
                min-width: 180px;
            }

            QComboBox::drop-down {
                border: none;
                width: 22px;
                background-color: #3b5164;
            }

            QComboBox::down-arrow {
                width: 10px;
                height: 10px;
            }

            QPushButton {
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }

            QPushButton#PrimaryButton {
                background-color: #27ae60;
                color: white;
                border: none;
            }

            QPushButton#PrimaryButton:hover {
                background-color: #2ecc71;
            }

            QPushButton#SecondaryButton {
                background-color: transparent;
                color: #ecf0f1;
                border: 1px solid #5d6d7e;
            }

            QPushButton#SecondaryButton:hover {
                background-color: #34495e;
            }

            QFrame#line {
                background-color: #5d6d7e;
            }
        """)

        self.settings = QSettings("LeonardoSoft", "SelecionadorFotos")

        # --- LAYOUT PRINCIPAL ---
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(14)
        main_layout.setContentsMargins(18, 18, 18, 18)

        # CABEÇALHO
        header_layout = QVBoxLayout()
        lbl_title = QLabel("Correção e Exportação")
        lbl_title.setObjectName("HeaderTitle")

        lbl_subtitle = QLabel("Ajuste sua configuração para exportação da mídia.")
        lbl_subtitle.setObjectName("HeaderSubtitle")
        lbl_subtitle.setWordWrap(True)

        header_layout.addWidget(lbl_title)
        header_layout.addWidget(lbl_subtitle)
        main_layout.addLayout(header_layout)

        line = QFrame()
        line.setObjectName("line")
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)

        # [REMOVIDO] SELEÇÃO DO MOTOR (Agora é automático)

        # 2. GRUPO: AJUSTES AUTOMÁTICOS
        # Definimos o título fixo, já que só existe um motor
        grp_auto = QGroupBox("Correção de Imagem (ImageMagick)")
        self.grp_auto = grp_auto
        self.grp_auto.setEnabled(True) # Sempre ativo
        
        layout_auto = QVBoxLayout(grp_auto)
        layout_auto.setSpacing(8)

        # 2.1 Full Auto
        self.chk_full_auto = QCheckBox("Correção automática")
        layout_auto.addWidget(self.chk_full_auto)

        # 2.2 Itens Granulares (Visualmente presentes, mas desativados para o IM)
        layout_subs = QHBoxLayout()
        layout_subs.setContentsMargins(18, 0, 0, 0)        

        layout_auto.addLayout(layout_subs)

        main_layout.addWidget(grp_auto)

        # 3. GRUPO: PROPRIEDADES DO ARQUIVO
        grp_props = QGroupBox("Exportação")
        self.grp_props = grp_props
        layout_props = QVBoxLayout(grp_props)
        layout_props.setSpacing(10)

        # 3.1 Redimensionar
        row_resize = QHBoxLayout()
        self.chk_resize = QCheckBox("Redimensionar (lado maior):")
        self.chk_resize.toggled.connect(self.on_resize_toggled)

        self.spin_resize = QSpinBox()
        self.spin_resize.setRange(100, 3000)
        self.spin_resize.setSuffix(" px")
        self.spin_resize.setValue(1920)
        self.spin_resize.setEnabled(False)

        row_resize.addWidget(self.chk_resize)
        row_resize.addStretch()
        row_resize.addWidget(self.spin_resize)

        layout_props.addLayout(row_resize)

        # 3.2 Qualidade
        row_quality = QHBoxLayout()
        self.chk_quality = QCheckBox("Definir qualidade:")
        self.chk_quality.toggled.connect(self.on_quality_toggled)

        self.spin_quality = QSpinBox()
        self.spin_quality.setRange(10, 100)
        self.spin_quality.setSuffix("%")
        self.spin_quality.setValue(75)
        self.spin_quality.setEnabled(False)

        row_quality.addWidget(self.chk_quality)
        row_quality.addStretch()
        row_quality.addWidget(self.spin_quality)

        layout_props.addLayout(row_quality)

        main_layout.addWidget(grp_props)

        # Espaço antes dos botões
        main_layout.addStretch()

        # RODAPÉ: BOTÕES
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        self.btn_cancel = QPushButton("Cancelar")
        self.btn_cancel.setObjectName("SecondaryButton")
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton("Salvar Preferências")
        self.btn_save.setObjectName("PrimaryButton")
        self.btn_save.clicked.connect(self.save_and_close)

        buttons_layout.addWidget(self.btn_cancel)
        buttons_layout.addWidget(self.btn_save)

        main_layout.addLayout(buttons_layout)

        # Carregar tudo
        self.load_settings()

    # --- LÓGICA DE INTERFACE ---

    def on_resize_toggled(self, checked):
        self.spin_resize.setEnabled(checked)

    def on_quality_toggled(self, checked):
        self.spin_quality.setEnabled(checked)

    # --- PERSISTÊNCIA ---

    def load_settings(self):
        # 2. Auto
        is_full_auto = self.settings.value("full_auto", False, type=bool)
        self.chk_full_auto.setChecked(is_full_auto)
        

        # 3. Resize e 4. Qualidade (Mantém igual)
        has_resize = self.settings.value("use_resize", False, type=bool)
        self.chk_resize.setChecked(has_resize)
        self.spin_resize.setValue(self.settings.value("resize_value", 1920, type=int))

        has_quality = self.settings.value("use_quality", False, type=bool)
        self.chk_quality.setChecked(has_quality)
        self.spin_quality.setValue(self.settings.value("quality_value", 75, type=int))
        

    def save_and_close(self):
        # 2. Auto
        self.settings.setValue("full_auto", self.chk_full_auto.isChecked())
        # Não salvamos exposure/shadows pois não são usados no IM
        
        # 3. Resize e 4. Qualidade (Mantém igual)
        self.settings.setValue("use_resize", self.chk_resize.isChecked())
        self.settings.setValue("resize_value", self.spin_resize.value())

        self.settings.setValue("use_quality", self.chk_quality.isChecked())
        self.settings.setValue("quality_value", self.spin_quality.value())

        self.accept()
