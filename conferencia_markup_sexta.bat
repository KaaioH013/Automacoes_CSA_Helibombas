@echo off
chcp 65001 >nul
title Conferencia markup sexta - CSA
cd /d "%~dp0"
echo.
echo  Conferencia semanal para Caio (sex. passada + seg a qui)
echo.
python conferencia_markup_sexta.py --enviar
echo.
if errorlevel 1 (echo  [ERRO]) else (echo  [OK])
pause
