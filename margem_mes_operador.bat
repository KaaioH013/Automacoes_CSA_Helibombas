@echo off
chcp 65001 >nul
title Margem mes operador - CSA
cd /d "%~dp0"
python enviar_email_margem_mes_operador.py --enviar
pause
