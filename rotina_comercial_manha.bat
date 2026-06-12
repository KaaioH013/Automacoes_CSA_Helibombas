@echo off
chcp 65001 >nul
title Rotina comercial manha - CSA
cd /d "%~dp0"
echo.
echo  Envia rotina diaria para Caio, Priscila e Patricia
echo.
python rotina_comercial_manha.py --enviar-equipe --enviar
echo.
if errorlevel 1 (echo  [ERRO]) else (echo  [OK])
pause
