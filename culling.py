import sys
import os
import shutil
from image_viewer import ZoomablePreview
from selector import ImageSelector
from collections import OrderedDict
from image_loader import ImageLoaderWorker
from PySide6.QtWidgets import (QApplication, QMainWindow, QListWidget, QListWidgetItem, 
                               QVBoxLayout, QWidget, QLabel, QPushButton, QFileDialog, 
                               QHBoxLayout, QProgressBar, QMessageBox, QLineEdit, QFrame, 
                               QAbstractItemView, QTextEdit)
from PySide6.QtGui import QIcon, QPixmap, QImageReader, QColor, QPainter, QBrush, QFont
from PySide6.QtCore import QSize, Qt, QThread, Signal, QRect, QEvent

# Silencia os avisos de metadados do Qt (Logs Fofoqueiros)
os.environ["QT_LOGGING_RULES"] = "qt.imageformats.tiff.warning=false"

# --- FUNÇÕES AUXILIARES (LÓGICA PURA) ---

def calcular_tamanho_proporcional(size_original, max_w, max_h):
    """Calcula novo tamanho mantendo aspect ratio."""
    if size_original.isEmpty():
        return QSize(max_w, max_h)
    
    w, h = size_original.width(), size_original.height()
    # Evita divisão por zero
    if w == 0 or h == 0: return QSize(max_w, max_h)

    ratio = min(max_w / w, max_h / h)
    return QSize(int(w * ratio), int(h * ratio))

def desenhar_overlay_rating(pixmap, rating):
    """Desenha o selo. Se rating for 0, retorna a imagem limpa."""
    if rating == 0:
        return pixmap
    
    resultado = pixmap.copy()
    painter = QPainter(resultado)
    painter.setRenderHint(QPainter.Antialiasing)

    tamanho_selo = 30
    margem = 5
    # Posiciona no canto superior direito
    x = resultado.width() - tamanho_selo - margem
    y = margem

    # Círculo Amarelo
    painter.setBrush(QBrush(QColor("#f1c40f")))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(x, y, tamanho_selo, tamanho_selo)

    # Número
    painter.setPen(QColor("#000000"))
    font = QFont("Arial", 12, QFont.Bold)
    painter.setFont(font)
    painter.drawText(QRect(x, y, tamanho_selo, tamanho_selo), Qt.AlignCenter, str(rating))

    painter.end()
    return resultado

class CopyWorker(QThread):
    progress_signal = Signal(str) # Envia texto para o log (ex: "Copiando 1/100")
    finished_signal = Signal(int) # Envia total copiado ao terminar

    def __init__(self, items, dest_folder):
        super().__init__()
        self.items = items # Dicionário {caminho: nota}
        self.dest_folder = dest_folder

    def run(self):
        total = len(self.items)
        count = 0
        try:
            # Garante que a pasta existe
            if not os.path.exists(self.dest_folder):
                os.makedirs(self.dest_folder)

            for i, (path, rating) in enumerate(self.items.items(), 1):
                filename = os.path.basename(path)
                dest_path = os.path.join(self.dest_folder, filename)
                
                # Copia preservando metadados (copy2)
                shutil.copy2(path, dest_path)
                
                count += 1
                # Envia atualização para o Log
                self.progress_signal.emit(f"Copiado: {count}/{total} - {filename}")
            
            self.finished_signal.emit(count)
            
        except Exception as e:
            self.progress_signal.emit(f"ERRO: {str(e)}")
            self.finished_signal.emit(0)

# --- APLICAÇÃO PRINCIPAL ---
class CullingApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Passa ou Repassa - v3.1 Dark & Linear")
        self.resize(1100, 750)
        self.setStyleSheet("background-color: #1e1e1e; color: #ecf0f1;") # Tema Base Escuro
        
        # Dados de Estado
        self.current_source_folder = ""
        self.current_dest_base = ""
        self.image_files = []
        self.selector = ImageSelector()
        self.thumbnails_cache = OrderedDict() # Guarda a imagem LIMPA original (LRU)
        self.cache_limit = 200 # Limite de imagens em memória RAM
        self.previews_cache = OrderedDict() # Cache para imagens grandes (720px)
        self.preview_cache_limit = 20       # Limite seguro de 40MB

        # --- LAYOUT PRINCIPAL ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # === 1. BLOCO DE CIMA (Preview | Controles) ===
        top_section = QWidget()
        top_layout = QHBoxLayout(top_section)
        top_layout.setContentsMargins(0, 0, 0, 0)

        # 1.1 Preview (Esquerda)
        self.preview_frame = ZoomablePreview()
        self.preview_frame.setStyleSheet("background-color: #000; border: 1px solid #333;")
        
        self.preview_frame.setMinimumSize(500, 400)
        
        # 1.2 Painel de Controle (Direita) - CORRIGIDO TEMA ESCURO
        controls_panel = QFrame()
        controls_panel.setFixedWidth(350)
        # CSS Corrigido para Dark Mode
        controls_panel.setStyleSheet("""
            QFrame { background-color: #2c3e50; border-radius: 8px; }
            QLabel { color: #ecf0f1; font-weight: bold; }
            QLineEdit { 
                background-color: #34495e; 
                color: #fff; 
                border: 1px solid #5d6d7e; 
                padding: 5px; 
                border-radius: 4px;
            }
        """)
        controls_layout = QVBoxLayout(controls_panel)
        controls_layout.setSpacing(15)

        # -- Botões e Inputs --
        self.btn_source = QPushButton("📂 1. Abrir Pasta Origem")
        self.estilizar_botao(self.btn_source, "#2980b9")
        self.input_source = QLineEdit()
        self.input_source.setPlaceholderText("Caminho da origem...")
        self.input_source.setReadOnly(True)
        
        self.btn_dest_base = QPushButton("📁 2. Pasta de Saída (Base)")
        self.estilizar_botao(self.btn_dest_base, "#7f8c8d")
        self.input_dest_base = QLineEdit()
        self.input_dest_base.setPlaceholderText("Ex: C:/Meus Documentos")
        self.input_dest_base.setReadOnly(True)

        lbl_nome = QLabel("3. Nome da nova pasta:")
        self.input_folder_name = QLineEdit()
        self.input_folder_name.setPlaceholderText("Ex: Aniversario_Leo")

        self.btn_export = QPushButton("🚀 CRIAR PASTA E COPIAR")
        self.estilizar_botao(self.btn_export, "#27ae60")
        self.btn_export.setFixedHeight(50) # Botão maior
        
        self.lbl_status = QLabel("Aguardando...")
        self.lbl_status.setAlignment(Qt.AlignCenter)
        self.lbl_status.setStyleSheet("color: #bdc3c7; font-weight: normal; font-size: 11px;")

        # Adiciona widgets ao painel
        controls_layout.addWidget(self.btn_source)
        controls_layout.addWidget(self.input_source)
        controls_layout.addWidget(self.btn_dest_base)
        controls_layout.addWidget(self.input_dest_base)
        
        # --- CAIXA DE LOG (NOVO) ---
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setPlaceholderText("Histórico de ações...")
        self.log_box.setStyleSheet("""
            background-color: #222; 
            color: #00ff00; 
            font-family: Consolas; 
            font-size: 10px; 
            border: 1px solid #444;
        """)
        controls_layout.addWidget(self.log_box)
        # ---------------------------

        controls_layout.addWidget(lbl_nome)
        controls_layout.addWidget(self.input_folder_name)
        controls_layout.addWidget(self.btn_export)
        controls_layout.addWidget(self.lbl_status)

        # --- BARRA DE FILTROS (SMART FILTERS) ---
        self.active_filters = set() # Conjunto vazio = Mostrar tudo
        
        filters_widget = QWidget()
        filters_widget.setStyleSheet("background: transparent;")
        filters_layout = QHBoxLayout(filters_widget)
        filters_layout.setContentsMargins(0, 10, 0, 0) # Margem superior para separar
        filters_layout.setSpacing(5)

        # Botão TUDO / CLASSIFICADAS (Toggle Dinâmico)
        self.btn_filter_all = QPushButton("Tudo") 
        self.btn_filter_all.setFixedHeight(30)
        self.btn_filter_all.clicked.connect(self.toggle_main_filter) 
        filters_layout.addWidget(self.btn_filter_all)

        # Botões Numéricos (0 a 5)
        self.filter_buttons = {}
        for i in range(6):
            btn = QPushButton(str(i))
            btn.setCheckable(True)
            btn.setFixedSize(30, 30)
            # Lambda com 'val=i' para capturar o valor correto no loop
            btn.clicked.connect(lambda checked, val=i: self.toggle_filter(val))
            self.filter_buttons[i] = btn
            filters_layout.addWidget(btn)

        controls_layout.addWidget(filters_widget)
        self.update_filter_visuals() # Define as cores iniciais
        # ----------------------------------------

        top_layout.addWidget(self.preview_frame, 1)
        top_layout.addWidget(controls_panel)

        # === 2. BLOCO DE BAIXO (Fita de Fotos) - CORRIGIDO LAYOUT ===
        self.filmstrip = QListWidget()
        self.filmstrip.setViewMode(QListWidget.IconMode)
        self.filmstrip.setFlow(QListWidget.LeftToRight) # Fluxo Horizontal
        self.filmstrip.setWrapping(False) # <--- O SEGREDO: NÃO QUEBRAR LINHA
        self.filmstrip.setFixedHeight(170)
        self.filmstrip.setIconSize(QSize(130, 130))
        self.filmstrip.setSpacing(10)
        self.filmstrip.setResizeMode(QListWidget.Adjust)
        self.filmstrip.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel) # Scroll suave
        self.filmstrip.setStyleSheet("""
            QListWidget { background-color: #2c2c2c; border-top: 2px solid #444; }
            QListWidget::item { color: #eee; }
            QListWidget::item:selected { background-color: #2980b9; border-radius: 5px; border: 2px solid #3498db;}
        """)
        self.filmstrip.installEventFilter(self)
        self.preview_frame.installEventFilter(self)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setStyleSheet("""
            QProgressBar { height: 4px; background-color: #222; border: none; }
            QProgressBar::chunk { background-color: #27ae60; }
        """)

        main_layout.addWidget(top_section, 1)
        main_layout.addWidget(self.filmstrip)
        main_layout.addWidget(self.progress)

        # --- CONEXÕES ---
        self.btn_source.clicked.connect(self.select_source_folder)
        self.btn_dest_base.clicked.connect(self.select_dest_base)
        self.btn_export.clicked.connect(self.export_files)
        self.filmstrip.currentItemChanged.connect(self.on_selection_changed)

        # Configuração do Novo Worker
        self.image_worker = ImageLoaderWorker()
        self.image_worker.signals.thumbnail_loaded.connect(self.add_thumbnail)
        self.image_worker.signals.preview_loaded.connect(self.update_preview_slot)
        self.image_worker.start()

    def closeEvent(self, event):
        """Garante que a Thread morra ao fechar a janela."""
        try:
            # Pára o worker de imagens
            if hasattr(self, "image_worker") and self.image_worker.isRunning():
                self.image_worker.stop()
            
            # Pára o worker de cópia se estiver rodando (opcional, mas seguro)
            if hasattr(self, "copy_thread") and self.copy_thread.isRunning():
                self.copy_thread.terminate() # Força parada pois cópia é bloqueante
        except Exception as e:
            print(f"Erro ao fechar: {e}")
            
        super().closeEvent(event)

    def estilizar_botao(self, btn, cor):
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {cor}; 
                color: white; 
                padding: 10px; 
                font-weight: bold; 
                border-radius: 4px;
                border: none;
            }}
            QPushButton:hover {{ background-color: {cor}99; }} 
        """)

    def log(self, text):
        """Adiciona mensagem na caixa de log com scroll automático."""
        self.log_box.append(text)
        # Scroll para o final
        scrollbar = self.log_box.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    # --- LÓGICA ---

    def select_source_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Selecionar Origem")
        if folder:
            self.current_source_folder = folder
            self.input_source.setText(folder)
            self.log(f"📂 Origem definida: {folder}")
            self.load_images(folder)

    def select_dest_base(self):
        folder = QFileDialog.getExistingDirectory(self, "Onde Salvar (Base)")
        if folder:
            self.current_dest_base = folder
            self.input_dest_base.setText(folder)
            self.log(f"📁 Destino base definido: {folder}")

    def load_images(self, folder):
        self.filmstrip.clear()
        self.selector.clear()
        self.thumbnails_cache.clear()
        self.preview_frame.clear()
        self.preview_frame.setText("Carregando...")

        extensoes = ('.jpg', '.jpeg', '.png', '.arw', '.cr2', '.nef', '.dng', '.bmp')
        self.image_files = [
            os.path.join(folder, f) for f in os.listdir(folder) 
            if f.lower().endswith(extensoes)
        ]
        self.image_files.sort()

        self.lbl_status.setText(f"{len(self.image_files)} fotos encontradas.")
        
        # Envia a lista para o Buffer Inteligente
        self.image_worker.set_paths(self.image_files)
        
        # Reseta visual
        self.progress.setVisible(False)
        self.filmstrip.setFocus()

    def add_thumbnail(self, path, pixmap):
        # Gerenciamento do Cache LRU
        if path in self.thumbnails_cache:
            self.thumbnails_cache.move_to_end(path) # Marca como usado recentemente
        self.thumbnails_cache[path] = pixmap
        
        # Se estourar o limite, remove o mais antigo (o primeiro da fila)
        if len(self.thumbnails_cache) > self.cache_limit:
            self.thumbnails_cache.popitem(last=False)
        
        # Verifica se já tem nota salva no selector e aplica o desenho
        rating_atual = self.selector.get_rating(path)
        if rating_atual > 0:
            pixmap = self.selector.apply_overlay(pixmap, rating_atual)

        item = QListWidgetItem(os.path.basename(path))
        item.setIcon(QIcon(pixmap))
        item.setData(Qt.UserRole, path)
        self.filmstrip.addItem(item)

    def update_preview_slot(self, path, pixmap):
        """Recebe a imagem grande carregada pelo Worker e exibe."""
        # 1. Guarda no Cache LRU
        if path in self.previews_cache:
            self.previews_cache.move_to_end(path)
        self.previews_cache[path] = pixmap
        
        if len(self.previews_cache) > self.preview_cache_limit:
            self.previews_cache.popitem(last=False)

        # 2. Se for a foto que o usuário está olhando agora, exibe
        current = self.filmstrip.currentItem()
        if current and current.data(Qt.UserRole) == path:
            self.preview_frame.setPixmap(pixmap)
            self.preview_frame.setText("")

    def on_loading_finished(self):
        self.progress.setVisible(False)
        self.lbl_status.setText("Use 1-5 para classificar (0 limpa).")
        if self.filmstrip.count() > 0:
            self.filmstrip.setCurrentRow(0)
            self.filmstrip.setFocus() # Garante foco no inicio

    def on_selection_changed(self, current, previous):
        if not current: return

        # --- NOVO: Força sair do zoom ao trocar de foto ---
        self.preview_frame.stop_zoom_mode()
        # --------------------------------------------------
        
        # Scroll suave para centralizar
        self.filmstrip.scrollToItem(current, QAbstractItemView.PositionAtCenter)

        path = current.data(Qt.UserRole)
        
        # Avisa o Worker qual é a posição atual para ele gerenciar o buffer e carregar o preview
        row = self.filmstrip.row(current)
        self.image_worker.update_position(row)
        
        # Tenta carregar do cache instantaneamente
        if path in self.previews_cache:
            self.preview_frame.setPixmap(self.previews_cache[path])
            self.previews_cache.move_to_end(path) # Renova a prioridade
        else:
            self.preview_frame.clear()
            self.preview_frame.setText("Carregando...")

        self.lbl_status.setText(f"Vendo: {os.path.basename(path)}")

    def eventFilter(self, obj, event):
        is_target = (obj is self.filmstrip or obj is self.preview_frame)
        
        if is_target and event.type() == QEvent.KeyPress:
            key = event.key()
            
            # 1. Lógica do Zoom (Tecla Z)
            if event.text().lower() == 'z':
                self.toggle_zoom_logic()
                return True
            
            # 2. Lógica das Setas (O Guarda de Trânsito Blindado)
            if key in (Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down):
                
                # CENÁRIO A: Tem Zoom -> Move a imagem
                if self.preview_frame._is_zoomed:
                    self.preview_frame.manual_scroll(key)
                    return True 
                
                # CENÁRIO B: Não tem Zoom e o foco está na Imagem -> Navega na lista manualmente
                # Isso evita chamar setFocus() durante um evento de tecla (o que causava o crash)
                if obj is self.preview_frame:
                    row = self.filmstrip.currentRow()
                    count = self.filmstrip.count()
                    
                    if count > 0:
                        if key in (Qt.Key_Left, Qt.Key_Up):
                            row = max(0, row - 1)
                        elif key in (Qt.Key_Right, Qt.Key_Down):
                            row = min(count - 1, row + 1)
                        
                        self.filmstrip.setCurrentRow(row)
                    
                    return True # Importante: Dizemos ao Qt "Já resolvi, não faça mais nada"

            # 3. Lógica das Notas (1-5)
            if self.process_rating_key(event):
                return True
                
        return super().eventFilter(obj, event)

    def process_rating_key(self, event):
        # Lógica centralizada de classificação
        key_char = event.text()
        valid_keys = {'1': 1, '2': 2, '3': 3, '4': 4, '5': 5, '0': 0}

        if key_char not in valid_keys:
            return False  # Não é tecla de nota, deixa o Qt lidar (ex: setas)

        current_item = self.filmstrip.currentItem()
        if not current_item:
            return False

        path = current_item.data(Qt.UserRole)
        novo_rating = valid_keys[key_char]

        # --- LÓGICA DE TOGGLE (Apertar a mesma tecla remove a nota) ---
        rating_atual = self.selector.get_rating(path)
        if novo_rating == rating_atual and novo_rating != 0:
            novo_rating = 0 # Desmarca
        # -------------------------------------------------------------

        # 1. Atualiza Lógica (Selector)
        self.selector.set_rating(path, novo_rating)

        # 2. Atualiza Visual
        if path in self.thumbnails_cache:
            pix_limpo = self.thumbnails_cache[path]
            # Se novo_rating for 0, o apply_overlay já devolve a imagem limpa
            pix_novo = self.selector.apply_overlay(pix_limpo, novo_rating)
            current_item.setIcon(QIcon(pix_novo))

        # 3. Revalida se a foto ainda deve aparecer na tela
        self.apply_filters()
        self.update_filter_visuals()
        
        return True # Confirmamos que tratamos o evento
    
    def toggle_zoom_logic(self):
        item = self.filmstrip.currentItem()
        if not item: return

        # SAIR DO ZOOM
        if self.preview_frame._is_zoomed:
            self.preview_frame.stop_zoom_mode()
            self.lbl_status.setText(f"Vendo: {os.path.basename(item.data(Qt.UserRole))}")
            self.filmstrip.setFocus()
            return

        # ENTRAR NO ZOOM
        path = item.data(Qt.UserRole)
        self.lbl_status.setText("Carregando Zoom HD...")
        QApplication.processEvents()

        full_pix = self.image_worker.get_full_resolution_image(path)
        
        if full_pix:
            self.preview_frame.start_zoom_mode(full_pix)
            self.lbl_status.setText("Modo Zoom: Use Scroll ou Botões")
        else:
            self.lbl_status.setText("Erro ao carregar zoom.")

    # --- LÓGICA DE FILTROS ---

    def toggle_filter(self, rating):
        """Adiciona ou remove uma nota do filtro."""
        if rating in self.active_filters:
            self.active_filters.remove(rating)
        else:
            self.active_filters.add(rating)
        
        self.update_filter_visuals()
        self.apply_filters()

    def toggle_main_filter(self):
        """Lógica inteligente: Tudo <-> Classificadas."""
        # Verifica se existe ALGUMA foto com nota no sistema
        tem_classificadas = any(r > 0 for r in self.selector.get_selected_items().values())

        if not self.active_filters:
            # Estamos vendo "Tudo".
            # Se tiver fotos classificadas, o botão dizia "Classificadas", então filtramos 1-5.
            if tem_classificadas:
                self.active_filters = {1, 2, 3, 4, 5}
            # Se não tem classificadas, o botão dizia "Tudo", então não faz nada (já está em tudo).
        else:
            # Estamos filtrando algo. O botão dizia "Tudo" (Reset). Limpamos o filtro.
            self.active_filters.clear()
        
        self.update_filter_visuals()
        self.apply_filters()

    def update_filter_visuals(self):
        """Atualiza texto e cor: Classificadas (Verde) / Tudo (Laranja)."""
        is_empty = (len(self.active_filters) == 0)
        
        # Verifica se existe ALGUMA foto com nota > 0
        tem_classificadas = any(r > 0 for r in self.selector.get_selected_items().values())
        
        # Estilos
        style_green = "background-color: #27ae60; color: white; border: none; font-weight: bold; border-radius: 4px;"
        style_gray = "background-color: #34495e; color: #bdc3c7; border: 1px solid #5d6d7e; border-radius: 4px;"
        style_orange = "background-color: #e67e22; color: white; border: none; font-weight: bold; border-radius: 4px;"

        # Lógica do Botão Principal
        if is_empty:
            # Sem filtro ativo (Vendo todas as imagens)
            if tem_classificadas:
                # Tem notas? Botão vira "Classificadas" -> Fica VERDE
                self.btn_filter_all.setText("Classificadas")
                self.btn_filter_all.setStyleSheet(style_green)
            else:
                # Não tem notas? Botão fica "Tudo" -> Fica LARANJA (Correção Solicitada)
                self.btn_filter_all.setText("Tudo")
                self.btn_filter_all.setStyleSheet(style_orange)
        else:
            # Com filtro ativo.
            # Botão vira Reset ("Tudo") -> Fica LARANJA
            self.btn_filter_all.setText("Tudo")
            self.btn_filter_all.setStyleSheet(style_orange)

        # Botões Numéricos (Mantém Verde se ativo, Cinza se inativo)
        for i, btn in self.filter_buttons.items():
            is_selected = i in self.active_filters
            btn.setStyleSheet(style_green if is_selected else style_gray)
            btn.setChecked(is_selected)

    def apply_filters(self):
        """Aplica a visibilidade na Fita de Fotos."""
        count = self.filmstrip.count()
        
        # Se vazio, mostra tudo (Otimização)
        if not self.active_filters:
            for i in range(count):
                self.filmstrip.item(i).setHidden(False)
            return

        # Filtra item por item
        for i in range(count):
            item = self.filmstrip.item(i)
            path = item.data(Qt.UserRole)
            rating = self.selector.get_rating(path) # Pega a nota real
            
            # Se a nota estiver no conjunto, mostra. Senão, esconde.
            should_show = rating in self.active_filters
            item.setHidden(not should_show)

    def export_files(self):
        # 1. Recupera TUDO que tem nota
        all_rated_items = self.selector.get_selected_items()
        
        # 2. APLICA A LÓGICA DO FILTRO NA EXPORTAÇÃO
        if self.active_filters:
            # Se tiver filtro ativo, pegamos apenas o que coincide
            selected_items = {
                path: rating 
                for path, rating in all_rated_items.items() 
                if rating in self.active_filters
            }
        else:
            # Se o filtro estiver vazio (Modo "Tudo"), exporta tudo que tem nota
            selected_items = all_rated_items

        # 3. Validações Padrão
        if not selected_items:
            # Mensagem personalizada dependendo do contexto
            if self.active_filters:
                msg = "Nenhuma foto com essa classificação foi encontrada!"
            else:
                msg = "Nenhuma foto classificada para exportar!"
            QMessageBox.warning(self, "Ops", msg)
            return

        if not self.current_dest_base:
            QMessageBox.warning(self, "Ops", "Selecione a Pasta de Saída!")
            return
        folder_name = self.input_folder_name.text().strip()
        if not folder_name:
            QMessageBox.warning(self, "Ops", "Digite um nome para a pasta!")
            return

        final_path = os.path.join(self.current_dest_base, folder_name)
        
        # Bloqueia botão para não clicar 2x
        self.btn_export.setEnabled(False)
        self.btn_export.setText("⏳ COPIANDO...")
        self.log(f"🚀 Iniciando cópia para: {final_path}")

        # Inicia Worker de Cópia
        self.copy_thread = CopyWorker(selected_items, final_path)
        self.copy_thread.progress_signal.connect(self.log) # Liga o sinal ao Log
        self.copy_thread.finished_signal.connect(self.on_copy_finished)
        self.copy_thread.start()

    def on_copy_finished(self, count):
        """Chamado quando a thread termina."""
        self.btn_export.setEnabled(True)
        self.btn_export.setText("🚀 CRIAR PASTA E COPIAR")
        
        if count > 0:
            QMessageBox.information(self, "Sucesso", f"Processo finalizado!\n{count} fotos copiadas.")
            self.log(f"✅ SUCESSO: {count} fotos copiadas.")
        else:
            self.log("❌ Falha ou nenhuma foto copiada.")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CullingApp()
    window.show()
    sys.exit(app.exec())