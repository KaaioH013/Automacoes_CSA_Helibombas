@echo off
chcp 65001 >nul
title Produtividade semanal - CSA
cd /d "%~dp0"
python enviar_email_produtividade_semanal.py --enviar
pause
