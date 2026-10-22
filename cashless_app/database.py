"""Cliente compartido de Cloud Firestore autenticado con ADC."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

from google.cloud import firestore


_client: firestore.Client | None = None


def _bundled_credential_path() -> Path | None:
    """Obtiene la credencial incluida junto al ejecutable portable."""
    if not getattr(sys, "frozen", False):
        return None
    candidate = Path(sys.executable).resolve().parent / "credenciales" / "firestore-service-account.json"
    return candidate if candidate.is_file() else None


def get_firestore_client() -> firestore.Client:
    global _client
    if _client is None:
        credential_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if not credential_path:
            bundled_credential = _bundled_credential_path()
            credential_path = str(bundled_credential) if bundled_credential else None
        if not credential_path:
            raise RuntimeError("No se encontro la credencial de Firestore incluida en la aplicacion.")
        if not Path(credential_path).is_file():
            raise RuntimeError("GOOGLE_APPLICATION_CREDENTIALS no apunta a un archivo valido.")
        _client = firestore.Client()
    return _client


def init_db() -> None:
    """Firestore crea las colecciones bajo demanda; registra la version del esquema."""
    get_firestore_client().collection("metadata").document("schema").set({"version": 1}, merge=True)


def next_id(collection_name: str) -> int:
    """Reserva IDs numericos para conservar el contrato de la interfaz Tk."""
    db = get_firestore_client()
    ref = db.collection("counters").document(collection_name)
    transaction = db.transaction()

    @firestore.transactional
    def allocate(transaction: Any) -> int:
        snapshot = ref.get(transaction=transaction)
        value = int(snapshot.to_dict().get("value", 0)) if snapshot.exists else 0
        value += 1
        transaction.set(ref, {"value": value})
        return value

    return allocate(transaction)
