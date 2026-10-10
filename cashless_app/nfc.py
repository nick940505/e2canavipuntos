from __future__ import annotations

from dataclasses import dataclass

try:
    from smartcard.Exceptions import CardConnectionException, NoCardException
    from smartcard.System import readers
except ImportError:  # pragma: no cover - depende del entorno del usuario
    CardConnectionException = None
    NoCardException = None
    readers = None


UID_APDU = [0xFF, 0xCA, 0x00, 0x00, 0x00]


def _normalize_uid(uid: str) -> str:
    return uid.replace(" ", "").strip().upper()


@dataclass
class NfcReader:
    """Lector de UID para ACR122U mediante PC/SC en Windows.

    El ACR122U se expone normalmente como un lector CCID/PC/SC. Esta capa evita
    el acceso USB directo de nfcpy, que genera el error ``libusb ... -12``.
    """

    reader_name: str | None = None

    @property
    def is_pcsc_available(self) -> bool:
        return readers is not None

    def _get_readers(self) -> list:
        if not self.is_pcsc_available:
            return []
        try:
            return list(readers())
        except Exception:
            return []

    def _select_reader(self):
        available_readers = self._get_readers()
        if not available_readers:
            raise RuntimeError(
                "No se detectó ningún lector PC/SC. Conecta el ACR122U y verifica "
                "el controlador CCID/PC/SC de Windows."
            )

        if self.reader_name:
            selected = next(
                (reader for reader in available_readers if str(reader) == self.reader_name),
                None,
            )
            if selected is None:
                raise RuntimeError(f"No se encontró el lector configurado: {self.reader_name}.")
            return selected

        return next(
            (reader for reader in available_readers if "ACR122" in str(reader).upper()), available_readers[0])

    def get_status(self) -> str:
        if not self.is_pcsc_available:
            return "Modo manual. Instala pyscard para usar el lector ACR122U."

        available_readers = self._get_readers()
        if not available_readers:
            return "Lector ACR122U no detectado. Conecta el lector o usa UID manual."

        return f"Lector PC/SC listo: {self._select_reader()}."

    def list_readers(self) -> list[str]:
        return [str(reader) for reader in self._get_readers()]

    def read_uid(self, manual_uid: str | None = None) -> str:
        if manual_uid and manual_uid.strip():
            return _normalize_uid(manual_uid)
        return self.read_uid_from_reader()

    def read_uid_from_reader(self) -> str:
        result = self.read_card()
        if not result:
            raise RuntimeError("No se detectó ninguna tarjeta NFC.")
        return result["uid"]

    def read_card(self, timeout: float | None = None) -> dict | bool:
        """Lee el UID de la tarjeta presente en el ACR122U.

        ``timeout`` se mantiene por compatibilidad con la interfaz anterior. PC/SC
        devuelve inmediatamente si no hay tarjeta sobre el lector.
        """
        if not self.is_pcsc_available:
            raise RuntimeError("No está instalada la dependencia pyscard. Usa UID manual o instala pyscard.")

        reader = self._select_reader()
        connection = reader.createConnection()
        try:
            connection.connect()
            data, sw1, sw2 = connection.transmit(UID_APDU)
            if (sw1, sw2) != (0x90, 0x00):
                raise RuntimeError(
                    f"El ACR122U respondió {sw1:02X} {sw2:02X}; no fue posible leer el UID."
                )
            return {"uid": "".join(f"{byte:02X}" for byte in data), "contenido": None}
        except NoCardException:
            raise RuntimeError("No hay una tarjeta sobre el lector ACR122U.") from None
        except CardConnectionException as error:
            raise RuntimeError(f"No fue posible conectar con el ACR122U: {error}") from error
        finally:
            try:
                connection.disconnect()
            except Exception:
                pass

    def write_text(self, texto: str) -> bool:
        raise RuntimeError(
            "La escritura NDEF no está disponible en el modo PC/SC del ACR122U. "
            "La lectura de UID sí funciona; la escritura requiere una implementación "
            "específica para el tipo de tarjeta."
        )
