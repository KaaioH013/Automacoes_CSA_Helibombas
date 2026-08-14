$ErrorActionPreference = 'Stop'

$workspace = (Resolve-Path $PSScriptRoot).Path
$runnerRotina = Join-Path $PSScriptRoot "run_rotina_comercial_manha-hidden.vbs"
$runnerSexta = Join-Path $PSScriptRoot "run_conferencia_markup_sexta-hidden.vbs"

foreach ($path in @($runnerRotina, $runnerSexta)) {
    if (-not (Test-Path $path)) {
        throw "Runner nao encontrado: $path"
    }
}

$hoje = Get-Date
$diasAteSegunda = ([int][DayOfWeek]::Monday - [int]$hoje.DayOfWeek + 7) % 7
$inicio = $hoje.Date.AddDays($diasAteSegunda)
$dataInicio = $inicio.ToString("dd/MM/yyyy")

$taskRotina = "CSA_Rotina_Comercial_Manha_0800"
$taskSexta = "CSA_Conferencia_Markup_Sexta_0815"

$actionRotina = "wscript.exe //B `"$runnerRotina`""
$actionSexta = "wscript.exe //B `"$runnerSexta`""

schtasks /Create /TN $taskRotina /TR $actionRotina /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST 08:00 /SD $dataInicio /F | Out-Null
schtasks /Create /TN $taskSexta /TR $actionSexta /SC WEEKLY /D FRI /ST 08:15 /SD $dataInicio /F | Out-Null

Write-Host "Repositorio: $workspace"
Write-Host "Tarefas registradas (inicio: $($inicio.ToString('dd/MM/yyyy'))):"
Write-Host " - $taskRotina  -> seg-sex 08:00"
Write-Host " - $taskSexta    -> sex      08:15"
Write-Host ""
Write-Host "Logs:"
Write-Host " - $workspace\logs\rotina_comercial_manha.log"
Write-Host " - $workspace\logs\conferencia_markup_sexta.log"
