@echo off
setlocal
set "GOOGLE_APPLICATION_CREDENTIALS=%~dp0credenciales\firestore-service-account.json"

if not exist "%GOOGLE_APPLICATION_CREDENTIALS%" (
  echo.
  echo No se encontro la credencial de Firestore.
  echo Copia el archivo JSON de la cuenta de servicio en:
  echo %~dp0credenciales\firestore-service-account.json
  echo.
  pause
  exit /b 1
)

start "" "%~dp0E2CanaVIPuntos.exe"
