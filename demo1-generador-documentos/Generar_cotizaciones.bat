@echo off
REM Doble clic aqui para generar las cotizaciones en PDF.
REM Usa el entorno virtual del proyecto (carpeta .venv en Proyecto-pymes).
chcp 65001 > nul
"%~dp0..\.venv\Scripts\python.exe" "%~dp0generar.py" %*
echo.
pause
