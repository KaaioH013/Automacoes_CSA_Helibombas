$ErrorActionPreference = 'Stop'

$workspace = (Resolve-Path $PSScriptRoot).Path
$scriptPath = Join-Path $workspace "conferencia_markup_sexta.py"
$logsDir = Join-Path $workspace "logs"

if (-not (Test-Path $logsDir)) {
    New-Item -Path $logsDir -ItemType Directory | Out-Null
}

$logFile = Join-Path $logsDir "conferencia_markup_sexta.log"
$maxTentativas = 3
$esperaSegundos = 15

try {
    Set-Location -Path $workspace
    $env:PYTHONIOENCODING = "utf-8"
    $env:PYTHONUTF8 = "1"

    for ($tentativa = 1; $tentativa -le $maxTentativas; $tentativa++) {
        $stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        "[$stamp] START conferencia markup sexta (tentativa $tentativa/$maxTentativas)" | Out-File -FilePath $logFile -Append -Encoding utf8

        py -3 $scriptPath --enviar 2>&1 | Out-File -FilePath $logFile -Append -Encoding utf8
        $exitCode = $LASTEXITCODE

        if ($exitCode -eq 0) {
            $ok = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
            "[$ok] OK conferencia markup sexta" | Out-File -FilePath $logFile -Append -Encoding utf8
            break
        }

        $fail = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
        "[$fail] WARN conferencia falhou com exit code $exitCode" | Out-File -FilePath $logFile -Append -Encoding utf8

        if ($tentativa -lt $maxTentativas) {
            Start-Sleep -Seconds $esperaSegundos
        }
        else {
            throw "Falha apos $maxTentativas tentativas (exit code $exitCode)."
        }
    }
}
catch {
    $errStamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "[$errStamp] ERROR conferencia: $($_.Exception.Message)" | Out-File -FilePath $logFile -Append -Encoding utf8
    throw
}
