@echo off
chcp 65001 >nul
title Preview rotina equipe - CSA
cd /d "%~dp0"
echo.
echo  Gera 3 e-mails de preview so para comercial1
echo.
python rotina_comercial_manha.py --preview-equipe --enviar
echo.
if errorlevel 1 (echo  [ERRO]) else (echo  [OK])
pause
