param(
    [string]$DistDir = (Join-Path $PSScriptRoot "dist_nuitka"),
    [string]$Publisher = "Plugintech",
    [string]$TimestampUrl = "http://timestamp.digicert.com",
    [string]$ExeName,
    [switch]$SkipSign
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "`n[STEP] $Message" -ForegroundColor Cyan
}

function Find-SignTool {
    $sdkRoot = "C:\Program Files (x86)\Windows Kits\10\bin"
    if (-not (Test-Path $sdkRoot)) {
        return $null
    }

    return Get-ChildItem $sdkRoot -Recurse -Filter signtool.exe |
        Sort-Object FullName -Descending |
        Select-Object -First 1 -ExpandProperty FullName
}

function Get-SigningCert {
    param([string]$SubjectName)

    $subject = "CN=$SubjectName"
    $existing = Get-ChildItem Cert:\CurrentUser\My |
        Where-Object { $_.Subject -eq $subject } |
        Sort-Object NotAfter -Descending |
        Select-Object -First 1

    if ($existing) {
        return $existing
    }

    Write-Host "Criando certificado autoassinado para $subject ..." -ForegroundColor Yellow
    return New-SelfSignedCertificate -Type CodeSigningCert -Subject $subject -CertStoreLocation Cert:\CurrentUser\My
}

function Test-Signature {
    param(
        [string]$SignToolPath,
        [string]$FilePath,
        [string]$PublisherName
    )

    & $SignToolPath verify /pa /v $FilePath
    if ($LASTEXITCODE -eq 0) {
        return
    }

    $sig = Get-AuthenticodeSignature -FilePath $FilePath
    $subject = ""
    if ($sig.SignerCertificate) {
        $subject = [string]$sig.SignerCertificate.Subject
    }

    if ($subject -like "*CN=$PublisherName*" -and [string]$sig.Status -in @("NotTrusted", "UnknownError", "Valid")) {
        Write-Host "Aviso: assinatura presente (certificado autoassinado, cadeia nao confiavel nesta maquina)." -ForegroundColor Yellow
        return
    }

    throw "Falha ao verificar assinatura. Status: $($sig.Status)"
}

Write-Step "Validando pasta de compilacao"
if (-not (Test-Path $DistDir)) {
    throw "Pasta nao encontrada: $DistDir"
}
$DistDir = (Resolve-Path $DistDir).Path

Write-Step "Localizando executavel"
if ([string]::IsNullOrWhiteSpace($ExeName)) {
    $exe = Get-ChildItem $DistDir -Filter "GeradorPolaroids-*.exe" |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
} else {
    $exePath = Join-Path $DistDir $ExeName
    if (-not (Test-Path $exePath)) {
        throw "Executavel nao encontrado: $exePath"
    }
    $exe = Get-Item $exePath
}

if (-not $exe) {
    throw "Nenhum GeradorPolaroids-*.exe encontrado em $DistDir"
}

Write-Host "Executavel: $($exe.Name)"

if (-not $SkipSign) {
    Write-Step "Assinando executavel"
    $signtool = Find-SignTool
    if (-not $signtool) {
        throw "signtool.exe nao encontrado. Instale o Windows SDK ou use -SkipSign"
    }

    $null = Get-SigningCert -SubjectName $Publisher

    & $signtool sign /fd SHA256 /a /tr $TimestampUrl /td SHA256 $exe.FullName
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao assinar executavel (exit code $LASTEXITCODE)"
    }

    Write-Step "Verificando assinatura"
    Test-Signature -SignToolPath $signtool -FilePath $exe.FullName -PublisherName $Publisher
} else {
    Write-Host "Assinatura ignorada (-SkipSign)" -ForegroundColor Yellow
}

Write-Step "Gerando hash SHA256"
$hash = (Get-FileHash -Path $exe.FullName -Algorithm SHA256).Hash.ToLower()
$shaPath = Join-Path $DistDir "SHA256.txt"
Set-Content -Path $shaPath -Value $hash -Encoding ascii

Write-Step "Concluido"
Write-Host "Executavel: $($exe.FullName)" -ForegroundColor Green
Write-Host "SHA256:     $hash" -ForegroundColor Green
Write-Host "Arquivo:    $shaPath" -ForegroundColor Green
