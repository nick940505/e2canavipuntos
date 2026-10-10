"""Cliente compartido de Cloud Firestore autenticado con ADC."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from google.cloud import firestore


_client: firestore.Client | None = None


def get_firestore_client() -> firestore.Client:
    global _client
    if _client is None:
        credential_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        if not credential_path:
            raise RuntimeError("Falta la variable GOOGLE_APPLICATION_CREDENTIALS.")
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
