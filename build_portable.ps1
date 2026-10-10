$ErrorActionPreference = "Stop"

# Genera una carpeta autocontenida para Windows. No incluye secretos ni
# credenciales de Firestore: se agregan al momento de distribuir la app.
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $projectRoot ".venv313\Scripts\python.exe"
$releaseRoot = Join-Path $projectRoot "release"

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
    --workpath (Join-Path $projectRoot "build") `
    --specpath $projectRoot `
    (Join-Path $projectRoot "app.py")

$appFolder = Join-Path $releaseRoot "E2CanaVIPuntos"
Copy-Item (Join-Path $projectRoot "DISTRIBUCION_PORTABLE.md") $appFolder
Copy-Item (Join-Path $projectRoot "Iniciar E2 Cana VIPuntos.cmd") $appFolder
New-Item -ItemType Directory -Force (Join-Path $appFolder "credenciales") | Out-Null
Copy-Item (Join-Path $projectRoot "credenciales-LEEME.txt") (Join-Path $appFolder "credenciales\LEEME.txt")

Write-Host "Listo: $appFolder"
