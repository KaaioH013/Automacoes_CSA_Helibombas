@echo off
chcp 65001 >nul
title Registrar tarefas CSA
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0registrar_tarefas.ps1"
echo.
pause
