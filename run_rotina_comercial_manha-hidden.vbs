' Rotina comercial manha sem janela visivel (Task Scheduler).
Set shell = CreateObject("WScript.Shell")
ps1 = "C:\DEV\Automacoes_CSA_Helibombas\run_rotina_comercial_manha.ps1"
cmd = "powershell.exe -NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File """ & ps1 & """"
shell.Run cmd, 0, True
