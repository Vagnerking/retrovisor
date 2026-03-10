@echo off
setlocal

REM Inicia o app usando todas as imagens da pasta referencias_alvo como base
cd /d %~dp0

python app.py --reference-dir referencias_alvo --similarity-threshold 0.5

endlocal
