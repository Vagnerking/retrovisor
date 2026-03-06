@echo off
setlocal

REM Gere um executável .exe no Windows usando PyInstaller
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller

pyinstaller --noconfirm --onefile --windowed --name VigiaWebcam app.py

echo.
echo Build finalizado. Arquivo gerado em: dist\VigiaWebcam.exe
endlocal
