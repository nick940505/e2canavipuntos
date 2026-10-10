from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from cashless_app.nfc import NfcReader
from cashless_app.services import CashlessService


class CashlessApp:
    def __init__(self) -> None:
        self.service = CashlessService()
        self.nfc_reader = NfcReader()
        self.root = tk.Tk()
        self.root.title("E2 Cana VIPuntos")
        self.root.geometry("1000x720")

        self.status_var = tk.StringVar(value=self.nfc_reader.get_status())
        self.user_search_var = tk.StringVar()

        self._build_layout()
        self.refresh_users()
        self.refresh_dashboard()

    def _build_layout(self) -> None:
        container = ttk.Frame(self.root, padding=16)
        container.pack(fill="both", expand=True)

        title = ttk.Label(
            container,
            text="E2 Cana VIPuntos",
            font=("Segoe UI", 20, "bold"),
        )
        title.pack(anchor="w", pady=(0, 12))

        notebook = ttk.Notebook(container)
        notebook.pack(fill="both", expand=True)

        self.users_tab = ttk.Frame(notebook, padding=12)
        self.cards_tab = ttk.Frame(notebook, padding=12)
        self.transactions_tab = ttk.Frame(notebook, padding=12)
        self.memberships_tab = ttk.Frame(notebook, padding=12)
        self.lookup_tab = ttk.Frame(notebook, padding=12)
        self.cashier_tab = ttk.Frame(notebook, padding=12)
        self.dashboard_tab = ttk.Frame(notebook, padding=12)

        notebook.add(self.users_tab, text="Usuarios")
        notebook.add(self.cards_tab, text="Tarjetas")
        notebook.add(self.transactions_tab, text="Transacciones")
        notebook.add(self.memberships_tab, text="Membresias")
        notebook.add(self.lookup_tab, text="Consulta NFC")
        notebook.add(self.cashier_tab, text="Caja")
        notebook.add(self.dashboard_tab, text="Dashboard")

        self._build_users_tab()
        self._build_cards_tab()
        self._build_transactions_tab()
        self._build_memberships_tab()
        self._build_lookup_tab()
        self._build_cashier_tab()
        self._build_dashboard_tab()

        status = ttk.Label(container, textvariable=self.status_var)
        status.pack(anchor="w", pady=(10, 0))

    def _build_users_tab(self) -> None:
        form = ttk.Frame(self.users_tab)
        form.pack(fill="x", pady=(0, 12))

        labels = [
            ("Nombres", "first_name"),
            ("Apellidos", "last_name"),
            ("Correo", "email"),
            ("Documento", "document"),
            ("Nacimiento", "birth_date"),
            ("Celular", "phone"),
            ("EPS", "health_provider"),
            ("UID tarjeta", "card_uid"),
        ]

        self.user_entries: dict[str, ttk.Entry] = {}
        for index, (label_text, key) in enumerate(labels):
            ttk.Label(form, text=label_text).grid(row=index // 2, column=(index % 2) * 2, sticky="w", padx=(0, 8), pady=6)
            entry = ttk.Entry(form, width=32)
            entry.grid(row=index // 2, column=(index % 2) * 2 + 1, sticky="ew", padx=(0, 16), pady=6)
            self.user_entries[key] = entry

        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)

        ttk.Button(form, text="Leer tarjeta", command=lambda: self.fill_uid(self.user_entries["card_uid"])).grid(row=4, column=0, columnspan=2, sticky="ew", pady=(12, 0), padx=(0, 8))
        ttk.Button(form, text="Registrar usuario", command=self.create_user).grid(row=4, column=2, columnspan=2, sticky="ew", pady=(12, 0))
        ttk.Button(form, text="Registrar y asociar tarjeta", command=self.create_user_with_card).grid(row=5, column=0, columnspan=4, sticky="ew", pady=(8, 0))

        search_frame = ttk.Frame(self.users_tab)
        search_frame.pack(fill="x", pady=(0, 8))
        ttk.Label(search_frame, text="Buscar usuario").pack(side="left")
        search_entry = ttk.Entry(search_frame, textvariable=self.user_search_var, width=32)
        search_entry.pack(side="left", padx=(8, 8))
        search_entry.bind("<KeyRelease>", lambda _event: self.refresh_users())
        ttk.Button(search_frame, text="Limpiar", command=self.clear_user_search).pack(side="left")

        self.users_tree = ttk.Treeview(
            self.users_tab,
            columns=("id", "document", "name", "phone", "card"),
            show="headings",
            height=12,
        )
        for key, title, width in [
            ("id", "Id", 60),
            ("document", "Documento", 140),
            ("name", "Nombre", 260),
            ("phone", "Celular", 160),
            ("card", "Tarjeta NFC", 180),
        ]:
            self.users_tree.heading(key, text=title)
            self.users_tree.column(key, width=width, anchor="w")
        self.users_tree.pack(fill="both", expand=True)
        self.users_tree.bind("<<TreeviewSelect>>", self.on_user_selected)

        self.user_detail_text = tk.Text(self.users_tab, height=14, wrap="word")
        self.user_detail_text.pack(fill="both", expand=True, pady=(12, 0))

    def _build_cards_tab(self) -> None:
        frame = ttk.Frame(self.cards_tab)
        frame.pack(fill="x")

        ttk.Label(frame, text="Documento del usuario").grid(row=0, column=0, sticky="w", pady=6)
        self.card_document_entry = ttk.Entry(frame, width=32)
        self.card_document_entry.grid(row=0, column=1, sticky="ew", pady=6, padx=(0, 12))

        ttk.Label(frame, text="UID de tarjeta").grid(row=1, column=0, sticky="w", pady=6)
        self.card_uid_entry = ttk.Entry(frame, width=32)
        self.card_uid_entry.grid(row=1, column=1, sticky="ew", pady=6, padx=(0, 12))

        ttk.Button(frame, text="Leer desde lector", command=lambda: self.fill_uid(self.card_uid_entry)).grid(row=1, column=2, sticky="ew", pady=6)
        ttk.Button(frame, text="Asignar tarjeta", command=self.assign_card).grid(row=2, column=0, columnspan=3, sticky="ew", pady=(12, 0))

        ttk.Label(frame, text="Texto NDEF").grid(row=3, column=0, sticky="w", pady=(18, 6))
        self.card_ndef_entry = ttk.Entry(frame, width=32)
        self.card_ndef_entry.grid(row=3, column=1, sticky="ew", pady=(18, 6), padx=(0, 12))
        ttk.Button(frame, text="Escribir en tarjeta", command=self.write_card_text).grid(row=3, column=2, sticky="ew", pady=(18, 6))
        frame.columnconfigure(1, weight=1)

    def _build_transactions_tab(self) -> None:
        frame = ttk.Frame(self.transactions_tab)
        frame.pack(fill="x")

        ttk.Label(frame, text="UID de tarjeta").grid(row=0, column=0, sticky="w", pady=6)
        self.tx_uid_entry = ttk.Entry(frame, width=32)
        self.tx_uid_entry.grid(row=0, column=1, sticky="ew", pady=6, padx=(0, 12))
        ttk.Button(frame, text="Leer desde lector", command=lambda: self.fill_uid(self.tx_uid_entry)).grid(row=0, column=2, sticky="ew", pady=6)

        ttk.Label(frame, text="Monto").grid(row=1, column=0, sticky="w", pady=6)
        self.tx_amount_entry = ttk.Entry(frame, width=32)
        self.tx_amount_entry.grid(row=1, column=1, sticky="ew", pady=6, padx=(0, 12))

        ttk.Label(frame, text="Descripcion").grid(row=2, column=0, sticky="w", pady=6)
        self.tx_description_entry = ttk.Entry(frame, width=32)
        self.tx_description_entry.grid(row=2, column=1, sticky="ew", pady=6, padx=(0, 12))

        ttk.Button(frame, text="Registrar transaccion", command=self.create_transaction).grid(row=3, column=0, columnspan=3, sticky="ew", pady=(12, 0))
        frame.columnconfigure(1, weight=1)

    def _build_memberships_tab(self) -> None:
        frame = ttk.Frame(self.memberships_tab)
        frame.pack(fill="x")

        ttk.Label(frame, text="Documento del usuario").grid(row=0, column=0, sticky="w", pady=6)
        self.membership_document_entry = ttk.Entry(frame, width=32)
        self.membership_document_entry.grid(row=0, column=1, sticky="ew", pady=6, padx=(0, 12))

        ttk.Label(frame, text="Nombre membresia").grid(row=1, column=0, sticky="w", pady=6)
        self.membership_name_entry = ttk.Entry(frame, width=32)
        self.membership_name_entry.grid(row=1, column=1, sticky="ew", pady=6, padx=(0, 12))

        ttk.Label(frame, text="Descuento %").grid(row=2, column=0, sticky="w", pady=6)
        self.membership_discount_entry = ttk.Entry(frame, width=32)
        self.membership_discount_entry.grid(row=2, column=1, sticky="ew", pady=6, padx=(0, 12))

        ttk.Label(frame, text="Duracion dias").grid(row=3, column=0, sticky="w", pady=6)
        self.membership_days_entry = ttk.Entry(frame, width=32)
        self.membership_days_entry.grid(row=3, column=1, sticky="ew", pady=6, padx=(0, 12))

        ttk.Button(frame, text="Crear membresia", command=self.create_membership).grid(row=4, column=0, columnspan=2, sticky="ew", pady=(12, 0))
        frame.columnconfigure(1, weight=1)

    def _build_lookup_tab(self) -> None:
        top = ttk.Frame(self.lookup_tab)
        top.pack(fill="x")

        ttk.Label(top, text="UID de tarjeta").grid(row=0, column=0, sticky="w", pady=6)
        self.lookup_uid_entry = ttk.Entry(top, width=32)
        self.lookup_uid_entry.grid(row=0, column=1, sticky="ew", padx=(0, 12), pady=6)

        ttk.Button(top, text="Leer desde lector", command=lambda: self.fill_uid(self.lookup_uid_entry)).grid(row=0, column=2, sticky="ew", pady=6)
        ttk.Button(top, text="Consultar", command=self.lookup_card).grid(row=0, column=3, sticky="ew", pady=6, padx=(8, 0))
        top.columnconfigure(1, weight=1)

        self.lookup_text = tk.Text(self.lookup_tab, height=22, wrap="word")
        self.lookup_text.pack(fill="both", expand=True, pady=(12, 0))

    def _build_cashier_tab(self) -> None:
        frame = ttk.Frame(self.cashier_tab)
        frame.pack(fill="x")

        ttk.Label(frame, text="UID de tarjeta").grid(row=0, column=0, sticky="w", pady=6)
        self.cashier_uid_entry = ttk.Entry(frame, width=32)
        self.cashier_uid_entry.grid(row=0, column=1, sticky="ew", pady=6, padx=(0, 12))
        ttk.Button(frame, text="Leer desde lector", command=lambda: self.fill_uid(self.cashier_uid_entry)).grid(row=0, column=2, sticky="ew", pady=6)

        ttk.Label(frame, text="Subtotal").grid(row=1, column=0, sticky="w", pady=6)
        self.cashier_subtotal_entry = ttk.Entry(frame, width=32)
        self.cashier_subtotal_entry.grid(row=1, column=1, sticky="ew", pady=6, padx=(0, 12))

        ttk.Label(frame, text="Descripcion").grid(row=2, column=0, sticky="w", pady=6)
        self.cashier_description_entry = ttk.Entry(frame, width=32)
        self.cashier_description_entry.grid(row=2, column=1, sticky="ew", pady=6, padx=(0, 12))

        ttk.Label(frame, text="Recarga saldo").grid(row=3, column=0, sticky="w", pady=(18, 6))
        self.cashier_topup_entry = ttk.Entry(frame, width=32)
        self.cashier_topup_entry.grid(row=3, column=1, sticky="ew", pady=(18, 6), padx=(0, 12))
        ttk.Button(frame, text="Recargar tarjeta", command=self.top_up_wallet).grid(row=3, column=2, sticky="ew", pady=(18, 6))

        ttk.Button(frame, text="Calcular total", command=self.preview_charge).grid(row=4, column=0, columnspan=2, sticky="ew", pady=(12, 0), padx=(0, 8))
        ttk.Button(frame, text="Cobrar", command=self.process_charge).grid(row=4, column=2, sticky="ew", pady=(12, 0))
        frame.columnconfigure(1, weight=1)

        self.cashier_text = tk.Text(self.cashier_tab, height=20, wrap="word")
        self.cashier_text.pack(fill="both", expand=True, pady=(12, 0))

    def _build_dashboard_tab(self) -> None:
        top = ttk.Frame(self.dashboard_tab)
        top.pack(fill="x", pady=(0, 12))

        self.dashboard_metrics_var = tk.StringVar(value="Cargando dashboard...")
        ttk.Label(top, textvariable=self.dashboard_metrics_var, justify="left").pack(anchor="w")
        ttk.Button(top, text="Actualizar dashboard", command=self.refresh_dashboard).pack(anchor="e", pady=(8, 0))

        ttk.Label(self.dashboard_tab, text="Ultimos movimientos de saldo").pack(anchor="w")
        self.wallet_tree = ttk.Treeview(
            self.dashboard_tab,
            columns=("tipo", "usuario", "documento", "monto", "fecha"),
            show="headings",
            height=8,
        )
        for key, title, width in [
            ("tipo", "Tipo", 100),
            ("usuario", "Usuario", 220),
            ("documento", "Documento", 120),
            ("monto", "Monto", 120),
            ("fecha", "Fecha", 180),
        ]:
            self.wallet_tree.heading(key, text=title)
            self.wallet_tree.column(key, width=width, anchor="w")
        self.wallet_tree.pack(fill="x", pady=(4, 12))

        ttk.Label(self.dashboard_tab, text="Ultimas transacciones").pack(anchor="w")
        self.dashboard_tx_tree = ttk.Treeview(
            self.dashboard_tab,
            columns=("id", "usuario", "documento", "monto", "puntos", "fecha"),
            show="headings",
            height=8,
        )
        for key, title, width in [
            ("id", "Id", 70),
            ("usuario", "Usuario", 220),
            ("documento", "Documento", 120),
            ("monto", "Monto", 120),
            ("puntos", "Puntos", 90),
            ("fecha", "Fecha", 180),
        ]:
            self.dashboard_tx_tree.heading(key, text=title)
            self.dashboard_tx_tree.column(key, width=width, anchor="w")
        self.dashboard_tx_tree.pack(fill="both", expand=True, pady=(4, 0))

    def create_user(self) -> None:
        try:
            self.service.create_user(
                first_name=self.user_entries["first_name"].get(),
                last_name=self.user_entries["last_name"].get(),
                email=self.user_entries["email"].get(),
                document=self.user_entries["document"].get(),
                birth_date=self.user_entries["birth_date"].get(),
                phone=self.user_entries["phone"].get(),
                health_provider=self.user_entries["health_provider"].get(),
            )
            self.status_var.set("Usuario registrado correctamente.")
            self._clear_entries(self.user_entries.values())
            self.refresh_users()
            self.refresh_dashboard()
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def create_user_with_card(self) -> None:
        try:
            uid = self.nfc_reader.read_uid(self.user_entries["card_uid"].get())
            self.service.create_user_with_card(
                first_name=self.user_entries["first_name"].get(),
                last_name=self.user_entries["last_name"].get(),
                email=self.user_entries["email"].get(),
                document=self.user_entries["document"].get(),
                birth_date=self.user_entries["birth_date"].get(),
                phone=self.user_entries["phone"].get(),
                health_provider=self.user_entries["health_provider"].get(),
                card_uid=uid,
            )
            self.status_var.set(f"Usuario registrado y tarjeta {uid} asociada.")
            self._clear_entries(self.user_entries.values())
            self.refresh_users()
            self.refresh_dashboard()
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def assign_card(self) -> None:
        try:
            uid = self.nfc_reader.read_uid(self.card_uid_entry.get())
            self.service.assign_card(self.card_document_entry.get(), uid)
            self.status_var.set(f"Tarjeta {uid} asignada correctamente.")
            self.card_document_entry.delete(0, tk.END)
            self.card_uid_entry.delete(0, tk.END)
            self.refresh_users()
            self.refresh_dashboard()
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def create_transaction(self) -> None:
        try:
            uid = self.nfc_reader.read_uid(self.tx_uid_entry.get())
            amount = float(self.tx_amount_entry.get())
            self.service.create_transaction(uid, amount, self.tx_description_entry.get())
            self.status_var.set("Transaccion registrada y puntos actualizados.")
            self.tx_uid_entry.delete(0, tk.END)
            self.tx_amount_entry.delete(0, tk.END)
            self.tx_description_entry.delete(0, tk.END)
            self.refresh_dashboard()
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def create_membership(self) -> None:
        try:
            self.service.create_membership(
                user_document=self.membership_document_entry.get(),
                membership_name=self.membership_name_entry.get(),
                discount_percent=float(self.membership_discount_entry.get()),
                duration_days=int(self.membership_days_entry.get()),
            )
            self.status_var.set("Membresia creada correctamente.")
            self.membership_document_entry.delete(0, tk.END)
            self.membership_name_entry.delete(0, tk.END)
            self.membership_discount_entry.delete(0, tk.END)
            self.membership_days_entry.delete(0, tk.END)
            self.refresh_dashboard()
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def write_card_text(self) -> None:
        try:
            texto = self.card_ndef_entry.get().strip()
            if not texto:
                raise ValueError("Ingresa el texto que quieres escribir en la tarjeta.")

            written = self.nfc_reader.write_text(texto)
            if not written:
                raise RuntimeError("No se escribio nada en la tarjeta.")

            self.status_var.set("Texto NDEF escrito correctamente en la tarjeta.")
            self.card_ndef_entry.delete(0, tk.END)
        except Exception as exc:
            messagebox.showerror("Escritura NFC", str(exc))

    def lookup_card(self) -> None:
        try:
            uid = self.nfc_reader.read_uid(self.lookup_uid_entry.get())
            summary = self.service.get_user_summary_by_card(uid)
            user = summary["user"]
            membership = summary["membership"]

            lines = [
                f"Usuario: {user['first_name']} {user['last_name']}",
                f"Documento: {user['document']}",
                f"Tarjeta: {user['card_uid']}",
                f"Saldo disponible: ${summary['wallet_balance']:.2f}",
                f"Puntos disponibles: {summary['points_balance']}",
                "",
                "Membresia:",
            ]

            if membership:
                lines.extend(
                    [
                        f"  Nombre: {membership['membership_name']}",
                        f"  Descuento: {membership['discount_percent']}%",
                        f"  Vigencia: {membership['start_date']} a {membership['end_date']}",
                        f"  Estado: {membership['status']}",
                    ]
                )
            else:
                lines.append("  Sin membresia activa registrada.")

            lines.extend(["", "Ultimas transacciones:"])
            if summary["recent_transactions"]:
                for transaction in summary["recent_transactions"]:
                    lines.append(
                        f"  #{transaction['id']} | ${transaction['amount']:.2f} | "
                        f"{transaction['points_earned']} pts | {transaction['created_at']} | "
                        f"{transaction['description'] or 'Sin descripcion'}"
                    )
            else:
                lines.append("  No hay transacciones registradas.")

            self.lookup_text.delete("1.0", tk.END)
            self.lookup_text.insert("1.0", "\n".join(lines))
            self.status_var.set(f"Consulta completada para la tarjeta {uid}.")
        except Exception as exc:
            messagebox.showerror("Error", str(exc))

    def preview_charge(self) -> None:
        try:
            uid = self.nfc_reader.read_uid(self.cashier_uid_entry.get())
            preview = self.service.preview_charge(uid, float(self.cashier_subtotal_entry.get()))
            self._render_cashier_preview(preview)
            self.status_var.set(f"Total calculado para la tarjeta {uid}.")
        except Exception as exc:
            messagebox.showerror("Caja", str(exc))

    def process_charge(self) -> None:
        try:
            uid = self.nfc_reader.read_uid(self.cashier_uid_entry.get())
            result = self.service.process_charge(
                uid=uid,
                subtotal=float(self.cashier_subtotal_entry.get()),
                description=self.cashier_description_entry.get(),
            )
            self._render_cashier_preview(result)
            self.status_var.set(
                f"Cobro realizado. Total ${result['total']:.2f}. Saldo restante ${result['balance_after']:.2f}."
            )
            self.cashier_subtotal_entry.delete(0, tk.END)
            self.cashier_description_entry.delete(0, tk.END)
            self.refresh_dashboard()
        except Exception as exc:
            messagebox.showerror("Caja", str(exc))

    def top_up_wallet(self) -> None:
        try:
            uid = self.nfc_reader.read_uid(self.cashier_uid_entry.get())
            amount = float(self.cashier_topup_entry.get())
            self.service.top_up_wallet(uid, amount)
            summary = self.service.get_user_summary_by_card(uid)
            self.cashier_text.delete("1.0", tk.END)
            self.cashier_text.insert(
                "1.0",
                "\n".join(
                    [
                        f"Recarga aplicada a {summary['user']['first_name']} {summary['user']['last_name']}",
                        f"Tarjeta: {summary['user']['card_uid']}",
                        f"Nuevo saldo: ${summary['wallet_balance']:.2f}",
                    ]
                ),
            )
            self.status_var.set(f"Recarga exitosa. Nuevo saldo ${summary['wallet_balance']:.2f}.")
            self.cashier_topup_entry.delete(0, tk.END)
            self.refresh_users()
            self.refresh_dashboard()
        except Exception as exc:
            messagebox.showerror("Caja", str(exc))

    def fill_uid(self, entry: ttk.Entry) -> None:
        try:
            uid = self.nfc_reader.read_uid_from_reader()
            entry.delete(0, tk.END)
            entry.insert(0, uid)
            self.status_var.set(f"Tarjeta detectada: {uid}")
        except Exception as exc:
            messagebox.showerror("Lectura NFC", str(exc))
            self.status_var.set(self.nfc_reader.get_status())

    def _render_cashier_preview(self, preview: dict) -> None:
        user = preview["user"]
        membership = preview["membership"]
        lines = [
            f"Cliente: {user['first_name']} {user['last_name']}",
            f"Documento: {user['document']}",
            f"Tarjeta: {user['card_uid']}",
            f"Saldo actual: ${preview['balance_before']:.2f}",
            f"Subtotal: ${preview['subtotal']:.2f}",
            f"Descuento: {preview['discount_percent']:.2f}% (${preview['discount_amount']:.2f})",
            f"Total a cobrar: ${preview['total']:.2f}",
            f"Saldo despues del cobro: ${preview['balance_after']:.2f}",
            f"Puntos a acumular: {preview['points_earned']}",
            "",
            "Membresia:",
            (
                f"{membership['membership_name']} - {membership['discount_percent']}%"
                if membership else "Sin membresia activa"
            ),
        ]
        if "transaction_id" in preview:
            lines.extend(["", f"Transaccion registrada: #{preview['transaction_id']}"])

        self.cashier_text.delete("1.0", tk.END)
        self.cashier_text.insert("1.0", "\n".join(lines))

    def refresh_users(self) -> None:
        for item in self.users_tree.get_children():
            self.users_tree.delete(item)

        for user in self.service.search_users(self.user_search_var.get()):
            full_name = f"{user['first_name']} {user['last_name']}"
            self.users_tree.insert(
                "",
                tk.END,
                values=(
                    user["id"],
                    user["document"],
                    full_name,
                    user["phone"],
                    user["card_uid"] or "Sin asignar",
                ),
            )

    def clear_user_search(self) -> None:
        self.user_search_var.set("")
        self.refresh_users()

    def on_user_selected(self, _event=None) -> None:
        selection = self.users_tree.selection()
        if not selection:
            return

        values = self.users_tree.item(selection[0], "values")
        if not values:
            return

        user_id = int(values[0])
        self.render_user_detail(user_id)

    def render_user_detail(self, user_id: int) -> None:
        try:
            detail = self.service.get_user_detail(user_id)
        except Exception as exc:
            messagebox.showerror("Usuario", str(exc))
            return

        user = detail["user"]
        membership = detail["membership"]

        lines = [
            f"Usuario: {user['first_name']} {user['last_name']}",
            f"Documento: {user['document']}",
            f"Correo: {user['email'] or 'Sin correo'}",
            f"Celular: {user['phone'] or 'Sin celular'}",
            f"Tarjeta NFC: {user['card_uid'] or 'Sin asignar'}",
            f"Saldo: ${detail['wallet_balance']:.2f}",
            f"Puntos: {detail['points_balance']}",
            "",
            "Membresia:",
        ]

        if membership:
            lines.extend(
                [
                    f"  Nombre: {membership['membership_name']}",
                    f"  Descuento: {membership['discount_percent']}%",
                    f"  Vigencia: {membership['start_date']} a {membership['end_date']}",
                ]
            )
        else:
            lines.append("  Sin membresia activa")

        lines.extend(["", "Movimientos de saldo:"])
        if detail["wallet_movements"]:
            for movement in detail["wallet_movements"]:
                lines.append(
                    f"  {movement['entry_type']} | ${movement['amount']:.2f} | "
                    f"{movement['created_at']} | {movement['description'] or 'Sin descripcion'}"
                )
        else:
            lines.append("  Sin movimientos registrados")

        lines.extend(["", "Transacciones:"])
        if detail["transactions"]:
            for transaction in detail["transactions"]:
                lines.append(
                    f"  #{transaction['id']} | ${transaction['amount']:.2f} | "
                    f"{transaction['points_earned']} pts | {transaction['created_at']} | "
                    f"{transaction['description'] or 'Sin descripcion'}"
                )
        else:
            lines.append("  Sin transacciones registradas")

        self.user_detail_text.delete("1.0", tk.END)
        self.user_detail_text.insert("1.0", "\n".join(lines))

    def refresh_dashboard(self) -> None:
        metrics = self.service.get_dashboard_metrics()
        self.dashboard_metrics_var.set(
            "\n".join(
                [
                    f"Usuarios registrados: {metrics['users_count']}",
                    f"Tarjetas activas: {metrics['cards_count']}",
                    f"Saldo total en monedero: ${metrics['total_balance']:.2f}",
                    f"Total recargado: ${metrics['total_topups']:.2f}",
                    f"Total cobrado: ${metrics['total_sales']:.2f}",
                    f"Puntos emitidos: {metrics['total_points']}",
                ]
            )
        )

        for item in self.wallet_tree.get_children():
            self.wallet_tree.delete(item)
        for movement in self.service.get_recent_wallet_movements():
            full_name = f"{movement['first_name']} {movement['last_name']}"
            self.wallet_tree.insert(
                "",
                tk.END,
                values=(
                    movement["entry_type"],
                    full_name,
                    movement["document"],
                    f"${movement['amount']:.2f}",
                    movement["created_at"],
                ),
            )

        for item in self.dashboard_tx_tree.get_children():
            self.dashboard_tx_tree.delete(item)
        for transaction in self.service.get_recent_transactions():
            full_name = f"{transaction['first_name']} {transaction['last_name']}"
            self.dashboard_tx_tree.insert(
                "",
                tk.END,
                values=(
                    transaction["id"],
                    full_name,
                    transaction["document"],
                    f"${transaction['amount']:.2f}",
                    transaction["points_earned"],
                    transaction["created_at"],
                ),
            )

    @staticmethod
    def _clear_entries(entries) -> None:
        for entry in entries:
            entry.delete(0, tk.END)

    def run(self) -> None:
        self.root.mainloop()
