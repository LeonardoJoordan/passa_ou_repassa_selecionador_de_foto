import os
import shutil
import platform
import subprocess
import tempfile

# Detecta o sistema operacional uma única vez
IS_WINDOWS = platform.system() == "Windows"

def export_file(source_path, dest_folder, settings):
    """
    Função Mestra de Exportação (Versão Lite).
    """
    filename = os.path.basename(source_path)
    final_dest_path = os.path.join(dest_folder, filename)
    
    engine = settings.get('engine_name', '[ Sem edição ]')

    try:
        if engine == 'ImageMagick':
            return _process_imagemagick(source_path, final_dest_path, settings)
        else:
            # Padrão: Cópia simples
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
    Constrói e executa o comando do ImageMagick.
    Funcionalidades: Full Auto, Resize, Qualidade.
    """
    executable = "magick" if IS_WINDOWS else "convert"
    cmd = [executable, src]
    
    # --- 1. FULL AUTO (Correção Geral) ---
    if settings.get('full_auto'):
        # O combo que validamos e funcionou
        cmd.append("-auto-gamma")
        cmd.extend(["-contrast-stretch", "0.1%x0.1%"])
        cmd.extend(["-modulate", "100,110"])
        #cmd.extend(["-unsharp", "0x0.75+0.75+0.008"])
    
    # (Removemos o 'else' com os controles manuais que não funcionam bem)

    # --- 2. REDIMENSIONAR ---
    if settings.get('use_resize') and settings.get('resize_value'):
        val = settings['resize_value']
        cmd.extend(["-resize", f"{val}x{val}>"]) 

    # --- 3. QUALIDADE (JPG) ---
    if settings.get('use_quality'):
        val = settings['quality_value']
        cmd.extend(["-quality", str(val)])

    cmd.append(dst)
    
    # Parâmetros de execução (aplica a flag no Windows para evitar o console piscando)
    run_params = {}
    if IS_WINDOWS:
        # SW_HIDE = 0 | CREATE_NO_WINDOW = 0x08000000
        # https://docs.microsoft.com/en-us/windows/win32/procthread/creation-flags
        # Adiciona flag para evitar que a tela preta (console) apareça
        CREATE_NO_WINDOW = 0x08000000
        run_params['creationflags'] = CREATE_NO_WINDOW
    
    try:
        # Executa o comando, aplicando as flags de criação (apenas no Windows)
        subprocess.run(cmd, check=True, capture_output=True, **run_params)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Erro ImageMagick: {e.stderr.decode('utf-8', errors='ignore')}")
        return False
    except FileNotFoundError:
        print(f"ERRO: ImageMagick ({executable}) não encontrado.")
        return False
    