# E2 Cana VIPuntos - versión portable

Esta carpeta ya contiene la aplicación y sus dependencias. No instales Python ni ejecutes `pip` en el computador destino.

## Antes de abrir por primera vez

1. Dentro de esta carpeta, crea una carpeta llamada `credenciales`.
2. Copia la llave JSON de la cuenta de servicio de Firestore en esa carpeta.
3. Renómbrala exactamente como `firestore-service-account.json`.

La llave es confidencial: no la envíes por correo ni la incluyas en repositorios públicos.

## Abrir la aplicación

Haz doble clic en `Iniciar E2 Cana VIPuntos.cmd`.

## Lector NFC ACR122U

Conecta el lector antes de abrir la aplicación. Windows normalmente instala el controlador CCID/PC/SC automáticamente. Si la app no detecta el lector, instala el controlador oficial del ACR122U para Windows; la aplicación no requiere una instalación adicional.

## Qué copiar al otro computador

Copia **toda** la carpeta `E2CanaVIPuntos`; no copies únicamente el archivo `.exe`.
