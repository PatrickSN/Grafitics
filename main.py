from ui.gui import StatApp

from tkinter import messagebox
import shutil
import subprocess
import platform
import urllib.request

def check_r_installed():
    return shutil.which("R") is not None

def install_r_linux():
    try:
        subprocess.run(["sudo", "apt-get", "update"], check=True)
        subprocess.run(["sudo", "apt-get", "install", "-y", "r-base"], check=True)
        messagebox.showwarning("Grafitics-Message","✅ R instalado com sucesso!")
    except subprocess.CalledProcessError as e:
        messagebox.showwarning("Grafitics-Message","❌ Erro ao instalar o R:", e)

def install_r_windows():
    url = "https://cloud.r-project.org/bin/windows/base/R-4.5.1-win.exe"
    installer = "R-installer.exe"
    
    messagebox.showwarning("Grafitics-Message","⬇️ Baixando instalador do R...")
    urllib.request.urlretrieve(url, installer)

    messagebox.showwarning("Grafitics-Message","🚀 Executando instalador...")
    subprocess.run([installer, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"], check=True)

    messagebox.showwarning("Grafitics-Message","✅ R instalado com sucesso!")

def install_r_mac():
    try:
        subprocess.run(["brew", "install", "r"], check=True)
        messagebox.showwarning("Grafitics-Message","✅ R instalado com sucesso!")
    except subprocess.CalledProcessError as e:
        messagebox.showwarning("Grafitics-Message","❌ Erro ao instalar o R:", e)

def ensure_r_installed():
    if check_r_installed():
        pass
    else:
        messagebox.showwarning("Grafitics-Message","⚠️ R não encontrado. Instalando...")
        os_type = platform.system()
        if os_type == "Linux":
            install_r_linux()
        elif os_type == "Windows":
            install_r_windows()
        elif os_type == "Darwin":  # macOS
            install_r_mac()
        else:
            messagebox.showwarning("Grafitics-Message","❌ Sistema não suportado para instalação automática. Por favor, instale o R manualmente.")



if __name__ == "__main__":
    ensure_r_installed()
    app = StatApp()
    app.mainloop()
