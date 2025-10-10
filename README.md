1. El primer paso es descargar el chromium e instalarlo. Después, dirigirse a la siguiente ruta (o similar): C:\Users\Mathias\AppData\Local\ms-playwright y copiar dicha carpeta de ms-playwright en tu carpeta raiz de este proyecto. Debe tener la siguiente estructura: ms-playwright/chromium-1187/chrome-win/

2. Para obtener el ejecutable en .exe, es necesario ejecutar el siguiente comando en la terminal
pyinstaller --onefile --add-data "ms-playwright;ms-playwright" --noconsole .\CapturarNetwork.py

3. Listo :D