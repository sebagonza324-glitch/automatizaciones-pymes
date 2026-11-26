@echo off
REM Doble clic aqui para abrir el programa de cotizaciones.
REM pythonw.exe = Python sin la ventana negra de consola.
start "" "%~dp0..\.venv\Scripts\pythonw.exe" "%~dp0app.py"
