from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from cashless_app.database import get_firestore_client, init_db, next_id


POINTS_PER_1000 = 1


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _row_to_dict(row: Row | None) -> dict | None:
    if row is None:
        return None
    return dict(row)


@dataclass
class CashlessService:
    def __post_init__(self) -> None:
        init_db()

    def create_user(
        self,
        first_name: str,
        last_name: str,
        email: str,
        document: str,
        birth_date: str,
        phone: str,
        health_provider: str,
    ) -> int:
        with get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO users (
                    first_name, last_name, email, document, birth_date,
                    phone, health_provider, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    first_name.strip(),
                    last_name.strip(),
                    email.strip(),
                    document.strip(),
                    birth_date.strip(),
                    phone.strip(),
                    health_provider.strip(),
                    now_iso(),
                ),
            )
            return int(cursor.lastrowid)

    def create_user_with_card(
        self,
        first_name: str,
        last_name: str,
        email: str,
        document: str,
        birth_date: str,
        phone: str,
        health_provider: str,
        card_uid: str,
    ) -> int:
        user_id = self.create_user(
            first_name=first_name,
            last_name=last_name,
            email=email,
            document=document,
            birth_date=birth_date,
            phone=phone,
            health_provider=health_provider,
        )
        self.assign_card(document, card_uid)
        return user_id

    def update_user(
        self,
        user_id: int,
        first_name: str,
        last_name: str,
        email: str,
        document: str,
        birth_date: str,
        phone: str,
        health_provider: str,
    ) -> None:
        with get_connection() as conn:
            existing = conn.execute(
                """
                SELECT id
                FROM users
                WHERE document = ? AND id <> ?
                """,
                (document.strip(), user_id),
            ).fetchone()
            if existing:
                raise ValueError("Ya existe otro usuario con ese documento.")

            cursor = conn.execute(
                """
                UPDATE users
                SET
                    first_name = ?,
                    last_name = ?,
                    email = ?,
                    document = ?,
                    birth_date = ?,
                    phone = ?,
                    health_provider = ?
                WHERE id = ?
                """,
                (
                    first_name.strip(),
                    last_name.strip(),
                    email.strip(),
                    document.strip(),
                    birth_date.strip(),
                    phone.strip(),
                    health_provider.strip(),
                    user_id,
                ),
            )
            if cursor.rowcount == 0:
                raise ValueError("No se encontro el usuario para actualizar.")

    def set_user_card(self, user_id: int, uid: str) -> None:
        normalized_uid = uid.strip().upper()
        if not normalized_uid:
            return

        with get_connection() as conn:
            user = conn.execute(
                "SELECT id FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
            if not user:
                raise ValueError("No se encontro el usuario para actualizar la tarjeta.")

            existing_owner = conn.execute(
                """
                SELECT user_id
                FROM nfc_cards
                WHERE uid = ? AND is_active = 1
                """,
                (normalized_uid,),
            ).fetchone()
            if existing_owner and existing_owner["user_id"] != user_id:
                raise ValueError("La tarjeta NFC ya esta asignada a otro usuario.")

            current_card = conn.execute(
                """
                SELECT id, uid
                FROM nfc_cards
                WHERE user_id = ? AND is_active = 1
                ORDER BY id DESC
                LIMIT 1
                """,
                (user_id,),
            ).fetchone()

            if current_card:
                if current_card["uid"] == normalized_uid:
                    return
                conn.execute(
                    """
                    UPDATE nfc_cards
                    SET is_active = 0
                    WHERE id = ?
                    """,
                    (current_card["id"],),
                )

            if not existing_owner:
                conn.execute(
                    """
                    INSERT INTO nfc_cards (uid, user_id, assigned_at)
                    VALUES (?, ?, ?)
                    """,
                    (normalized_uid, user_id, now_iso()),
                )

    def assign_card(self, user_document: str, uid: str) -> None:
        with get_connection() as conn:
            user = conn.execute(
                "SELECT id FROM users WHERE document = ?",
                (user_document.strip(),),
            ).fetchone()
            if not user:
                raise ValueError("No existe un usuario con ese documento.")

            existing = conn.execute(
                "SELECT id FROM nfc_cards WHERE uid = ?",
                (uid.strip().upper(),),
            ).fetchone()
            if existing:
                raise ValueError("La tarjeta NFC ya esta asignada.")

            conn.execute(
                """
                INSERT INTO nfc_cards (uid, user_id, assigned_at)
                VALUES (?, ?, ?)
                """,
                (uid.strip().upper(), user["id"], now_iso()),
            )

    def get_user_by_card(self, uid: str) -> dict:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT
                    users.id,
                    users.first_name,
                    users.last_name,
                    users.email,
                    users.document,
                    users.birth_date,
                    users.phone,
                    users.health_provider,
                    users.is_active,
                    nfc_cards.uid AS card_uid
                FROM nfc_cards
                JOIN users ON users.id = nfc_cards.user_id
                WHERE nfc_cards.uid = ? AND nfc_cards.is_active = 1
                """,
                (uid.strip().upper(),),
            ).fetchone()
            if not row:
                raise ValueError("No se encontro un usuario para esa tarjeta.")
            return dict(row)

    def list_users(self) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    users.id,
                    users.first_name,
                    users.last_name,
                    users.document,
                    users.phone,
                    users.is_active,
                    nfc_cards.uid AS card_uid
                FROM users
                LEFT JOIN nfc_cards ON nfc_cards.user_id = users.id AND nfc_cards.is_active = 1
                ORDER BY users.id DESC
                """
            ).fetchall()
            return [dict(row) for row in rows]

    def search_users(self, term: str = "") -> list[dict]:
        normalized = term.strip()
        with get_connection() as conn:
            if not normalized:
                return self.list_users()

            pattern = f"%{normalized}%"
            rows = conn.execute(
                """
                SELECT
                    users.id,
                    users.first_name,
                    users.last_name,
                    users.document,
                    users.phone,
                    users.is_active,
                    nfc_cards.uid AS card_uid
                FROM users
                LEFT JOIN nfc_cards ON nfc_cards.user_id = users.id AND nfc_cards.is_active = 1
                WHERE
                    users.first_name LIKE ? OR
                    users.last_name LIKE ? OR
                    users.document LIKE ? OR
                    users.phone LIKE ? OR
                    nfc_cards.uid LIKE ?
                ORDER BY users.id DESC
                """,
                (pattern, pattern, pattern, pattern, pattern),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_user_detail(self, user_id: int) -> dict:
        with get_connection() as conn:
            user_row = conn.execute(
                """
                SELECT
                    users.id,
                    users.first_name,
                    users.last_name,
                    users.email,
                    users.document,
                    users.birth_date,
                    users.phone,
                    users.health_provider,
                    users.is_active,
                    nfc_cards.uid AS card_uid
                FROM users
                LEFT JOIN nfc_cards ON nfc_cards.user_id = users.id AND nfc_cards.is_active = 1
                WHERE users.id = ?
                """,
                (user_id,),
            ).fetchone()
            if not user_row:
                raise ValueError("No se encontro el usuario seleccionado.")

            user = dict(user_row)
            membership = self.get_active_membership(user_id)
            wallet_movements = [
                dict(row)
                for row in conn.execute(
                    """
                    SELECT id, amount, entry_type, description, created_at
                    FROM wallet_ledger
                    WHERE user_id = ?
                    ORDER BY id DESC
                    LIMIT 15
                    """,
                    (user_id,),
                ).fetchall()
            ]
            transactions = [
                dict(row)
                for row in conn.execute(
                    """
                    SELECT id, amount, points_earned, description, created_at
                    FROM transactions
                    WHERE user_id = ?
                    ORDER BY id DESC
                    LIMIT 15
                    """,
                    (user_id,),
                ).fetchall()
            ]

        return {
            "user": user,
            "membership": membership,
            "wallet_balance": round(self.get_wallet_balance(user_id), 2),
            "points_balance": self.get_points_balance(user_id),
            "wallet_movements": wallet_movements,
            "transactions": transactions,
        }

    def create_membership(
        self,
        user_document: str,
        membership_name: str,
        discount_percent: float,
        duration_days: int,
    ) -> None:
        with get_connection() as conn:
            user = conn.execute(
                "SELECT id FROM users WHERE document = ?",
                (user_document.strip(),),
            ).fetchone()
            if not user:
                raise ValueError("No existe un usuario con ese documento.")

            start_date = datetime.now()
            end_date = start_date + timedelta(days=duration_days)

            conn.execute(
                """
                INSERT INTO memberships (
                    user_id, membership_name, discount_percent,
                    start_date, end_date, status
                ) VALUES (?, ?, ?, ?, ?, 'active')
                """,
                (
                    user["id"],
                    membership_name.strip(),
                    discount_percent,
                    start_date.date().isoformat(),
                    end_date.date().isoformat(),
                ),
            )

    def create_transaction(self, uid: str, amount: float, description: str) -> int:
        user = self.get_user_by_card(uid)
        points_earned = int(amount // 1000) * POINTS_PER_1000

        with get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO transactions (
                    user_id, card_uid, amount, points_earned, description, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user["id"],
                    uid.strip().upper(),
                    amount,
                    points_earned,
                    description.strip(),
                    now_iso(),
                ),
            )
            transaction_id = int(cursor.lastrowid)

            if points_earned > 0:
                conn.execute(
                    """
                    INSERT INTO points_ledger (
                        user_id, transaction_id, points_delta,
                        reason, expires_at, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        user["id"],
                        transaction_id,
                        points_earned,
                        "Compra cashless",
                        (datetime.now() + timedelta(days=365)).date().isoformat(),
                        now_iso(),
                    ),
                )

            return transaction_id

    def get_active_membership(self, user_id: int) -> dict | None:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT membership_name, discount_percent, start_date, end_date, status
                FROM memberships
                WHERE user_id = ? AND status = 'active'
                ORDER BY id DESC
                LIMIT 1
                """,
                (user_id,),
            ).fetchone()
            return _row_to_dict(row)

    def get_wallet_balance(self, user_id: int) -> float:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT COALESCE(SUM(amount), 0) AS balance
                FROM wallet_ledger
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
            return float(row["balance"])

    def get_recent_wallet_movements(self, limit: int = 20) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    wallet_ledger.id,
                    users.first_name,
                    users.last_name,
                    users.document,
                    wallet_ledger.card_uid,
                    wallet_ledger.amount,
                    wallet_ledger.entry_type,
                    wallet_ledger.description,
                    wallet_ledger.created_at
                FROM wallet_ledger
                JOIN users ON users.id = wallet_ledger.user_id
                ORDER BY wallet_ledger.id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_recent_transactions(self, limit: int = 20) -> list[dict]:
        with get_connection() as conn:
            rows = conn.execute(
                """
                SELECT
                    transactions.id,
                    users.first_name,
                    users.last_name,
                    users.document,
                    transactions.card_uid,
                    transactions.amount,
                    transactions.points_earned,
                    transactions.description,
                    transactions.created_at
                FROM transactions
                JOIN users ON users.id = transactions.user_id
                ORDER BY transactions.id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_dashboard_metrics(self) -> dict:
        with get_connection() as conn:
            users_count = int(conn.execute("SELECT COUNT(*) AS total FROM users").fetchone()["total"])
            cards_count = int(
                conn.execute(
                    "SELECT COUNT(*) AS total FROM nfc_cards WHERE is_active = 1"
                ).fetchone()["total"]
            )
            total_balance = float(
                conn.execute(
                    "SELECT COALESCE(SUM(amount), 0) AS total FROM wallet_ledger"
                ).fetchone()["total"]
            )
            total_sales = float(
                conn.execute(
                    """
                    SELECT COALESCE(SUM(amount), 0) AS total
                    FROM wallet_ledger
                    WHERE entry_type = 'charge'
                    """
                ).fetchone()["total"]
            )
            total_topups = float(
                conn.execute(
                    """
                    SELECT COALESCE(SUM(amount), 0) AS total
                    FROM wallet_ledger
                    WHERE entry_type = 'topup'
                    """
                ).fetchone()["total"]
            )
            total_points = int(
                conn.execute(
                    "SELECT COALESCE(SUM(points_delta), 0) AS total FROM points_ledger"
                ).fetchone()["total"]
            )

        return {
            "users_count": users_count,
            "cards_count": cards_count,
            "total_balance": round(total_balance, 2),
            "total_sales": round(abs(total_sales), 2),
            "total_topups": round(total_topups, 2),
            "total_points": total_points,
        }

    def top_up_wallet(self, uid: str, amount: float, description: str = "Recarga de saldo") -> None:
        if amount <= 0:
            raise ValueError("La recarga debe ser mayor que cero.")

        user = self.get_user_by_card(uid)
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO wallet_ledger (
                    user_id, card_uid, amount, entry_type, description, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user["id"],
                    uid.strip().upper(),
                    amount,
                    "topup",
                    description.strip(),
                    now_iso(),
                ),
            )

    def preview_charge(self, uid: str, subtotal: float) -> dict:
        if subtotal <= 0:
            raise ValueError("El subtotal debe ser mayor que cero.")

        user = self.get_user_by_card(uid)
        membership = self.get_active_membership(user["id"])
        discount_percent = float(membership["discount_percent"]) if membership else 0.0
        discount_amount = round(subtotal * (discount_percent / 100), 2)
        total = round(subtotal - discount_amount, 2)
        balance_before = round(self.get_wallet_balance(user["id"]), 2)
        balance_after = round(balance_before - total, 2)
        points_earned = int(total // 1000) * POINTS_PER_1000

        return {
            "user": user,
            "membership": membership,
            "subtotal": round(subtotal, 2),
            "discount_percent": discount_percent,
            "discount_amount": discount_amount,
            "total": total,
            "balance_before": balance_before,
            "balance_after": balance_after,
            "points_earned": points_earned,
        }

    def process_charge(self, uid: str, subtotal: float, description: str) -> dict:
        preview = self.preview_charge(uid, subtotal)
        user = preview["user"]

        if preview["balance_after"] < 0:
            raise ValueError("Saldo insuficiente para completar la compra.")

        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO wallet_ledger (
                    user_id, card_uid, amount, entry_type, description, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user["id"],
                    uid.strip().upper(),
                    -preview["total"],
                    "charge",
                    description.strip() or "Cobro cashless",
                    now_iso(),
                ),
            )

        transaction_id = self.create_transaction(
            uid=uid,
            amount=preview["total"],
            description=description.strip() or f"Compra cashless - subtotal {preview['subtotal']:.2f}",
        )

        preview["transaction_id"] = transaction_id
        return preview

    def get_points_balance(self, user_id: int) -> int:
        with get_connection() as conn:
            row = conn.execute(
                """
                SELECT COALESCE(SUM(points_delta), 0) AS balance
                FROM points_ledger
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
            return int(row["balance"])

    def get_user_summary_by_card(self, uid: str) -> dict:
        user = self.get_user_by_card(uid)

        with get_connection() as conn:
            membership = self.get_active_membership(user["id"])

            transactions = [
                dict(row)
                for row in conn.execute(
                    """
                    SELECT id, amount, points_earned, description, created_at
                    FROM transactions
                    WHERE user_id = ?
                    ORDER BY id DESC
                    LIMIT 10
                    """,
                    (user["id"],),
                ).fetchall()
            ]

        return {
            "user": user,
            "points_balance": self.get_points_balance(user["id"]),
            "wallet_balance": round(self.get_wallet_balance(user["id"]), 2),
            "membership": membership,
            "recent_transactions": transactions,
        }


# Firestore implementation.  Kept as the public class name so the Tk interface
# can continue using its existing service contract.
@dataclass
class CashlessService:
    def __post_init__(self) -> None:
        init_db()
        self.db = get_firestore_client()

    def _all(self, collection: str) -> list[dict]:
        return [item.to_dict() or {} for item in self.db.collection(collection).stream()]

    def _one(self, collection: str, record_id: int) -> dict | None:
        snapshot = self.db.collection(collection).document(str(record_id)).get()
        return snapshot.to_dict() if snapshot.exists else None

    def _user_by_document(self, document: str) -> dict | None:
        return next((s.to_dict() for s in self.db.collection("users").where("document", "==", document.strip()).limit(1).stream()), None)

    def _card(self, uid: str) -> dict | None:
        return next((s.to_dict() for s in self.db.collection("nfc_cards").where("uid", "==", uid.strip().upper()).limit(1).stream()), None)

    def create_user(self, first_name: str, last_name: str, email: str, document: str, birth_date: str, phone: str, health_provider: str) -> int:
        document = document.strip()
        if self._user_by_document(document):
            raise ValueError("Ya existe un usuario con ese documento.")
        user_id = next_id("users")
        self.db.collection("users").document(str(user_id)).set({"id": user_id, "first_name": first_name.strip(), "last_name": last_name.strip(), "email": email.strip(), "document": document, "birth_date": birth_date.strip(), "phone": phone.strip(), "health_provider": health_provider.strip(), "is_active": 1, "created_at": now_iso()})
        return user_id

    def create_user_with_card(self, first_name: str, last_name: str, email: str, document: str, birth_date: str, phone: str, health_provider: str, card_uid: str) -> int:
        user_id = self.create_user(first_name, last_name, email, document, birth_date, phone, health_provider)
        self.set_user_card(user_id, card_uid)
        return user_id

    def update_user(self, user_id: int, first_name: str, last_name: str, email: str, document: str, birth_date: str, phone: str, health_provider: str) -> None:
        if not self._one("users", user_id):
            raise ValueError("No se encontro el usuario para actualizar.")
        duplicate = self._user_by_document(document)
        if duplicate and duplicate["id"] != user_id:
            raise ValueError("Ya existe otro usuario con ese documento.")
        self.db.collection("users").document(str(user_id)).update({"first_name": first_name.strip(), "last_name": last_name.strip(), "email": email.strip(), "document": document.strip(), "birth_date": birth_date.strip(), "phone": phone.strip(), "health_provider": health_provider.strip()})

    def set_user_card(self, user_id: int, uid: str) -> None:
        uid = uid.strip().upper()
        if not uid:
            return
        if not self._one("users", user_id):
            raise ValueError("No se encontro el usuario para actualizar la tarjeta.")
        card = self._card(uid)
        if card and card.get("is_active", 1) and card["user_id"] != user_id:
            raise ValueError("La tarjeta NFC ya esta asignada a otro usuario.")
        for old in self._all("nfc_cards"):
            if old["user_id"] == user_id and old.get("is_active", 1):
                if old["uid"] == uid:
                    return
                self.db.collection("nfc_cards").document(str(old["id"])).update({"is_active": 0})
        if card:
            self.db.collection("nfc_cards").document(str(card["id"])).update({"is_active": 1})
            return
        card_id = next_id("nfc_cards")
        self.db.collection("nfc_cards").document(str(card_id)).set({"id": card_id, "uid": uid, "user_id": user_id, "is_active": 1, "assigned_at": now_iso()})

    def assign_card(self, user_document: str, uid: str) -> None:
        user = self._user_by_document(user_document)
        if not user:
            raise ValueError("No existe un usuario con ese documento.")
        if self._card(uid):
            raise ValueError("La tarjeta NFC ya esta asignada.")
        self.set_user_card(user["id"], uid)

    def get_user_by_card(self, uid: str) -> dict:
        card = self._card(uid)
        user = self._one("users", card["user_id"]) if card and card.get("is_active", 1) else None
        if not user:
            raise ValueError("No se encontro un usuario para esa tarjeta.")
        return {**user, "card_uid": card["uid"]}

    def _with_card(self, user: dict) -> dict:
        card = next((c for c in self._all("nfc_cards") if c["user_id"] == user["id"] and c.get("is_active", 1)), None)
        return {**user, "card_uid": card["uid"] if card else None}

    def list_users(self) -> list[dict]:
        return [self._with_card(x) for x in sorted(self._all("users"), key=lambda x: x["id"], reverse=True)]

    def search_users(self, term: str = "") -> list[dict]:
        term = term.strip().casefold()
        users = self.list_users()
        return users if not term else [u for u in users if term in " ".join(str(u.get(k) or "") for k in ("first_name", "last_name", "document", "phone", "card_uid")).casefold()]

    def _records(self, collection: str, user_id: int, limit: int | None = None) -> list[dict]:
        rows = sorted((x for x in self._all(collection) if x["user_id"] == user_id), key=lambda x: x["id"], reverse=True)
        return rows[:limit] if limit else rows

    def get_user_detail(self, user_id: int) -> dict:
        user = self._one("users", user_id)
        if not user:
            raise ValueError("No se encontro el usuario seleccionado.")
        return {"user": self._with_card(user), "membership": self.get_active_membership(user_id), "wallet_balance": round(self.get_wallet_balance(user_id), 2), "points_balance": self.get_points_balance(user_id), "wallet_movements": self._records("wallet_ledger", user_id, 15), "transactions": self._records("transactions", user_id, 15)}

    def create_membership(self, user_document: str, membership_name: str, discount_percent: float, duration_days: int) -> None:
        user = self._user_by_document(user_document)
        if not user:
            raise ValueError("No existe un usuario con ese documento.")
        record_id, start = next_id("memberships"), datetime.now()
        self.db.collection("memberships").document(str(record_id)).set({"id": record_id, "user_id": user["id"], "membership_name": membership_name.strip(), "discount_percent": float(discount_percent), "start_date": start.date().isoformat(), "end_date": (start + timedelta(days=duration_days)).date().isoformat(), "status": "active"})

    def create_transaction(self, uid: str, amount: float, description: str) -> int:
        user, record_id = self.get_user_by_card(uid), next_id("transactions")
        points = int(amount // 1000) * POINTS_PER_1000
        self.db.collection("transactions").document(str(record_id)).set({"id": record_id, "user_id": user["id"], "card_uid": uid.strip().upper(), "amount": float(amount), "points_earned": points, "description": description.strip(), "created_at": now_iso()})
        if points:
            ledger_id = next_id("points_ledger")
            self.db.collection("points_ledger").document(str(ledger_id)).set({"id": ledger_id, "user_id": user["id"], "transaction_id": record_id, "points_delta": points, "reason": "Compra cashless", "expires_at": (datetime.now() + timedelta(days=365)).date().isoformat(), "created_at": now_iso()})
        return record_id

    def get_active_membership(self, user_id: int) -> dict | None:
        return next((x for x in self._records("memberships", user_id) if x.get("status") == "active"), None)

    def get_wallet_balance(self, user_id: int) -> float:
        return sum(float(x["amount"]) for x in self._records("wallet_ledger", user_id))

    def _recent(self, collection: str, limit: int) -> list[dict]:
        users = {x["id"]: x for x in self._all("users")}
        rows = sorted(self._all(collection), key=lambda x: x["id"], reverse=True)[:limit]
        return [{**x, "first_name": users[x["user_id"]]["first_name"], "last_name": users[x["user_id"]]["last_name"], "document": users[x["user_id"]]["document"]} for x in rows]

    def get_recent_wallet_movements(self, limit: int = 20) -> list[dict]:
        return self._recent("wallet_ledger", limit)

    def get_recent_transactions(self, limit: int = 20) -> list[dict]:
        return self._recent("transactions", limit)

    def get_dashboard_metrics(self) -> dict:
        wallet = self._all("wallet_ledger")
        return {"users_count": len(self._all("users")), "cards_count": sum(c.get("is_active", 1) for c in self._all("nfc_cards")), "total_balance": round(sum(float(x["amount"]) for x in wallet), 2), "total_sales": round(abs(sum(float(x["amount"]) for x in wallet if x["entry_type"] == "charge")), 2), "total_topups": round(sum(float(x["amount"]) for x in wallet if x["entry_type"] == "topup"), 2), "total_points": sum(int(x["points_delta"]) for x in self._all("points_ledger"))}

    def _wallet_entry(self, user: dict, uid: str, amount: float, entry_type: str, description: str) -> None:
        record_id = next_id("wallet_ledger")
        self.db.collection("wallet_ledger").document(str(record_id)).set({"id": record_id, "user_id": user["id"], "card_uid": uid.strip().upper(), "amount": float(amount), "entry_type": entry_type, "description": description.strip(), "created_at": now_iso()})

    def top_up_wallet(self, uid: str, amount: float, description: str = "Recarga de saldo") -> None:
        if amount <= 0:
            raise ValueError("La recarga debe ser mayor que cero.")
        self._wallet_entry(self.get_user_by_card(uid), uid, amount, "topup", description)

    def preview_charge(self, uid: str, subtotal: float) -> dict:
        if subtotal <= 0:
            raise ValueError("El subtotal debe ser mayor que cero.")
        user, membership = self.get_user_by_card(uid), None
        membership = self.get_active_membership(user["id"])
        percent = float(membership["discount_percent"]) if membership else 0.0
        total = round(subtotal - subtotal * percent / 100, 2)
        balance = round(self.get_wallet_balance(user["id"]), 2)
        return {"user": user, "membership": membership, "subtotal": round(subtotal, 2), "discount_percent": percent, "discount_amount": round(subtotal - total, 2), "total": total, "balance_before": balance, "balance_after": round(balance - total, 2), "points_earned": int(total // 1000) * POINTS_PER_1000}

    def process_charge(self, uid: str, subtotal: float, description: str) -> dict:
        preview = self.preview_charge(uid, subtotal)
        if preview["balance_after"] < 0:
            raise ValueError("Saldo insuficiente para completar la compra.")
        description = description.strip() or "Cobro cashless"
        self._wallet_entry(preview["user"], uid, -preview["total"], "charge", description)
        preview["transaction_id"] = self.create_transaction(uid, preview["total"], description)
        return preview

    def get_points_balance(self, user_id: int) -> int:
        return sum(int(x["points_delta"]) for x in self._records("points_ledger", user_id))

    def get_user_summary_by_card(self, uid: str) -> dict:
        user = self.get_user_by_card(uid)
        return {"user": user, "points_balance": self.get_points_balance(user["id"]), "wallet_balance": round(self.get_wallet_balance(user["id"]), 2), "membership": self.get_active_membership(user["id"]), "recent_transactions": self._records("transactions", user["id"], 10)}
