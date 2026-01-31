# Punto de entrada para Gunicorn (Render). Carga la app Flask desde app.py
# para evitar conflicto con el paquete app/
import importlib.util
import os

_here = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("server", os.path.join(_here, "app.py"))
server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(server)
app = server.app
