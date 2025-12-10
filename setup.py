from cx_Freeze import setup, Executable
import sys

# Dependências
build_exe_options = {
    "packages": ["PySide6", "rawpy", "os", "sys", "shutil"],
    "includes": ["PySide6.QtCore", "PySide6.QtGui", "PySide6.QtWidgets"],
    "include_files": [
        "image_viewer.py",
        "selector.py", 
        "image_loader.py"
    ],
    "excludes": ["tkinter"],
}

# Configuração base (cx_Freeze 7.x usa "gui" ao invés de "Win32GUI")
base = None
if sys.platform == "win32":
    base = "gui"  # Esconde o console no Windows

setup(
    name="PassaOuRepassa",
    version="3.1",
    description="Sistema de culling de fotos",
    options={"build_exe": build_exe_options},
    executables=[Executable(
        "culling.py",
        base=base,
        target_name="PassaOuRepassa.exe",
        icon="icon.ico"
    )]
)