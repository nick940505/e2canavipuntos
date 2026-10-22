# E2 Cana VIPuntos - versión portable

Esta carpeta ya contiene la aplicación y sus dependencias. No instales Python ni ejecutes `pip` en el computador destino.

## Abrir la aplicación

Haz doble clic en `E2CanaVIPuntos.exe`. La aplicación ya incluye sus dependencias
y la credencial de Firestore, por lo que no requiere configuración adicional.

La carpeta contiene una credencial confidencial. Distribúyela solo por un canal
privado y no la publiques en repositorios ni servicios de almacenamiento públicos.

## Lector NFC ACR122U

Conecta el lector antes de abrir la aplicación. Windows normalmente instala el controlador CCID/PC/SC automáticamente. Si la app no detecta el lector, instala el controlador oficial del ACR122U para Windows; la aplicación no requiere una instalación adicional.

## Qué copiar al otro computador

Copia **toda** la carpeta `E2CanaVIPuntos`; no copies únicamente el archivo `.exe`.
