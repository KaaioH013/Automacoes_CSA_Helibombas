@echo off
chcp 65001 >nul
title Margem cotacoes - CSA
cd /d "%~dp0"
python enviar_email_margem_cotacoes.py --dias 30 --enviar
pause
