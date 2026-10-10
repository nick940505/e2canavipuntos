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
- Recargar saldo y cobrar desde caja con descuento por membresia
- Visualizar historial basico

## Estructura

- `app.py`: punto de entrada
- `cashless_app/database.py`: inicializacion y acceso a Cloud Firestore
- `cashless_app/services.py`: logica de negocio
- `cashless_app/nfc.py`: capa para integrar el lector NFC
- `cashless_app/ui.py`: interfaz de escritorio con tkinter

## Ejecutar

```powershell
.\.venv\Scripts\python.exe app.py
```

## Acceso por rol

En el primer arranque la app solicita crear una cuenta de administrador. Las contrasenas no se almacenan en texto plano: se protegen localmente con PBKDF2.

Despues de iniciar sesion, el administrador puede abrir la pestana `Accesos` para crear cuentas de tipo `usuario`, `staff` o `admin`. Cada cuenta abre solo las pestañas autorizadas para su rol.

## Integracion NFC

La app usa el ACR122U a traves de PC/SC, que es el modo estandar de Windows para este lector. Asi evita el error `libusb ... not supported (-12)` que aparece al intentar acceder al dispositivo por USB directo.

Instalacion sugerida:

```powershell
.\.venv\Scripts\python.exe -m pip install pyscard
```

Flujo:

- Conecta el lector NFC al equipo.
- Abre la app.
- En `Usuarios` puedes leer el UID de una tarjeta y registrarla junto con el usuario.
- Usa el boton `Leer desde lector` en Tarjetas, Transacciones o Consulta NFC.
- Acerca la tarjeta al lector para capturar el UID automaticamente.

La lectura de UID esta integrada. La escritura NDEF queda fuera de este flujo PC/SC porque depende del tipo exacto de tarjeta y requiere una implementacion especifica.

Si las librerias NFC no estan instaladas, la app sigue funcionando en modo manual para que puedas escribir el UID.

## Base de datos en Cloud Firestore

La aplicación usa Cloud Firestore mediante Application Default Credentials. La
variable `GOOGLE_APPLICATION_CREDENTIALS` debe apuntar a la credencial ya
configurada; la llave no se guarda en el repositorio.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Migrar datos existentes de SQLite

La primera migración no sobrescribe documentos que ya existan en Firestore, por
lo que puede reintentarse sin duplicar información. Desde la raíz del proyecto:

```powershell
.\.venv313\Scripts\python.exe migrate_sqlite_to_firestore.py
```

## Siguiente paso recomendado

Integrar el lector NFC real en `cashless_app/nfc.py` para reemplazar la captura manual del UID.
