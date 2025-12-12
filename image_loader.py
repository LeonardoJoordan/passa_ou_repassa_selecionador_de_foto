import os
import rawpy
from PySide6.QtCore import QThread, Signal, QObject, QSize, QMutex, QWaitCondition, Qt
from PySide6.QtGui import QImageReader, QPixmap, QImage

class LoaderSignals(QObject):
    # Sinais para comunicar com a interface (Main Thread)
    thumbnail_loaded = Signal(str, QPixmap)  # Caminho, Imagem
    preview_loaded = Signal(str, QPixmap)    # Caminho, Imagem
    
class ImageLoaderWorker(QThread):
    def __init__(self):
        super().__init__()
        self.signals = LoaderSignals()
        
        # --- CONFIGURAÇÕES DE PERFORMANCE (O SEGREDO) ---
        self.thumb_size = QSize(160, 120)  # Tamanho nativo EXIF comum
        self.preview_size = QSize(720, 720) # Limite definido por você
        
        # Buffer (Janela Deslizante)
        self.buffer_range = (15, 30) # (Atrás, Frente)
        self.loaded_thumbs = set()   # Rastrea o que já carregamos para não repetir
        
        # Estado
        self.all_paths = []
        self.current_index = 0
        self.running = True
        self.needs_update = False
        
        # Sincronização
        self.mutex = QMutex()
        self.condition = QWaitCondition()

    def set_paths(self, paths):
        """Recebe a lista bruta de arquivos ao abrir a pasta."""
        self.mutex.lock()
        self.all_paths = paths
        self.loaded_thumbs.clear()
        self.current_index = 0
        self.needs_update = True
        self.condition.wakeOne()
        self.mutex.unlock()

    def update_position(self, index):
        """O Main avisa: 'O usuário pulou para a foto X'."""
        self.mutex.lock()
        self.current_index = index
        self.needs_update = True
        self.condition.wakeOne()
        self.mutex.unlock()

    def set_max_preview_size(self, size: QSize):
        """Define o novo limite máximo de tamanho para o preview."""
        self.mutex.lock()
        # Se o tamanho não mudou, não faz nada
        if self.preview_size == size:
            self.mutex.unlock()
            return

        self.preview_size = size
        # Dispara uma atualização para recarregar o preview atual, se necessário
        self.needs_update = True
        self.condition.wakeOne()
        self.mutex.unlock()

    def stop(self):
        self.running = False
        self.condition.wakeOne()
        self.wait()

    def run(self):
        """O Loop Infinito Inteligente."""
        while self.running:
            self.mutex.lock()
            
            # Se não tem nada novo para fazer, dorme para economizar CPU
            if not self.needs_update:
                self.condition.wait(self.mutex)
            
            if not self.running:
                self.mutex.unlock()
                break

            # Copia dados para trabalhar sem travar o mutex
            index = self.current_index
            paths = self.all_paths
            self.needs_update = False
            self.mutex.unlock()

            if not paths:
                continue

            # --- ESTRATÉGIA DE PRIORIDADE (ALGORITMO) ---
            
            # 1. Prioridade Máxima: O Preview da Imagem Atual (Para o usuário ver agora)
            if 0 <= index < len(paths):
                self._load_preview(paths[index])

            # 2. Prioridade Alta: O Preview da Próxima Imagem (Preload)
            if index + 1 < len(paths):
                self._load_preview(paths[index + 1])

            # 3. Prioridade Média: Thumbnails da Janela Deslizante
            # Calcula a janela: [start ... index ... end]
            start = max(0, index - self.buffer_range[0])
            end = min(len(paths), index + self.buffer_range[1])

            # Carrega thumbnails que faltam nessa janela
            for i in range(start, end):
                if not self.running: break
                if self.needs_update: break # Usuário mudou rápido demais, aborta e recalcula!
                
                path = paths[i]
                if path not in self.loaded_thumbs:
                    self._load_thumbnail(path)
                    self.loaded_thumbs.add(path)

    def _extract_raw_preview(self, path):
        """Usa o rawpy para extrair o JPEG embutido sem processar o RAW."""
        try:
            with rawpy.imread(path) as raw:
                # Tenta extrair a thumbnail (geralmente é o preview Full HD embutido)
                thumb = raw.extract_thumb()
            
            # Converte os bytes extraídos direto para QImage
            if thumb.format == rawpy.ThumbFormat.JPEG:
                img = QImage.fromData(thumb.data)
                return img
            return None
        except Exception as e:
            print(f"Erro ao ler RAW {path}: {e}")
            return None

    def _load_preview(self, path):
        """Carrega a imagem 'grande' (Max 720px), suportando RAW e JPG."""
        try:
            img = None
            # SE FOR RAW: Usa a técnica do Photo Mechanic (rawpy)
            if path.lower().endswith(('.arw', '.cr2', '.nef', '.dng', '.orf')):
                img = self._extract_raw_preview(path)
                
                # Se conseguiu ler o RAW, redimensiona para o tamanho de preview
                if img and not img.isNull():
                    new_size = self._calculate_aspect_ratio(img.size(), self.preview_size)
                    img = img.scaled(new_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.signals.preview_loaded.emit(path, QPixmap.fromImage(img))
                    return # Sai da função, trabalho feito

            # SE FOR JPG/PNG (ou se o RAW falhou): Usa o método padrão rápido do Qt
            reader = QImageReader(path)
            orig_size = reader.size()
            scaled_size = self._calculate_aspect_ratio(orig_size, self.preview_size)
            reader.setScaledSize(scaled_size)
            
            # Auto-rotação para JPGs
            reader.setAutoTransform(True)

            img_data = reader.read()
            if not img_data.isNull():
                self.signals.preview_loaded.emit(path, QPixmap.fromImage(img_data))
                
        except Exception as e:
            print(f"Erro preview {path}: {e}")

    def _load_thumbnail(self, path):
        """Carrega a miniatura para a fita (Max 160px)."""
        try:
            img = None
            # SE FOR RAW
            if path.lower().endswith(('.arw', '.cr2', '.nef', '.dng', '.orf')):
                img = self._extract_raw_preview(path)
                
                if img and not img.isNull():
                    new_size = self._calculate_aspect_ratio(img.size(), self.thumb_size)
                    # Usa FastTransformation para thumbnails (ganha performance)
                    img = img.scaled(new_size, Qt.KeepAspectRatio, Qt.FastTransformation)
                    self.signals.thumbnail_loaded.emit(path, QPixmap.fromImage(img))
                    return

            # SE FOR JPG/PNG
            reader = QImageReader(path)
            orig_size = reader.size()
            scaled_size = self._calculate_aspect_ratio(orig_size, self.thumb_size)
            reader.setScaledSize(scaled_size)
            
            img_data = reader.read()
            if not img_data.isNull():
                self.signals.thumbnail_loaded.emit(path, QPixmap.fromImage(img_data))
        except Exception:
            pass

    def _calculate_aspect_ratio(self, current, maximum):
        if current.isEmpty(): return maximum
        w, h = current.width(), current.height()
        ratio = min(maximum.width() / w, maximum.height() / h)
        return QSize(int(w * ratio), int(h * ratio))
    
    def get_full_resolution_image(self, path):
        """Método síncrono para buscar a imagem em resolução máxima (para Zoom)."""
        try:
            img = None
            # 1. Tenta RAW
            if path.lower().endswith(('.arw', '.cr2', '.nef', '.dng', '.orf')):
                img = self._extract_raw_preview(path)
                # Nota: Não redimensionamos aqui!
            
            # 2. Tenta JPG/PNG se não for RAW ou se RAW falhou
            if img is None:
                reader = QImageReader(path)
                reader.setAutoTransform(True)
                # Lê direto (sem setScaledSize)
                img_data = reader.read()
                if not img_data.isNull():
                    img = img_data

            if img and not img.isNull():
                return QPixmap.fromImage(img)
            return None

        except Exception as e:
            print(f"Erro zoom {path}: {e}")
            return None