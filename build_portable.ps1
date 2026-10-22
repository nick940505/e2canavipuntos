$ErrorActionPreference = "Stop"

# Genera una carpeta autocontenida para Windows, incluida la credencial de
# Firestore configurada en este equipo. No se debe versionar el ZIP resultante.
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $projectRoot ".venv313\Scripts\python.exe"
$releaseRoot = Join-Path $projectRoot "release\privado"
$credentialPath = [Environment]::GetEnvironmentVariable("GOOGLE_APPLICATION_CREDENTIALS", "User")
if (-not $credentialPath) {
    $credentialPath = [Environment]::GetEnvironmentVariable("GOOGLE_APPLICATION_CREDENTIALS", "Machine")
}
if (-not $credentialPath -or -not (Test-Path -LiteralPath $credentialPath)) {
    throw "No se encontro una credencial valida en GOOGLE_APPLICATION_CREDENTIALS."
}

& $python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --onedir `
    --name "E2CanaVIPuntos" `
    --add-data "$projectRoot\assets;assets" `
    --collect-all google.cloud.firestore `
    --collect-all google.api_core `
    --collect-all google.auth `
    --collect-all grpc `
    --collect-all smartcard `
    --distpath $releaseRoot `
    --workpath (Join-Path $projectRoot "build-privado") `
    --specpath $projectRoot `
    (Join-Path $projectRoot "app.py")

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller no pudo generar el paquete portable."
}

$appFolder = Join-Path $releaseRoot "E2CanaVIPuntos"
Copy-Item (Join-Path $projectRoot "DISTRIBUCION_PORTABLE.md") $appFolder
Copy-Item (Join-Path $projectRoot "Iniciar E2 Cana VIPuntos.cmd") $appFolder
New-Item -ItemType Directory -Force (Join-Path $appFolder "credenciales") | Out-Null
Copy-Item -LiteralPath $credentialPath -Destination (Join-Path $appFolder "credenciales\firestore-service-account.json")

Write-Host "Listo: $appFolder"
