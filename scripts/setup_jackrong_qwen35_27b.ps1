param(
    [Parameter(Mandatory = $true)]
    [string]$GgufPath,

    [string]$ModelName = "hf.co/Jackrong/Qwen3.5-27B-Claude-4.6-Opus-Reasoning-Distilled-GGUF:Q4_K_M"
)

$ErrorActionPreference = "Stop"

function Require-Command {
    param([string]$Name)

    $cmd = Get-Command $Name -ErrorAction SilentlyContinue
    if (-not $cmd) {
        throw "Required command '$Name' was not found in PATH."
    }
}

Require-Command "ollama"

$resolvedInput = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($GgufPath)
if (-not (Test-Path $resolvedInput -PathType Leaf)) {
    throw "GGUF file not found: $GgufPath"
}
$resolvedGguf = (Resolve-Path $resolvedInput).Path

$modelfilePath = Join-Path $PSScriptRoot "Modelfile.jackrong-qwen35-27b"
$modelfile = @(
    "FROM $resolvedGguf"
) -join "`r`n"

Set-Content -Path $modelfilePath -Value $modelfile -Encoding ascii

Write-Host "Using GGUF: $resolvedGguf"
Write-Host "Writing Modelfile: $modelfilePath"
Write-Host "Creating Ollama model: $ModelName"

& ollama create $ModelName -f $modelfilePath

Write-Host ""
Write-Host "Done. Verify with:"
Write-Host "  ollama list"
Write-Host "  ollama run $ModelName"
