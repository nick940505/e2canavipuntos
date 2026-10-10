# E2 Cana VIPuntos

Aplicacion de escritorio tipo cashless con identificacion por tarjeta NFC.

## Alcance del MVP

- Registrar usuarios
- Asociar una tarjeta NFC a un usuario
- Registrar usuario y asociar tarjeta en un mismo paso
- Consultar un usuario por UID de tarjeta
- Registrar transacciones
- Acumular puntos
- Gestionar membresias
- Escribir texto NDEF en la tarjeta
- Recargar saldo y cobrar desde caja con descuento por membresia
- Visualizar historial basico

## Estructura

- `app.py`: punto de entrada
- `cashless_app/database.py`: inicializacion y acceso a SQLite
- `cashless_app/services.py`: logica de negocio
- `cashless_app/nfc.py`: capa para integrar el lector NFC
- `cashless_app/ui.py`: interfaz de escritorio con tkinter

## Ejecutar

```powershell
.\.venv\Scripts\python.exe app.py
```

## Integracion NFC

La app ya usa una integracion basada en `nfcpy`, `ndeflib` y `pynput`, tomada de tu codigo funcional del lector.

Instalacion sugerida:

```powershell
.\.venv\Scripts\python.exe -m pip install nfcpy ndeflib pynput
```

Flujo:

- Conecta el lector NFC al equipo.
- Abre la app.
- En `Usuarios` puedes leer la tarjeta y registrarla junto con el usuario.
- Usa el boton `Leer desde lector` en Tarjetas, Transacciones o Consulta NFC.
- En `Tarjetas` puedes escribir un texto NDEF directamente sobre la tarjeta.
- Acerca la tarjeta al lector para capturar el UID automaticamente.
- Si presionas `ESC`, la espera de lectura se cancela.

La clase `NfcReader` tambien quedo preparada para escribir texto NDEF en la tarjeta desde codigo.

Si las librerias NFC no estan instaladas, la app sigue funcionando en modo manual para que puedas escribir el UID.

La base de datos se crea en:

`%LOCALAPPDATA%\e2canavipuntos\e2canavipuntos.db`

## Siguiente paso recomendado

Integrar el lector NFC real en `cashless_app/nfc.py` para reemplazar la captura manual del UID.
