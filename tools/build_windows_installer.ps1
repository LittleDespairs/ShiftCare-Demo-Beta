param(
    [ValidateSet("ShiftCare", "Demo")]
    [string]$Target = "ShiftCare",
    [switch]$InstallInnoSetup,
    [switch]$Release,
    [switch]$Sign,
    [string]$CertificateThumbprint = $env:SHIFTCARE_SIGN_CERT_THUMBPRINT,
    [string]$CertificateSubject = $env:SHIFTCARE_SIGN_CERT_SUBJECT,
    [string]$SignToolPath = $env:SHIFTCARE_SIGNTOOL_PATH,
    [string]$TimestampUrl = $(if ($env:SHIFTCARE_TIMESTAMP_URL) { $env:SHIFTCARE_TIMESTAMP_URL } else { "http://timestamp.digicert.com" })
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
$pyinstaller = Join-Path $repoRoot ".venv\Scripts\pyinstaller.exe"
$specName = if ($Target -eq "Demo") { "ShiftCare_Demo_0.20.11_beta.spec" } else { "ShiftCare_0.20.11_beta.spec" }
$installerName = if ($Target -eq "Demo") { "ScheduleAppDemo.iss" } else { "ScheduleApp.iss" }
$spec = Join-Path $repoRoot $specName
$installerScript = Join-Path $repoRoot "installer\$installerName"
$iconScript = Join-Path $repoRoot "tools\create_windows_icon.py"
$releaseConfig = Join-Path $repoRoot "release_config.py"

function Find-SignTool {
    param([string]$ConfiguredPath)

    if ($ConfiguredPath) {
        if (Test-Path -LiteralPath $ConfiguredPath) {
            return (Resolve-Path -LiteralPath $ConfiguredPath).Path
        }
        throw "Configured SignToolPath was not found: $ConfiguredPath"
    }

    $command = Get-Command signtool.exe -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }

    $windowsKitsRoot = "${env:ProgramFiles(x86)}\Windows Kits\10\bin"
    if (Test-Path -LiteralPath $windowsKitsRoot) {
        $candidate = Get-ChildItem -Path $windowsKitsRoot -Recurse -Filter signtool.exe -ErrorAction SilentlyContinue |
            Where-Object { $_.FullName -match "\\x64\\signtool\.exe$" } |
            Sort-Object FullName -Descending |
            Select-Object -First 1
        if ($candidate) {
            return $candidate.FullName
        }
    }

    return $null
}

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

function Get-InnoDefine {
    param(
        [string]$Path,
        [string]$Name
    )

    $pattern = "^\s*#define\s+$([regex]::Escape($Name))\s+`"(?<value>[^`"]+)`""
    foreach ($line in Get-Content -LiteralPath $Path) {
        $match = [regex]::Match($line, $pattern)
        if ($match.Success) {
            return $match.Groups["value"].Value
        }
    }

    throw "Could not find Inno define $Name in $Path"
}

function Get-InnoDirective {
    param(
        [string]$Path,
        [string]$Name
    )

    $pattern = "^\s*$([regex]::Escape($Name))=(?<value>.+?)\s*$"
    foreach ($line in Get-Content -LiteralPath $Path) {
        $match = [regex]::Match($line, $pattern)
        if ($match.Success) {
            return $match.Groups["value"].Value.Trim()
        }
    }

    throw "Could not find Inno directive $Name in $Path"
}

function Get-ReleaseConfigSignerSubject {
    param([string]$Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Release config was not found: $Path"
    }

    $pattern = '^\s*WINDOWS_SIGNER_SUBJECT\s*=\s*"(?<value>[^"]+)"'
    foreach ($line in Get-Content -LiteralPath $Path) {
        $match = [regex]::Match($line, $pattern)
        if ($match.Success) {
            return $match.Groups["value"].Value.Trim()
        }
    }

    throw "Could not find WINDOWS_SIGNER_SUBJECT in $Path"
}

function Get-SignIdentityArgs {
    param(
        [string]$Thumbprint,
        [string]$Subject
    )

    if ($Thumbprint) {
        $normalizedThumbprint = $Thumbprint.Replace(" ", "").Trim()
        if (-not $normalizedThumbprint) {
            throw "Certificate thumbprint is empty."
        }
        return @("/sha1", $normalizedThumbprint)
    }

    if ($Subject) {
        $normalizedSubject = $Subject.Trim()
        if (-not $normalizedSubject) {
            throw "Certificate subject is empty."
        }
        return @("/n", $normalizedSubject)
    }

    throw "Code signing is enabled, but no certificate identity was provided. Set SHIFTCARE_SIGN_CERT_THUMBPRINT or SHIFTCARE_SIGN_CERT_SUBJECT."
}

function Convert-SignArgsToInnoCommand {
    param(
        [string]$ToolPath,
        [string[]]$IdentityArgs,
        [string]$Timestamp
    )

    $identity = if ($IdentityArgs[0] -eq "/sha1") {
        '/sha1 "{0}"' -f $IdentityArgs[1]
    }
    else {
        '/n "{0}"' -f $IdentityArgs[1]
    }

    return ('"{0}" sign /fd SHA256 /tr "{1}" /td SHA256 {2} "$f"' -f $ToolPath, $Timestamp, $identity)
}

function Invoke-CodeSign {
    param(
        [string]$ToolPath,
        [string[]]$IdentityArgs,
        [string]$Timestamp,
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "File to sign was not found: $Path"
    }

    & $ToolPath sign /fd SHA256 /tr $Timestamp /td SHA256 @IdentityArgs $Path
}

function Test-CodeSignature {
    param(
        [string]$ToolPath,
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "File to verify was not found: $Path"
    }

    & $ToolPath verify /pa /tw /v $Path
}

function Test-ExpectedSignerSubject {
    param(
        [string]$Path,
        [string]$ExpectedSubject
    )

    if (-not $ExpectedSubject) {
        throw "Expected signer subject is empty. Set WINDOWS_SIGNER_SUBJECT in release_config.py."
    }

    $signature = Get-AuthenticodeSignature -LiteralPath $Path
    if (-not $signature.SignerCertificate) {
        throw "Signed file has no signer certificate: $Path"
    }

    $actualSubject = [string]$signature.SignerCertificate.Subject
    if ($actualSubject.ToLowerInvariant().Contains($ExpectedSubject.ToLowerInvariant())) {
        return
    }

    throw "Signed file publisher '$actualSubject' does not match release_config.py WINDOWS_SIGNER_SUBJECT '$ExpectedSubject'."
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

$signtool = $null
$signIdentityArgs = @()
$innoSignCommand = $null
$expectedSignerSubject = $null
if ($Sign) {
    $signtool = Find-SignTool -ConfiguredPath $SignToolPath
    if (-not $signtool) {
        throw "signtool.exe was not found. Install Windows SDK Signing Tools or set SHIFTCARE_SIGNTOOL_PATH."
    }

    $signIdentityArgs = Get-SignIdentityArgs -Thumbprint $CertificateThumbprint -Subject $CertificateSubject
    $innoSignCommand = Convert-SignArgsToInnoCommand -ToolPath $signtool -IdentityArgs $signIdentityArgs -Timestamp $TimestampUrl
    $expectedSignerSubject = Get-ReleaseConfigSignerSubject -Path $releaseConfig
}

$appExeName = Get-InnoDefine -Path $installerScript -Name "MyAppExeName"
$appDistDir = Get-InnoDefine -Path $installerScript -Name "MyAppDistDir"
$installerVersion = Get-InnoDefine -Path $installerScript -Name "MyAppVersion"
$outputBaseFilename = Get-InnoDirective -Path $installerScript -Name "OutputBaseFilename"
$outputBaseFilename = $outputBaseFilename.Replace("{#MyAppVersion}", $installerVersion)
$appDistPath = Join-Path (Split-Path -Parent $installerScript) $appDistDir
$appExePath = Join-Path $appDistPath $appExeName
$installerOutputPath = Join-Path $repoRoot "dist\installer\$outputBaseFilename.exe"

Push-Location $repoRoot
try {
    & $python $iconScript
    $pyinstallerArgs = @("--noconfirm")
    if ($Release) {
        $pyinstallerArgs += "--clean"
    }
    $pyinstallerArgs += $spec
    & $pyinstaller @pyinstallerArgs

    if ($Sign) {
        Invoke-CodeSign -ToolPath $signtool -IdentityArgs $signIdentityArgs -Timestamp $TimestampUrl -Path $appExePath
    }

    $innoArgs = @()
    if ($Sign) {
        $innoArgs += "/DCodeSign"
        $innoArgs += "/SShiftCareSignTool=$innoSignCommand"
    }
    $innoArgs += $installerScript
    & $iscc @innoArgs

    if ($Sign) {
        Test-CodeSignature -ToolPath $signtool -Path $appExePath
        Test-CodeSignature -ToolPath $signtool -Path $installerOutputPath
        Test-ExpectedSignerSubject -Path $appExePath -ExpectedSubject $expectedSignerSubject
        Test-ExpectedSignerSubject -Path $installerOutputPath -ExpectedSubject $expectedSignerSubject
    }
}
finally {
    Pop-Location
}
