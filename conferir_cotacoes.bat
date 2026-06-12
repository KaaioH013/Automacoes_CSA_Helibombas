@echo off
chcp 65001 >nul
title Conferir cotacoes em andamento - CSA
cd /d "%~dp0"
echo.
python enviar_email_conferencia_cotacoes.py --todos --enviar
echo.
if errorlevel 1 (echo  [ERRO]) else (echo  [OK])
pause
