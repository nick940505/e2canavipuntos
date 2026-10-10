"""Migración única, reejecutable e idempotente de SQLite a Cloud Firestore.

Ejecutar desde la raíz del proyecto cuando GOOGLE_APPLICATION_CREDENTIALS esté
definida para la terminal:

    ./.venv313/Scripts/python.exe migrate_sqlite_to_firestore.py
"""

from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path
from typing import Any

from google.cloud import firestore

from cashless_app.database import get_firestore_client


COLLECTIONS = (
    "users",
    "nfc_cards",
    "memberships",
    "transactions",
    "points_ledger",
    "wallet_ledger",
    "access_accounts",
)


def default_database_path() -> Path:
    local_appdata = os.environ.get("LOCALAPPDATA")
    if not local_appdata:
        raise RuntimeError("No se pudo determinar LOCALAPPDATA; indica --sqlite-path.")
    return Path(local_appdata) / "e2canavipuntos" / "e2canavipuntos.db"


def sqlite_rows(database_path: Path, table: str) -> list[dict[str, Any]]:
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    try:
        return [dict(row) for row in connection.execute(f"SELECT * FROM {table}")]
    finally:
        connection.close()


def migrate_collection(db: firestore.Client, database_path: Path, collection: str) -> tuple[int, int]:
    """Copia documentos que no existan; nunca sobrescribe Firestore."""
    copied = skipped = 0
    batch = db.batch()
    pending = 0
    for row in sqlite_rows(database_path, collection):
        reference = db.collection(collection).document(str(row["id"]))
        if reference.get().exists:
            skipped += 1
            continue
        batch.set(reference, row)
        copied += 1
        pending += 1
        if pending == 450:
            batch.commit()
            batch = db.batch()
            pending = 0
    if pending:
        batch.commit()
    return copied, skipped


def update_counter(db: firestore.Client, database_path: Path, collection: str) -> None:
    rows = sqlite_rows(database_path, collection)
    if rows:
        reference = db.collection("counters").document(collection)
        existing = reference.get()
        current = int((existing.to_dict() or {}).get("value", 0)) if existing.exists else 0
        reference.set({"value": max(current, max(int(row["id"]) for row in rows))}, merge=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Migra datos de SQLite a Cloud Firestore.")
    parser.add_argument("--sqlite-path", type=Path, default=default_database_path())
    args = parser.parse_args()
    database_path: Path = args.sqlite_path

    if not database_path.is_file():
        raise SystemExit(f"No se encontró la base SQLite: {database_path}")
    if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        raise SystemExit("Falta GOOGLE_APPLICATION_CREDENTIALS en esta terminal.")

    db = get_firestore_client()
    results: dict[str, tuple[int, int]] = {}
    for collection in COLLECTIONS:
        results[collection] = migrate_collection(db, database_path, collection)
        update_counter(db, database_path, collection)

    print("Migración completada (copiados / omitidos porque ya existían):")
    for collection, (copied, skipped) in results.items():
        print(f"- {collection}: {copied} / {skipped}")


if __name__ == "__main__":
    main()
