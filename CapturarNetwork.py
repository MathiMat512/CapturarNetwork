import asyncio
import json
import time
from urllib.parse import urlparse
import threading
import tkinter as tk
from tkinter import messagebox
from playwright.async_api import async_playwright
import sys
import os
import glob

# ========================== CONFIGURACIÓN PLAYWRIGHT ==========================
def get_chromium_path():
    """Obtiene la ruta de Chromium portátil"""
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    chromium_rel = os.path.join(base_path, "ms-playwright", "chromium-1187", "chrome-win", "chrome.exe")
    
    if os.path.exists(chromium_rel):
        print(f"✅ Chromium encontrado en: {chromium_rel}")
        return chromium_rel
    else:
        print("❌ Chromium no encontrado")
        return None

# ========================== LÓGICA PRINCIPAL ==========================
async def main_with_url(url):
    if not url.startswith("http"):
        url = "http://" + url

    entries = {}
    estado = "✔️"

    parsed_url = urlparse(url)
    domain = parsed_url.hostname or "output"
    if domain.startswith("www."):
        domain = domain[4:]

    # Obtener la ruta de Chromium
    chromium_path = get_chromium_path()

    async with async_playwright() as p:
        try:
            print(f"🚀 Lanzando Chromium desde: {chromium_path}")
            
            # Lanzar Chromium con la ruta específica
            browser = await p.chromium.launch(
                executable_path=chromium_path,
                headless=True,
                timeout=30000
            )
            
            print("✅ Chromium lanzado exitosamente")
            
        except Exception as e:
            print(f"❌ Error lanzando Chromium: {e}")

        context = await browser.new_context()
        page = await context.new_page()

        def entrar_desde_solicitud(req):
            rid = req._impl_obj._guid if hasattr(req, "_impl_obj") else req.timing.__repr__()
            return {
                "id": rid,
                "name": req.url,
                "status": None,
                "type": req.resource_type,
                "method": req.method,
                "failure": None,
                "timestamp": time.time()
            }

        page.on("request", lambda req: entries.setdefault(req.url + "|" + str(req.timing), entrar_desde_solicitud(req)))

        async def on_response(resp):
            req = resp.request
            key = req.url + "|" + str(req.timing)
            ent = entries.get(key)
            if not ent:
                ent = {
                    "id": key,
                    "name": req.url,
                    "status": resp.status,
                    "type": req.resource_type,
                    "method": req.method,
                    "failure": None,
                    "timestamp": time.time()
                }
            else:
                ent["status"] = resp.status
                ent["type"] = req.resource_type
            entries[key] = ent

        async def on_request_failed(req):
            nonlocal estado
            key = req.url + "|" + str(req.timing)
            ent = entries.get(key)
            failure = req.failure
            if not ent:
                ent = {
                    "id": key,
                    "name": req.url,
                    "status": None,
                    "type": req.resource_type,
                    "method": req.method,
                    "failure": failure,
                    "timestamp": time.time()
                }
            else:
                ent["failure"] = failure
            entries[key] = ent

        page.on("response", lambda r: asyncio.create_task(on_response(r)))
        page.on("requestfailed", lambda r: asyncio.create_task(on_request_failed(r)))

        print(f"🌐 Visitando {url} ... (timeout 20s para carga inicial).")
        try:
            await page.goto(url, timeout=20000, wait_until="domcontentloaded")
            print("✅ Página cargada exitosamente")
        except Exception as e:
            estado = "❌"
            print(f"⚠️ Advertencia: la página ha sido rechazada: {e!s}")

        await asyncio.sleep(4)

        try:
            await page.wait_for_load_state("networkidle", timeout=5000)
        except Exception:
            pass

        result_list = []
        for k, v in entries.items():
            if isinstance(v.get("status"), str) and v["status"].isdigit():
                v["status"] = int(v["status"])
            result_list.append({
                "name": v.get("name"),
                "status": v.get("status"),
                "type": v.get("type"),
                "method": v.get("method"),
                "failure": v.get("failure")
            })

        OUTPUT_FILE = f"{estado}{domain}_network_log.json"

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            json.dump(result_list, f, ensure_ascii=False, indent=2)

        print(f"💾 Se han guardado {len(result_list)} registros en '{OUTPUT_FILE}'")
        await browser.close()

# ========================== INTERFAZ GRÁFICA ==========================
class NetworkCaptureApp:
    def __init__(self, root):
        self.root = root
        self.setup_ui()

    def setup_ui(self):
        ancho_ventana = 400
        alto_ventana = 300

        ancho_pantalla = self.root.winfo_screenwidth()
        alto_pantalla = self.root.winfo_screenheight()

        x = (ancho_pantalla // 2) - (ancho_ventana // 2)
        y = (alto_pantalla // 2) - (alto_ventana // 2)

        self.root.geometry(f"{ancho_ventana}x{alto_ventana}+{x}+{y}")
        self.root.title("Aplicación para capturar Network")

        etiqueta = tk.Label(self.root, text="Ingrese el url de la página a verificar:", font=("Arial", 12, "bold"))
        etiqueta.pack(pady=10)

        self.entrada_url = tk.Entry(self.root, width=50)
        self.entrada_url.pack(pady=5)
        self.entrada_url.bind('<Return>', lambda event: self.enviar_url())

        self.boton_verificar = tk.Button(self.root, text="Verificar", font=("Arial", 12, "bold"), command=self.enviar_url)
        self.boton_verificar.pack(pady=20)

        self.boton_limpiar = tk.Button(self.root, text="Limpiar", font=("Arial", 12, "bold"), command=self.limpiar_archivos)
        self.boton_limpiar.pack(pady=5)

        self.estado_label = tk.Label(self.root, text="", font=("Arial", 10))
        self.estado_label.pack(pady=5)

    def ejecutar_captura(self, url):
        try:
            asyncio.run(main_with_url(url))
            self.mostrar_exito()
        except Exception as e:
            self.mostrar_error(f"Error: {str(e)}")

    def enviar_url(self):
        url = self.entrada_url.get().strip()
        if not url:
            messagebox.showwarning("Advertencia", "Por favor, ingrese una URL")
            return
        if not url.startswith(("www.")):
            url = "www." + url

        print(f"📥 URL ingresada: {url}")

        self.boton_verificar.config(state="disabled")
        self.estado_label.config(text="Procesando... Por favor espere.")
        self.root.update()

        thread = threading.Thread(target=self.ejecutar_captura, args=(url,))
        thread.daemon = True
        thread.start()

    def mostrar_exito(self):
        self.boton_verificar.config(state="normal")
        self.estado_label.config(text="¡Completado! Revisa el archivo JSON.")
        self.root.after(3000, lambda: self.estado_label.config(text=""))

    def limpiar_archivos(self):
        self.entrada_url.delete(0, tk.END)
        self.root.after(2000, lambda: self.estado_label.config(text=""))

    def mostrar_error(self, mensaje):
        self.boton_verificar.config(state="normal")
        self.estado_label.config(text=mensaje)
        messagebox.showerror("Error", mensaje)
        self.root.after(3000, lambda: self.estado_label.config(text=""))

if __name__ == "__main__":
    # Verificar Chromium al inicio
    chromium_path = get_chromium_path()
    if not chromium_path:
        print("❌ ADVERTENCIA: Chromium no encontrado")
    else:
        print("✅ Chromium verificado correctamente")
    
    root = tk.Tk()
    app = NetworkCaptureApp(root)
    root.mainloop()