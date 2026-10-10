from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import pbkdf2_hmac, sha256
from hmac import compare_digest
from os import urandom

from cashless_app.database import get_firestore_client, init_db, next_id


VALID_ROLES = {"usuario", "staff", "admin"}
PBKDF2_ITERATIONS = 310_000
ACCOUNT_CREATION_SECRET_HASH = "08f0c31e3a8beeb38f48cc64e1e6c72cfdc481d52c6440c4c577a757dfc56439"


@dataclass(frozen=True)
class AuthenticatedAccount:
    id: int
    username: str
    role: str


def _now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _hash_password(password: str, salt: bytes) -> bytes:
    return pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)


def is_creation_secret_valid(creation_secret: str) -> bool:
    candidate_hash = sha256(creation_secret.encode("utf-8")).hexdigest()
    return compare_digest(candidate_hash, ACCOUNT_CREATION_SECRET_HASH)


class AuthService:
    """Autenticación local con contraseñas cifradas mediante PBKDF2."""

    def __init__(self) -> None:
        init_db()

    def has_accounts(self) -> bool:
        with get_connection() as conn:
            return conn.execute("SELECT EXISTS(SELECT 1 FROM access_accounts)").fetchone()[0] == 1

    def has_role_account(self, role: str) -> bool:
        if role not in VALID_ROLES:
            raise ValueError("Rol no válido.")
        with get_connection() as conn:
            return conn.execute(
                "SELECT EXISTS(SELECT 1 FROM access_accounts WHERE role = ? AND is_active = 1)",
                (role,),
            ).fetchone()[0] == 1

    def create_account(self, username: str, password: str, role: str, creation_secret: str) -> int:
        if not is_creation_secret_valid(creation_secret):
            raise ValueError("Palabra secreta incorrecta.")
        normalized_username = username.strip()
        if len(normalized_username) < 3:
            raise ValueError("El usuario debe tener al menos 3 caracteres.")
        if len(password) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres.")
        if role not in VALID_ROLES:
            raise ValueError("Rol no válido.")

        salt = urandom(16)
        password_hash = _hash_password(password, salt)
        with get_connection() as conn:
            existing = conn.execute(
                "SELECT 1 FROM access_accounts WHERE username = ?",
                (normalized_username,),
            ).fetchone()
            if existing:
                raise ValueError("Ese usuario ya existe. Escribe un nombre de usuario diferente.")
            cursor = conn.execute(
                """
                INSERT INTO access_accounts (
                    username, password_salt, password_hash, role, created_at
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (normalized_username, salt, password_hash, role, _now_iso()),
            )
            return int(cursor.lastrowid)

    def create_initial_admin(self, username: str, password: str, creation_secret: str) -> int:
        if self.has_accounts():
            raise ValueError("Ya existe una cuenta. Inicia sesión con una cuenta registrada.")
        return self.create_account(username, password, "admin", creation_secret)

    def create_required_account(self, username: str, password: str, role: str, creation_secret: str) -> int:
        if self.has_role_account(role):
            raise ValueError(f"Ya existe una cuenta activa de {role}.")
        return self.create_account(username, password, role, creation_secret)

    def authenticate(self, username: str, password: str) -> AuthenticatedAccount | None:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT id, username, password_salt, password_hash, role
                FROM access_accounts
                WHERE username = ? AND is_active = 1
                """,
                (username.strip(),),
            ).fetchone()

        if not row or not compare_digest(_hash_password(password, row["password_salt"]), row["password_hash"]):
            return None
        return AuthenticatedAccount(id=row["id"], username=row["username"], role=row["role"])

    def list_accounts(self) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT id, username, role, is_active, created_at
                FROM access_accounts
                ORDER BY username COLLATE NOCASE
                """
            ).fetchall()
        return [dict(row) for row in rows]


class AuthService:
    """Autenticacion respaldada por la coleccion Firestore access_accounts."""

    def __init__(self) -> None:
        init_db()
        self.db = get_firestore_client()

    def _accounts(self) -> list[dict]:
        return [snapshot.to_dict() or {} for snapshot in self.db.collection("access_accounts").stream()]

    def has_accounts(self) -> bool:
        return bool(self._accounts())

    def has_role_account(self, role: str) -> bool:
        if role not in VALID_ROLES:
            raise ValueError("Rol no válido.")
        return any(account["role"] == role and account.get("is_active", 1) for account in self._accounts())

    def create_account(self, username: str, password: str, role: str, creation_secret: str) -> int:
        if not is_creation_secret_valid(creation_secret):
            raise ValueError("Palabra secreta incorrecta.")
        username = username.strip()
        if len(username) < 3:
            raise ValueError("El usuario debe tener al menos 3 caracteres.")
        if len(password) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres.")
        if role not in VALID_ROLES:
            raise ValueError("Rol no válido.")
        if any(account["username"].casefold() == username.casefold() for account in self._accounts()):
            raise ValueError("Ese usuario ya existe. Escribe un nombre de usuario diferente.")
        account_id, salt = next_id("access_accounts"), urandom(16)
        self.db.collection("access_accounts").document(str(account_id)).set({"id": account_id, "username": username, "password_salt": salt, "password_hash": _hash_password(password, salt), "role": role, "is_active": 1, "created_at": _now_iso()})
        return account_id

    def create_initial_admin(self, username: str, password: str, creation_secret: str) -> int:
        if self.has_accounts():
            raise ValueError("Ya existe una cuenta. Inicia sesión con una cuenta registrada.")
        return self.create_account(username, password, "admin", creation_secret)

    def create_required_account(self, username: str, password: str, role: str, creation_secret: str) -> int:
        if self.has_role_account(role):
            raise ValueError(f"Ya existe una cuenta activa de {role}.")
        return self.create_account(username, password, role, creation_secret)

    def authenticate(self, username: str, password: str) -> AuthenticatedAccount | None:
        account = next((a for a in self._accounts() if a["username"] == username.strip() and a.get("is_active", 1)), None)
        if not account or not compare_digest(_hash_password(password, account["password_salt"]), account["password_hash"]):
            return None
        return AuthenticatedAccount(id=account["id"], username=account["username"], role=account["role"])

    def list_accounts(self) -> list[dict]:
        return sorted(self._accounts(), key=lambda account: account["username"].casefold())
