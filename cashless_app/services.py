from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from sqlite3 import Row

from cashless_app.database import get_connection, init_db


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
