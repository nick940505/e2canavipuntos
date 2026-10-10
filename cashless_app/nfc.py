from __future__ import annotations

from dataclasses import dataclass

try:
    import ndef
    import nfc
    from pynput import keyboard
except ImportError:  # pragma: no cover - depende del entorno del usuario
    ndef = None
    nfc = None
    keyboard = None


def _normalize_uid(uid: str) -> str:
    return uid.replace(" ", "").strip().upper()


@dataclass
class NfcReader:
    """Adaptador NFC basado en nfcpy con fallback manual."""

    device_path: str = "usb"

    @property
    def is_nfcpy_available(self) -> bool:
        return nfc is not None and keyboard is not None and ndef is not None

    def get_status(self) -> str:
        if not self.is_nfcpy_available:
            return "Modo manual. Instala nfcpy, ndeflib y pynput para usar el lector NFC."
        return f"Lector NFC listo sobre dispositivo '{self.device_path}'."

    def list_readers(self) -> list[str]:
        if not self.is_nfcpy_available:
            return []
        return [self.device_path]

    def read_uid(self, manual_uid: str | None = None) -> str:
        if manual_uid and manual_uid.strip():
            return _normalize_uid(manual_uid)
        return self.read_uid_from_reader()

    def read_uid_from_reader(self) -> str:
        result = self.read_card()
        if not result:
            raise RuntimeError("No se detecto ninguna tarjeta NFC.")
        return result["uid"]

    def read_card(self, timeout: float | None = None) -> dict | bool:
        if not self.is_nfcpy_available:
            raise RuntimeError("No estan instaladas las dependencias NFC. Usa el modo manual o instala las librerias.")

        uid_leido = None
        contenido = None
        cancelar = False

        def on_press(key):
            nonlocal cancelar
            if key == keyboard.Key.esc:
                cancelar = True
                return False
            return True

        listener = keyboard.Listener(on_press=on_press)
        listener.start()

        def on_connect(tag):
            nonlocal uid_leido, contenido

            uid_leido = tag.identifier.hex().upper()

            if tag.ndef:
                try:
                    textos = []
                    for record in tag.ndef.records:
                        if isinstance(record, ndef.TextRecord):
                            textos.append(record.text)
                        elif isinstance(record, ndef.UriRecord):
                            textos.append(record.uri)
                        else:
                            textos.append(str(record))

                    contenido = " | ".join(textos) if textos else None
                except Exception:
                    contenido = None

            return False

        def terminar():
            return cancelar

        try:
            with nfc.ContactlessFrontend(self.device_path) as clf:
                clf.connect(
                    rdwr={"on-connect": on_connect},
                    terminate=terminar,
                )
        except Exception as exc:
            listener.stop()
            raise RuntimeError(f"Error al leer la tarjeta NFC: {exc}") from exc

        listener.stop()

        if uid_leido:
            return {"uid": uid_leido, "contenido": contenido}

        return False

    def write_text(self, texto: str) -> bool:
        if not self.is_nfcpy_available:
            raise RuntimeError("No estan instaladas las dependencias NFC para escribir la tarjeta.")

        cancelar = False
        escrito = False

        def on_press(key):
            nonlocal cancelar
            if key == keyboard.Key.esc:
                cancelar = True
                return False
            return True

        listener = keyboard.Listener(on_press=on_press)
        listener.start()

        def on_connect(tag):
            nonlocal escrito

            if not tag.ndef:
                return False

            if not tag.ndef.is_writeable:
                return False

            try:
                tag.ndef.records = [ndef.TextRecord(texto)]
                escrito = True
            except Exception as exc:
                raise RuntimeError(f"Error escribiendo en la tarjeta NFC: {exc}") from exc

            return False

        def terminar():
            return cancelar

        try:
            with nfc.ContactlessFrontend(self.device_path) as clf:
                clf.connect(
                    rdwr={"on-connect": on_connect},
                    terminate=terminar,
                )
        except Exception as exc:
            listener.stop()
            raise RuntimeError(f"Error al iniciar la escritura NFC: {exc}") from exc

        listener.stop()
        return escrito
