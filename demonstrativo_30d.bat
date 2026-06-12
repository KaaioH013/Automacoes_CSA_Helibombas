@echo off
chcp 65001 >nul
title Demonstrativo 30 dias - CSA
cd /d "%~dp0"
echo.
echo  Envio unico demonstrativo completo (30 dias)
echo.
python enviar_demonstrativo_comercial_30d.py --enviar
echo.
if errorlevel 1 (echo  [ERRO]) else (echo  [OK])
pause
