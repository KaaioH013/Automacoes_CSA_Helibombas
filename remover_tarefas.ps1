$ErrorActionPreference = 'Stop'

$tasks = @(
    "CSA_Rotina_Comercial_Manha_0800",
    "CSA_Conferencia_Markup_Sexta_0815"
)

foreach ($task in $tasks) {
    schtasks /Delete /TN $task /F 2>$null
    Write-Host "Removida (se existia): $task"
}
