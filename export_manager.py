import os
import shutil
import platform
import subprocess

# Detecta o sistema operacional uma única vez
IS_WINDOWS = platform.system() == "Windows"

def export_file(source_path, dest_folder, settings):
    """
    Função Mestra de Exportação.
    
    Args:
        source_path (str): Caminho original da foto.
        dest_folder (str): Pasta onde a foto deve ser salva.
        settings (dict): Dicionário contendo:
            - 'engine': 'ImageMagick', 'RawTherapee' ou '[ Sem edição ]'
            - 'quality': int (0-100)
            - 'resize': int (largura em px) ou None
            - 'auto_exposure': bool
            etc.
            
    Returns:
        bool: True se sucesso, False se falha.
    """
    # Garante que o nome do arquivo seja preservado
    filename = os.path.basename(source_path)
    final_dest_path = os.path.join(dest_folder, filename)
    
    engine = settings.get('engine_name', '[ Sem edição ]')

    try:
        if engine == 'ImageMagick':
            return _process_imagemagick(source_path, final_dest_path, settings)
        
        elif engine == 'RawTherapee':
            # Placeholder para o futuro
            print(f"⚠️ Motor RawTherapee ainda não implementado. Usando cópia simples.")
            return _copy_simple(source_path, final_dest_path)
            
        else:
            # Padrão: Cópia simples (fiel aos metadados)
            return _copy_simple(source_path, final_dest_path)

    except Exception as e:
        print(f"❌ Erro crítico ao exportar {filename}: {e}")
        return False

def _copy_simple(src, dst):
    """Cópia burra: apenas duplica o arquivo."""
    try:
        shutil.copy2(src, dst)
        return True
    except Exception as e:
        print(f"Erro na cópia simples: {e}")
        return False

def _process_imagemagick(src, dst, settings):
    """
    Constrói e executa o comando do ImageMagick (magick / convert).
    """
    # 1. Define o executável base dependendo do OS
    # No Windows moderno é 'magick', no Linux geralmente é 'convert' ou 'magick'
    executable = "magick" if IS_WINDOWS else "convert"
    
    # 2. Inicia a lista de comandos
    cmd = [executable, src]
    
    # --- APLICAR AJUSTES (IMPLEMENTAREMOS A LÓGICA DETALHADA DEPOIS) ---
    # Por enquanto, é apenas um teste de passagem (pass-through)
    
    # Exemplo: Se tiver resize
    if settings.get('use_resize') and settings.get('resize_value'):
        val = settings['resize_value']
        cmd.extend(["-resize", f"{val}x{val}>"]) # '>' significa "só diminua, não aumente"

    # Define qualidade (para JPG)
    if settings.get('use_quality'):
        val = settings['quality_value']
        cmd.extend(["-quality", str(val)])

    # Define destino
    cmd.append(dst)
    
    # 3. Executa
    try:
        # shell=False é mais seguro e evita problemas de escape de strings
        subprocess.run(cmd, check=True, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Erro ImageMagick: {e.stderr.decode('utf-8', errors='ignore')}")
        return False
    except FileNotFoundError:
        print(f"ERRO: ImageMagick não encontrado no sistema (comando '{executable}').")
        return False