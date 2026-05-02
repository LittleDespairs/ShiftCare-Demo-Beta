param(
    [switch]$InstallInnoSetup
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
$pyinstaller = Join-Path $repoRoot ".venv\Scripts\pyinstaller.exe"
$spec = Join-Path $repoRoot "ShiftCare_0.15.8_beta.spec"
$installerScript = Join-Path $repoRoot "installer\ScheduleApp.iss"
$iconScript = Join-Path $repoRoot "tools\create_windows_icon.py"

function Find-InnoCompiler {
    $command = Get-Command iscc.exe -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    $candidatePaths = @(
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe"
    )

    foreach ($path in $candidatePaths) {
        if ($path -and (Test-Path -LiteralPath $path)) {
            return $path
        }
    }

    return $null
}

if (-not (Test-Path -LiteralPath $python)) {
    throw "Python virtual environment was not found: $python"
}

if (-not (Test-Path -LiteralPath $pyinstaller)) {
    throw "PyInstaller was not found: $pyinstaller"
}

$iscc = Find-InnoCompiler
if (-not $iscc -and $InstallInnoSetup) {
    $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
    if (-not $winget) {
        throw "winget.exe was not found. Install Inno Setup 6 manually: https://jrsoftware.org/isinfo.php"
    }

    & $winget.Source install --id JRSoftware.InnoSetup --exact --silent --accept-source-agreements --accept-package-agreements
    $iscc = Find-InnoCompiler
}

if (-not $iscc) {
    throw "Inno Setup compiler was not found. Install it or rerun with -InstallInnoSetup."
}

Push-Location $repoRoot
try {
    & $python $iconScript
    & $pyinstaller --noconfirm $spec
    & $iscc $installerScript
}
finally {
    Pop-Location
}
