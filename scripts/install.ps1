<#
.SYNOPSIS
    Convenience PowerShell wrapper for the AI Second Brain Toolkit installer.
.DESCRIPTION
    Discovers Python (>= 3.11) and invokes scripts/install_toolkit.py with forwarded arguments.
.EXAMPLE
    .\scripts\install.ps1 --check-only
    .\scripts\install.ps1 --vault "C:\Users\username\OneDrive\AI-Second-Brain"
    .\scripts\install.ps1 --dry-run --json
#>
[CmdletBinding()]
param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ForwardArgs
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoRoot = Split-Path -Parent $ScriptDir
$Installer = Join-Path $ScriptDir "install_toolkit.py"

# Discover Python interpreter
$PythonExe = $null
$PythonArgs = @()

$Candidates = @(
    (Join-Path $RepoRoot ".venv-graphify\Scripts\python.exe"),
    (Join-Path $RepoRoot ".venv\Scripts\python.exe")
)

foreach ($c in $Candidates) {
    if (Test-Path $c) {
        $PythonExe = $c
        break
    }
}

if (-not $PythonExe) {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        $PythonExe = "py"
        $PythonArgs = @("-3")
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        $PythonExe = "python"
    } else {
        Write-Error "Python 3.11+ is required but neither virtual environment nor system Python was found."
        exit 1
    }
}

& $PythonExe @PythonArgs $Installer $ForwardArgs
exit $LASTEXITCODE
