@echo off
chcp 65001 >nul
title Margem pedidos - CSA
cd /d "%~dp0"
python enviar_email_margem_pedidos_novos.py --dias 7 --enviar
pause
