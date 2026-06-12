@echo off
chcp 65001 >nul
title Remover tarefas CSA
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0remover_tarefas.ps1"
echo.
pause
