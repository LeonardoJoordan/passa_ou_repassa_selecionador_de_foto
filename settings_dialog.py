import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QCheckBox, QGroupBox,
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
        lbl_title = QLabel("Configurações do Processamento")
        lbl_title.setObjectName("HeaderTitle")

        lbl_subtitle = QLabel("Ajuste o motor de edição, correções automáticas e parâmetros de exportação.")
        lbl_subtitle.setObjectName("HeaderSubtitle")
        lbl_subtitle.setWordWrap(True)

        header_layout.addWidget(lbl_title)
        header_layout.addWidget(lbl_subtitle)
        main_layout.addLayout(header_layout)

        # Linha separadora
        line = QFrame()
        line.setObjectName("line")
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)

        # 1. SELEÇÃO DO MOTOR
        row_engine = QHBoxLayout()

        lbl_engine = QLabel("Motor para edição:")
        lbl_engine.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self.combo_engine = QComboBox()
        self.combo_engine.addItems(["[ Sem edição ]", "RawTherapee", "Darktable", "ImageMagick"])

        row_engine.addWidget(lbl_engine)
        row_engine.addStretch()
        row_engine.addWidget(self.combo_engine)

        main_layout.addLayout(row_engine)

        # 2. GRUPO: AJUSTES AUTOMÁTICOS
        grp_auto = QGroupBox("Correção de Imagem (Automático)")
        layout_auto = QVBoxLayout(grp_auto)
        layout_auto.setSpacing(8)

        # 2.1 Full Auto
        self.chk_full_auto = QCheckBox("Full Auto (Ajuste Completo)")
        self.chk_full_auto.toggled.connect(self.on_full_auto_toggled)
        layout_auto.addWidget(self.chk_full_auto)

        # 2.2 Itens Granulares
        layout_subs = QHBoxLayout()
        layout_subs.setContentsMargins(18, 0, 0, 0)  # Indentação visual

        self.chk_exposure = QCheckBox("Exposição")
        self.chk_shadows = QCheckBox("Sombras")
        self.chk_highlights = QCheckBox("Realces")

        # Estados manuais "lembrados" para quando sair do Full Auto
        self._prev_exposure = False
        self._prev_shadows = False
        self._prev_highlights = False

        layout_subs.addWidget(self.chk_exposure)
        layout_subs.addWidget(self.chk_shadows)
        layout_subs.addWidget(self.chk_highlights)
        layout_subs.addStretch()

        layout_auto.addLayout(layout_subs)

        main_layout.addWidget(grp_auto)

        # 3. GRUPO: PROPRIEDADES DO ARQUIVO
        grp_props = QGroupBox("Exportação")
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

    def on_full_auto_toggled(self, checked):
        """Se Full Auto estiver marcado, bloqueia e marca os outros."""
        if checked:
            # Guarda o estado atual (manual) antes de forçar tudo ligado
            self._prev_exposure = self.chk_exposure.isChecked()
            self._prev_shadows = self.chk_shadows.isChecked()
            self._prev_highlights = self.chk_highlights.isChecked()

            # Full Auto ativa tudo e trava os controles manuais
            self.chk_exposure.setChecked(True)
            self.chk_shadows.setChecked(True)
            self.chk_highlights.setChecked(True)

            self.chk_exposure.setEnabled(False)
            self.chk_shadows.setEnabled(False)
            self.chk_highlights.setEnabled(False)
        else:
            # Saiu do Full Auto: libera os controles manuais
            self.chk_exposure.setEnabled(True)
            self.chk_shadows.setEnabled(True)
            self.chk_highlights.setEnabled(True)

            # Restaura como o usuário tinha deixado antes do Full Auto
            self.chk_exposure.setChecked(self._prev_exposure)
            self.chk_shadows.setChecked(self._prev_shadows)
            self.chk_highlights.setChecked(self._prev_highlights)

    def on_resize_toggled(self, checked):
        self.spin_resize.setEnabled(checked)

    def on_quality_toggled(self, checked):
        self.spin_quality.setEnabled(checked)

    # --- PERSISTÊNCIA ---

    def load_settings(self):
        # 1. Engine
        self.combo_engine.setCurrentIndex(
            self.settings.value("engine_index", 0, type=int)
        )

        # 2. Auto
        is_full_auto = self.settings.value("full_auto", False, type=bool)

        # Carrega primeiro os valores individuais
        self.chk_exposure.setChecked(self.settings.value("auto_exposure", False, type=bool))
        self.chk_shadows.setChecked(self.settings.value("auto_shadows", False, type=bool))
        self.chk_highlights.setChecked(self.settings.value("auto_highlights", False, type=bool))

        # Guarda esse estado como "manual" padrão
        self._prev_exposure = self.chk_exposure.isChecked()
        self._prev_shadows = self.chk_shadows.isChecked()
        self._prev_highlights = self.chk_highlights.isChecked()

        # Por último aplica o Full Auto (vai chamar on_full_auto_toggled)
        self.chk_full_auto.setChecked(is_full_auto)

        # 3. Resize
        has_resize = self.settings.value("use_resize", False, type=bool)
        self.chk_resize.setChecked(has_resize)
        self.spin_resize.setValue(
            self.settings.value("resize_value", 1920, type=int)
        )

        # 4. Qualidade
        has_quality = self.settings.value("use_quality", False, type=bool)
        self.chk_quality.setChecked(has_quality)
        self.spin_quality.setValue(
            self.settings.value("quality_value", 75, type=int)
        )

    def save_and_close(self):
        # 1. Engine
        self.settings.setValue("engine_index", self.combo_engine.currentIndex())

        # 2. Auto
        self.settings.setValue("full_auto", self.chk_full_auto.isChecked())
        self.settings.setValue("auto_exposure", self.chk_exposure.isChecked())
        self.settings.setValue("auto_shadows", self.chk_shadows.isChecked())
        self.settings.setValue("auto_highlights", self.chk_highlights.isChecked())

        # 3. Resize
        self.settings.setValue("use_resize", self.chk_resize.isChecked())
        self.settings.setValue("resize_value", self.spin_resize.value())

        # 4. Qualidade
        self.settings.setValue("use_quality", self.chk_quality.isChecked())
        self.settings.setValue("quality_value", self.spin_quality.value())

        self.accept()
